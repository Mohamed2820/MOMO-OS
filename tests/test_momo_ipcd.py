import json
import os
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path

from intelligence.security.ipc_protocol import encode_request
from intelligence.security.linux_peercred import PeerCredentialError
from momo_ipcd import handle_connection, prepare_socket_path


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
        worker = threading.Thread(target=run)
        worker.start()
        client.sendall(encode_request({
            "version": 1, "request_id": "deny-1",
            "operation": "status.read", "args": {},
        }))
        client.settimeout(1)
        self.assertEqual(client.recv(1), b"")
        worker.join(timeout=2)
        self.assertFalse(errors)
        client.close()
        server.close()

    def test_rejects_any_operation_other_than_status_read(self):
        server, client = socket.socketpair()
        worker = threading.Thread(
            target=handle_connection, args=(server, frozenset({os.getuid()}))
        )
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

    def test_refuses_to_replace_regular_file_or_foreign_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ipc.sock"
            path.write_text("do not replace", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                prepare_socket_path(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "do not replace")


if __name__ == "__main__":
    unittest.main()
