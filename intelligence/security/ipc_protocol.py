"""Strict bounded framing for the MOMO local IPC protocol.

This module validates transport framing and message shape only. It does not
authenticate peers, authorize operations, or dispatch requests.
"""
from __future__ import annotations

import json
import re
import socket
import struct
from typing import Any

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 64 * 1024
_HEADER = struct.Struct("!I")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_OPERATION = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_REQUIRED_KEYS = frozenset({"version", "request_id", "operation", "args"})


class IPCProtocolError(ValueError):
    """Raised when an IPC frame or request violates the protocol."""


def _reject_constant(value: str) -> None:
    raise IPCProtocolError(f"Non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IPCProtocolError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != _REQUIRED_KEYS:
        raise IPCProtocolError("Request must contain exactly the required fields")
    if type(payload["version"]) is not int or payload["version"] != PROTOCOL_VERSION:
        raise IPCProtocolError("Unsupported IPC protocol version")
    request_id = payload["request_id"]
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise IPCProtocolError("Invalid request_id")
    operation = payload["operation"]
    if not isinstance(operation, str) or not _OPERATION.fullmatch(operation):
        raise IPCProtocolError("Invalid operation name")
    if not isinstance(payload["args"], dict):
        raise IPCProtocolError("args must be a JSON object")
    return payload


def encode_request(payload: dict[str, Any]) -> bytes:
    request = validate_request(payload)
    try:
        body = json.dumps(
            request, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise IPCProtocolError("Request cannot be encoded as bounded JSON") from exc
    if not body or len(body) > MAX_FRAME_BYTES:
        raise IPCProtocolError("Request frame exceeds size limit")
    return _HEADER.pack(len(body)) + body


def decode_frame(frame: bytes) -> dict[str, Any]:
    if not isinstance(frame, bytes) or len(frame) < _HEADER.size:
        raise IPCProtocolError("Frame is shorter than its header")
    (length,) = _HEADER.unpack(frame[:_HEADER.size])
    if length == 0 or length > MAX_FRAME_BYTES:
        raise IPCProtocolError("Invalid frame length")
    if len(frame) != _HEADER.size + length:
        raise IPCProtocolError("Frame length does not match payload")
    try:
        body = frame[_HEADER.size:].decode("utf-8", errors="strict")
        payload = json.loads(
            body, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except IPCProtocolError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise IPCProtocolError("Malformed JSON payload") from exc
    return validate_request(payload)


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        part = connection.recv(size - len(chunks))
        if not part:
            raise IPCProtocolError("Peer closed before complete frame arrived")
        chunks.extend(part)
    return bytes(chunks)


def recv_request(connection: socket.socket) -> dict[str, Any]:
    """Read one bounded frame from an already-authenticated stream socket."""
    header = _recv_exact(connection, _HEADER.size)
    (length,) = _HEADER.unpack(header)
    if length == 0 or length > MAX_FRAME_BYTES:
        raise IPCProtocolError("Invalid frame length")
    body = _recv_exact(connection, length)
    return decode_frame(header + body)


def send_request(connection: socket.socket, payload: dict[str, Any]) -> None:
    """Send one validated request frame; callers own timeout and peer policy."""
    connection.sendall(encode_request(payload))
