import os
import socket
import unittest

from intelligence.security.linux_peercred import (
    PeerCredentialError,
    get_peer_credentials,
    require_peer_identity,
)


class LinuxPeerCredentialTests(unittest.TestCase):
    def setUp(self):
        self.server, self.client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

    def tearDown(self):
        self.server.close()
        self.client.close()

    def test_reads_kernel_reported_peer_credentials(self):
        peer = get_peer_credentials(self.server)
        self.assertEqual(peer.pid, os.getpid())
        self.assertEqual(peer.uid, os.getuid())
        self.assertEqual(peer.gid, os.getgid())

    def test_allows_exact_uid_and_primary_gid(self):
        peer = require_peer_identity(
            self.server, allowed_uids={os.getuid()}, allowed_gids={os.getgid()}
        )
        self.assertEqual(peer.uid, os.getuid())

    def test_rejects_uid_outside_allowlist(self):
        with self.assertRaises(PeerCredentialError):
            require_peer_identity(self.server, allowed_uids={os.getuid() + 1})

    def test_rejects_primary_gid_outside_allowlist(self):
        with self.assertRaises(PeerCredentialError):
            require_peer_identity(
                self.server, allowed_uids={os.getuid()}, allowed_gids={os.getgid() + 1}
            )

    def test_empty_allowlist_denies_all_peers(self):
        with self.assertRaises(ValueError):
            require_peer_identity(self.server, allowed_uids=set())

    def test_invalid_allowlist_types_are_rejected(self):
        with self.assertRaises(ValueError):
            require_peer_identity(self.server, allowed_uids={True})

    def test_rejects_non_unix_socket(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(listener.getsockname())
        accepted, _ = listener.accept()
        try:
            with self.assertRaises(PeerCredentialError):
                get_peer_credentials(accepted)
        finally:
            accepted.close()
            client.close()
            listener.close()


if __name__ == "__main__":
    unittest.main()
