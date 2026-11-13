import socket
import struct
import unittest

from intelligence.security.ipc_protocol import (
    IPCProtocolError,
    MAX_FRAME_BYTES,
    decode_frame,
    encode_request,
    recv_request,
    send_request,
)

VALID = {
    "version": 1,
    "request_id": "req-001",
    "operation": "status.read",
    "args": {"scope": "runtime"},
}


class IPCProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(decode_frame(encode_request(VALID)), VALID)

    def test_rejects_unknown_or_missing_fields(self):
        for payload in (
            {**VALID, "extra": True},
            {key: value for key, value in VALID.items() if key != "args"},
        ):
            with self.subTest(payload=payload), self.assertRaises(IPCProtocolError):
                encode_request(payload)

    def test_rejects_bool_as_protocol_version(self):
        with self.assertRaises(IPCProtocolError):
            encode_request({**VALID, "version": True})

    def test_rejects_unsupported_version(self):
        with self.assertRaises(IPCProtocolError):
            encode_request({**VALID, "version": 2})

    def test_rejects_invalid_request_id_and_operation(self):
        for field, value in (("request_id", "x" * 129), ("operation", "BAD OP")):
            with self.subTest(field=field), self.assertRaises(IPCProtocolError):
                encode_request({**VALID, field: value})

    def test_rejects_non_object_args(self):
        with self.assertRaises(IPCProtocolError):
            encode_request({**VALID, "args": []})

    def test_rejects_duplicate_json_keys(self):
        body = b'{"version":1,"request_id":"a","operation":"x","args":{},"args":{}}'
        frame = struct.pack("!I", len(body)) + body
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame)

    def test_rejects_non_finite_json_constants(self):
        body = b'{"version":1,"request_id":"a","operation":"x","args":{"n":NaN}}'
        frame = struct.pack("!I", len(body)) + body
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame)

    def test_rejects_invalid_utf8(self):
        body = b'{"version":1,"request_id":"a","operation":"x","args":{"v":"\xff"}}'
        frame = struct.pack("!I", len(body)) + body
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame)

    def test_rejects_truncated_and_trailing_data(self):
        frame = encode_request(VALID)
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame[:-1])
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame + b"x")

    def test_rejects_oversized_frame_before_reading_body(self):
        frame = struct.pack("!I", MAX_FRAME_BYTES + 1)
        with self.assertRaises(IPCProtocolError):
            decode_frame(frame)

    def test_socket_stream_round_trip(self):
        left, right = socket.socketpair()
        try:
            send_request(left, VALID)
            self.assertEqual(recv_request(right), VALID)
        finally:
            left.close()
            right.close()

    def test_peer_eof_mid_frame_is_rejected(self):
        left, right = socket.socketpair()
        try:
            left.sendall(struct.pack("!I", 20) + b"short")
            left.close()
            with self.assertRaises(IPCProtocolError):
                recv_request(right)
        finally:
            right.close()


if __name__ == "__main__":
    unittest.main()
