"""Narrow typed executor for explicitly registered read-only operations.

This first executor deliberately supports only R0/R1 operations. It does not
accept shell commands, arbitrary callables from request data, or side effects.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Callable, Mapping
from typing import Any

from intelligence.runtime.argument_binding import (
    ArgumentBindingError, canonical_arguments, parse_and_bind,
)
from intelligence.runtime.momo_runtime import Risk


class OperationDenied(PermissionError):
    """Raised when an operation is unknown or fails its typed policy contract."""


class OperationExecutionError(RuntimeError):
    """Raised when an approved read-only operation fails after it starts."""


@dataclass(frozen=True)
class OperationSpec:
    operation_id: str
    domain: str
    required_capability: str
    risk: Risk
    argument_types: Mapping[str, type]
    handler: Callable[[Mapping[str, Any]], dict[str, Any]]
    side_effects: bool = False


@dataclass(frozen=True)
class OperationResult:
    operation_id: str
    task_id: str
    step_id: str
    status: str
    result: Mapping[str, Any]
    result_sha256: str


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


class OperationRegistry:
    """In-process allowlist of typed, read-only operation adapters."""

    _ID = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")

    def __init__(self) -> None:
        self._operations: dict[str, OperationSpec] = {}

    def register(self, spec: OperationSpec) -> None:
        if not isinstance(spec, OperationSpec):
            raise TypeError("Only OperationSpec instances can be registered")
        if not isinstance(spec.operation_id, str) or not self._ID.fullmatch(spec.operation_id):
            raise ValueError("Operation ID is invalid")
        if not isinstance(spec.domain, str) or not spec.domain.strip():
            raise ValueError("Operation domain is required")
        if not isinstance(spec.required_capability, str) or not spec.required_capability.strip():
            raise ValueError("Operation capability is required")
        if spec.risk not in {Risk.R0, Risk.R1}:
            raise ValueError("The initial typed executor permits only R0/R1 operations")
        if spec.side_effects is not False:
            raise ValueError("The initial typed executor refuses side-effecting operations")
        if not callable(spec.handler):
            raise TypeError("Operation handler must be callable")
        if not isinstance(spec.argument_types, Mapping):
            raise TypeError("argument_types must be a mapping")
        schema = dict(spec.argument_types)
        for name, expected_type in schema.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Argument names must be non-empty strings")
            if expected_type not in {str, int, bool, float, dict, list}:
                raise TypeError(f"Unsupported argument type for {name}")
        if spec.operation_id in self._operations:
            raise ValueError(f"Operation is already registered: {spec.operation_id}")
        self._operations[spec.operation_id] = OperationSpec(
            spec.operation_id, spec.domain, spec.required_capability, spec.risk,
            MappingProxyType(schema), spec.handler, False,
        )

    def get(self, operation_id: str) -> OperationSpec:
        try:
            return self._operations[operation_id]
        except (KeyError, TypeError) as error:
            raise OperationDenied("Operation is not registered") from error

    @staticmethod
    def validate_arguments(spec: OperationSpec, arguments: Mapping[str, Any]) -> None:
        expected = set(spec.argument_types)
        actual = set(arguments)
        if actual != expected:
            raise OperationDenied("Arguments do not match the operation schema")
        for name, expected_type in spec.argument_types.items():
            if type(arguments[name]) is not expected_type:
                raise OperationDenied(f"Argument has the wrong type: {name}")


class TypedExecutor:
    """Execute one registered read-only adapter after gate authorization."""

    def __init__(self, coordinator, gate, registry: OperationRegistry) -> None:
        self.coordinator = coordinator
        self.gate = gate
        self.registry = registry

    def execute(
        self,
        task_id: str,
        plan,
        step_id: str,
        operation_id: str,
        args_payload: str | bytes,
        approval_token: str | None = None,
    ) -> OperationResult:
        spec = self.registry.get(operation_id)
        step = next((item for item in plan.steps if item.step_id == step_id), None)
        if step is None:
            raise OperationDenied("Step is not part of the supplied plan")
        if step.domain != spec.domain:
            raise OperationDenied("Operation domain does not match the planned step")
        if spec.required_capability not in step.required_capabilities:
            raise OperationDenied("Planned step does not declare the required capability")
        if step.risk is not spec.risk:
            raise OperationDenied("Operation risk does not match the planned step")

        try:
            arguments, canonical_json, _digest = parse_and_bind(args_payload)
        except ArgumentBindingError as error:
            raise OperationDenied(f"Invalid operation arguments: {error}") from error
        self.registry.validate_arguments(spec, arguments)

        authorized = self.gate.start_step_with_arguments(
            task_id, plan, step_id, args_payload, approval_token=approval_token,
        )
        if authorized.canonical_json != canonical_json:
            raise OperationDenied("Authorized arguments changed during validation")

        try:
            result = spec.handler(authorized.arguments)
            if type(result) is not dict:
                raise TypeError("Read-only adapter must return a JSON object")
            _encoded_result, result_sha256 = canonical_arguments(result)
        except Exception as error:
            summary = f"{type(error).__name__}: {error}"[:500]
            self.coordinator.execution.finish_step(
                task_id, step_id, False, error=summary,
            )
            raise OperationExecutionError("Read-only operation failed") from error

        finished = self.coordinator.execution.finish_step(
            task_id, step_id, True, result_sha256=result_sha256,
        )
        return OperationResult(
            operation_id, task_id, step_id, finished.status.value,
            _freeze(result), result_sha256,
        )


def system_status_read(_arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Return a minimal, non-sensitive view of the running Linux environment."""
    uname = os.uname()
    return {
        "service": "momo-runtime",
        "state": "ready",
        "kernel": uname.release,
        "architecture": uname.machine,
    }


def default_read_only_registry() -> OperationRegistry:
    registry = OperationRegistry()
    registry.register(OperationSpec(
        operation_id="system.status.read",
        domain="system",
        required_capability="system.status.read",
        risk=Risk.R1,
        argument_types={},
        handler=system_status_read,
    ))
    return registry
