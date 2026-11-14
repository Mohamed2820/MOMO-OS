"""Strict, bounded canonicalization for operation argument payloads.

This is a serialization primitive only. It does not authenticate the caller,
authorize an operation, or make an untrusted caller-supplied digest trustworthy.
The trusted execution broker must parse the exact received payload and compute
the digest itself before binding approval to it.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

MAX_ARGUMENT_BYTES = 64 * 1024
MAX_ARGUMENT_DEPTH = 32
MAX_ARGUMENT_NODES = 4096
MAX_INTEGER = (1 << 63) - 1


class ArgumentBindingError(ValueError):
    """Raised when an argument payload is invalid or exceeds safe bounds."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArgumentBindingError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ArgumentBindingError(f"Non-standard JSON numeric constant: {value}")


def _validate(value: Any, *, depth: int, budget: list[int]) -> None:
    budget[0] += 1
    if budget[0] > MAX_ARGUMENT_NODES:
        raise ArgumentBindingError("Argument payload exceeds the node limit")
    if depth > MAX_ARGUMENT_DEPTH:
        raise ArgumentBindingError("Argument payload exceeds the nesting limit")

    if value is None or type(value) in (bool, str):
        return
    if type(value) is int:
        if not -MAX_INTEGER - 1 <= value <= MAX_INTEGER:
            raise ArgumentBindingError("Integer argument is outside the signed 64-bit range")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ArgumentBindingError("Non-finite numbers are not valid arguments")
        return
    if type(value) is list:
        for item in value:
            _validate(item, depth=depth + 1, budget=budget)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ArgumentBindingError("JSON object keys must be strings")
            _validate(item, depth=depth + 1, budget=budget)
        return
    raise ArgumentBindingError(f"Unsupported argument value type: {type(value).__name__}")


def parse_arguments(payload: str | bytes, *, max_bytes: int = MAX_ARGUMENT_BYTES) -> dict[str, Any]:
    """Parse one bounded JSON object, rejecting duplicate keys and extensions."""
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_ARGUMENT_BYTES:
        raise ValueError("max_bytes must be between 1 and MAX_ARGUMENT_BYTES")
    if isinstance(payload, bytes):
        raw = payload
        try:
            source = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ArgumentBindingError("Arguments must be valid UTF-8") from error
    elif isinstance(payload, str):
        source = payload
        try:
            raw = payload.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ArgumentBindingError("Arguments must be valid Unicode text") from error
    else:
        raise ArgumentBindingError("Arguments must be supplied as UTF-8 JSON text")
    if len(raw) > max_bytes:
        raise ArgumentBindingError("Argument payload exceeds the byte limit")
    try:
        value = json.loads(
            source,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except ArgumentBindingError:
        raise
    except (json.JSONDecodeError, UnicodeError, ValueError) as error:
        raise ArgumentBindingError("Arguments are not valid strict JSON") from error
    if type(value) is not dict:
        raise ArgumentBindingError("The argument payload must be a JSON object")
    _validate(value, depth=0, budget=[0])
    return value


def canonical_arguments(value: dict[str, Any]) -> tuple[str, str]:
    """Return deterministic UTF-8 JSON and its SHA-256 digest after validation."""
    if type(value) is not dict:
        raise ArgumentBindingError("Arguments must be a JSON object")
    _validate(value, depth=0, budget=[0])
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ArgumentBindingError("Arguments cannot be canonicalized") from error
    try:
        raw = encoded.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ArgumentBindingError("Arguments contain invalid Unicode text") from error
    if len(raw) > MAX_ARGUMENT_BYTES:
        raise ArgumentBindingError("Canonical arguments exceed the byte limit")
    return encoded, hashlib.sha256(raw).hexdigest()


def parse_and_bind(payload: str | bytes) -> tuple[dict[str, Any], str, str]:
    """Parse the exact payload and return (arguments, canonical JSON, digest)."""
    arguments = parse_arguments(payload)
    encoded, digest = canonical_arguments(arguments)
    return arguments, encoded, digest
