import json
import os
import socket
import subprocess
import sys
import struct
import tempfile
import threading
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "board/momo/rootfs-overlay/usr/lib/momo"))

from intelligence.security.ipc_protocol import encode_request
from intelligence.security.linux_peercred import PeerCredentialError
from momo_ipcd import RequestReplayGuard, handle_connection, prepare_socket_path


class IPCServiceTests(unittest.TestCase):
    def test_status_read_only_request_returns_limited_status(self):
        server, client = socket.socketpair()
        worker = threading.Thread(
            target=handle_connection, args=(server, frozenset({os.getuid()}))
        )
        worker.start()
        client.sendall(encode_request({
            "version": 1, "request_id": "status-1",
            "operation": "status.read", "args": {},
        }))
        header = client.recv(4)
        length = struct.unpack("!I", header)[0]
        body = bytearray()
        while len(body) < length:
            body.extend(client.recv(length - len(body)))
        response = json.loads(body.decode("utf-8"))
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertTrue(response["ok"])
        self.assertEqual(response["request_id"], "status-1")
        self.assertEqual(response["result"]["tool_execution"], "disabled")
        self.assertEqual(response["result"]["capabilities"], ["status.read"])
        client.close()
        server.close()

    def test_rejects_non_allowlisted_peer(self):
        server, client = socket.socketpair()
        errors = []
        def run():
            try:
                handle_connection(server, frozenset({os.getuid() + 100000}))
            except Exception as exc:
                errors.append(exc)
            finally:
                server.close()
        worker = threading.Thread(target=run)
        worker.start()
        client.settimeout(1)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(client.recv(1), b"")
        self.assertFalse(errors)
        client.close()
        server.close()

    def test_rejects_any_operation_other_than_status_read(self):
        server, client = socket.socketpair()
        def run():
            try:
                handle_connection(server, frozenset({os.getuid()}))
            finally:
                server.close()
        worker = threading.Thread(target=run)
        worker.start()
        client.sendall(encode_request({
            "version": 1, "request_id": "exec-1",
            "operation": "process.execute", "args": {"command": "id"},
        }))
        client.settimeout(1)
        self.assertEqual(client.recv(1), b"")
        worker.join(timeout=2)
        client.close()
        server.close()

    def test_replay_guard_rejects_duplicates_and_evicts_oldest_bounded_entry(self):
        guard = RequestReplayGuard(capacity=2)
        self.assertTrue(guard.claim("one"))
        self.assertTrue(guard.claim("two"))
        self.assertFalse(guard.claim("one"))
        self.assertTrue(guard.claim("three"))
        self.assertTrue(guard.claim("one"))
        self.assertFalse(guard.claim("three"))

    def test_replay_guard_rejects_invalid_identifiers(self):
        guard = RequestReplayGuard()
        self.assertFalse(guard.claim(""))
        self.assertFalse(guard.claim(None))

    def test_process_restrictions_apply_limits_and_no_new_privs(self):
        service_path = ROOT / "board/momo/rootfs-overlay/usr/lib/momo"
        code = (
            "import ctypes, resource; "
            "from momo_ipcd import apply_process_restrictions; "
            "apply_process_restrictions(); "
            "assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0); "
            "assert resource.getrlimit(resource.RLIMIT_NOFILE) == (32, 32); "
            "assert resource.getrlimit(resource.RLIMIT_FSIZE) == (0, 0); "
            "assert ctypes.CDLL(None).prctl(39, 0, 0, 0, 0) == 1"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(service_path)
        result = subprocess.run(
            [sys.executable, "-c", code], env=env,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_refuses_to_replace_regular_file_or_foreign_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ipc.sock"
            path.write_text("do not replace", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                prepare_socket_path(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "do not replace")


if __name__ == "__main__":
    unittest.main()
