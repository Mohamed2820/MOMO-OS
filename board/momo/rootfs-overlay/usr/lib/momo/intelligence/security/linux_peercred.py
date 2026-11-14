"""Linux AF_UNIX peer identity helpers backed by kernel-provided credentials.

This module authenticates the connected local process identity only. It does
not authorize an operation, grant capabilities, or create a process sandbox.
"""
from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from collections.abc import Iterable


class PeerCredentialError(PermissionError):
    """Raised when a Unix-socket peer is not in the configured identity set."""


@dataclass(frozen=True)
class PeerCredentials:
    pid: int
    uid: int
    gid: int


def get_peer_credentials(connection: socket.socket) -> PeerCredentials:
    """Return Linux SO_PEERCRED for a connected AF_UNIX socket."""
    if not isinstance(connection, socket.socket):
        raise TypeError("connection must be a socket.socket")
    if connection.family != socket.AF_UNIX:
        raise PeerCredentialError("Only AF_UNIX connections are supported")
    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("Kernel does not expose SO_PEERCRED")

    raw = connection.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
    )
    if len(raw) != struct.calcsize("3i"):
        raise PeerCredentialError("Kernel returned malformed peer credentials")
    pid, uid, gid = struct.unpack("3i", raw)
    if pid <= 0 or uid < 0 or gid < 0:
        raise PeerCredentialError("Kernel returned invalid peer credentials")
    return PeerCredentials(pid=pid, uid=uid, gid=gid)


def require_peer_identity(
    connection: socket.socket,
    allowed_uids: Iterable[int],
    allowed_gids: Iterable[int] | None = None,
) -> PeerCredentials:
    """Require the peer's kernel-reported UID and optionally primary GID.

    Supplementary groups are not represented by SO_PEERCRED. Callers needing
    supplementary-group policy must resolve it through a separately trusted
    identity source. An empty allowlist denies all peers.
    """
    uids = frozenset(allowed_uids)
    gids = None if allowed_gids is None else frozenset(allowed_gids)
    if not uids or any(type(value) is not int or value < 0 for value in uids):
        raise ValueError("allowed_uids must contain non-negative integer IDs")
    if gids is not None and any(
        type(value) is not int or value < 0 for value in gids
    ):
        raise ValueError("allowed_gids must contain non-negative integer IDs")

    peer = get_peer_credentials(connection)
    if peer.uid not in uids:
        raise PeerCredentialError("Unix-socket peer UID is not authorized")
    if gids is not None and peer.gid not in gids:
        raise PeerCredentialError("Unix-socket peer primary GID is not authorized")
    return peer
