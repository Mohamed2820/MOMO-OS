"""Unprivileged, read-only MOMO local IPC status service.

The service accepts only root-owned local clients and one read-only operation.
It intentionally has no shell, process, filesystem-write, or tool dispatcher.
"""
from __future__ import annotations

import ctypes
import errno
import json
import os
import resource
import socket
import stat
import struct
import threading
from collections import deque
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, "/usr/lib/momo")

from intelligence.security.ipc_protocol import (
    IPCProtocolError, MAX_FRAME_BYTES, decode_frame, recv_request,
)
from intelligence.security.linux_peercred import (
    PeerCredentialError, require_peer_identity,
)

SOCKET_PATH = Path("/run/momo/ipc.sock")
ALLOWED_CLIENT_UIDS = frozenset({0})
MAX_CLIENTS_PER_LOOP = 8
MAX_ADDRESS_SPACE = 256 * 1024 * 1024


def apply_process_restrictions() -> None:
    """Apply conservative per-process limits and Linux no_new_privs."""
    limits = (
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_NOFILE, 32),
        (resource.RLIMIT_FSIZE, 0),
        (resource.RLIMIT_CPU, 120),
        (resource.RLIMIT_AS, MAX_ADDRESS_SPACE),
    )
    for limit, value in limits:
        resource.setrlimit(limit, (value, value))
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    # Linux PR_SET_NO_NEW_PRIVS = 38. This is not a seccomp filter.
    if prctl(38, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
REPLAY_CACHE_CAPACITY = 1024


class RequestReplayGuard:
    """Bounded in-memory replay detector for request IDs within one daemon run."""

    def __init__(self, capacity: int = REPLAY_CACHE_CAPACITY) -> None:
        if type(capacity) is not int or capacity < 1:
            raise ValueError("Replay cache capacity must be a positive integer")
        self._capacity = capacity
        self._order: deque[str] = deque()
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def claim(self, request_id: str) -> bool:
        if not isinstance(request_id, str) or not request_id:
            return False
        with self._lock:
            if request_id in self._seen:
                return False
            if len(self._order) >= self._capacity:
                expired = self._order.popleft()
                self._seen.remove(expired)
            self._order.append(request_id)
            self._seen.add(request_id)
            return True


def _response_frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(
        payload, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    if not body or len(body) > MAX_FRAME_BYTES:
        raise IPCProtocolError("Response exceeds frame size limit")
    return struct.pack("!I", len(body)) + body


def _status_payload() -> dict[str, Any]:
    uname = os.uname()
    return {
        "service": "momo-ipcd",
        "state": "ready",
        "kernel": uname.release,
        "architecture": uname.machine,
        "protocol_version": 1,
        "capabilities": ["status.read"],
        "tool_execution": "disabled",
    }


def handle_connection(
    connection: socket.socket, allowed_uids: frozenset[int],
    replay_guard: RequestReplayGuard | None = None,
) -> None:
    """Authenticate, validate and answer one read-only request."""
    try:
        peer = require_peer_identity(connection, allowed_uids)
        request = recv_request(connection)
        if replay_guard is not None and not replay_guard.claim(request["request_id"]):
            raise IPCProtocolError("Duplicate request identifier")
        if request["operation"] != "status.read" or request["args"] != {}:
            raise IPCProtocolError("Operation is not available")
        response = {
            "version": 1,
            "request_id": request["request_id"],
            "ok": True,
            "peer_pid": peer.pid,
            "result": _status_payload(),
        }
        connection.sendall(_response_frame(response))
    except (PeerCredentialError, IPCProtocolError, OSError, ValueError):
        # Fail closed: no diagnostic detail is returned to an untrusted peer.
        return


def prepare_socket_path(path: Path) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.geteuid():
        raise RuntimeError("Refusing to replace a non-owned or non-socket IPC path")
    path.unlink()



def apply_seccomp_filter() -> None:
    """Install a fail-closed syscall denylist after socket setup.

    The default action is ALLOW; dangerous process/namespace and execution
    syscalls are denied. This is defense in depth, not a complete allowlist.
    """
    try:
        seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    except OSError as exc:
        raise RuntimeError("libseccomp is required; refusing to run without syscall filter") from exc
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_rule_add.restype = ctypes.c_int
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_load.restype = ctypes.c_int
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]

    action_allow = 0x7FFF0000
    action_errno = 0x00050000 | errno.EPERM
    context = seccomp.seccomp_init(action_allow)
    if not context:
        raise OSError(ctypes.get_errno(), "seccomp_init failed")
    denied = (
        "execve", "execveat", "fork", "vfork", "clone", "clone3",
        "ptrace", "mount", "umount2", "pivot_root", "chroot",
        "unshare", "setns", "reboot", "kexec_load", "bpf", "keyctl",
        "perf_event_open", "open_by_handle_at", "io_uring_setup",
        "io_uring_enter", "io_uring_register", "userfaultfd",
        "process_vm_readv", "process_vm_writev",
    )
    try:
        for name in denied:
            number = seccomp.seccomp_syscall_resolve_name(name.encode("ascii"))
            if number < 0:
                continue
            result = seccomp.seccomp_rule_add(context, action_errno, number, 0)
            if result != 0:
                raise OSError(-result, f"seccomp rule failed: {name}")
        result = seccomp.seccomp_load(context)
        if result != 0:
            raise OSError(-result, "seccomp_load failed")
    finally:
        seccomp.seccomp_release(context)

def serve(path: Path = SOCKET_PATH) -> None:
    apply_process_restrictions()
    prepare_socket_path(path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    replay_guard = RequestReplayGuard()
    try:
        server.bind(str(path))
        os.chmod(path, 0o660)
        server.listen(MAX_CLIENTS_PER_LOOP)
        server.settimeout(1.0)
        apply_seccomp_filter()
        while True:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(2.0)
                handle_connection(connection, ALLOWED_CLIENT_UIDS, replay_guard)
    finally:
        server.close()
        try:
            metadata = path.lstat()
            if stat.S_ISSOCK(metadata.st_mode) and metadata.st_uid == os.geteuid():
                path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    serve()
