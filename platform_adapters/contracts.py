"""Typed, platform-neutral contracts for MOMO hardware adapters.

This module defines interfaces and result types only. It intentionally contains
no shell, root, device-file, or vendor-specific implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from intelligence.runtime.momo_runtime import Risk


class PlatformTrack(str, Enum):
    ANDROID = "android"
    MAINLINE_LINUX = "mainline-linux"
    VIRTUAL = "virtual"


class CapabilityState(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    PERMISSION_DENIED = "permission_denied"


@dataclass(frozen=True)
class PlatformIdentity:
    track: PlatformTrack
    architecture: str
    platform_release: str
    kernel_release: str | None = None
    device_profile_id: str | None = None


@dataclass(frozen=True)
class Capability:
    capability_id: str
    state: CapabilityState
    reason: str = ""


@dataclass(frozen=True)
class OperationSpec:
    operation_id: str
    risk: Risk
    required_capabilities: frozenset[str]
    reversible: bool
    description: str


@dataclass(frozen=True)
class OperationRequest:
    operation_id: str
    arguments: dict[str, object]
    approval_id: str | None = None


@dataclass(frozen=True)
class OperationResult:
    operation_id: str
    state: CapabilityState
    audit_id: str
    message: str = ""
    data: dict[str, object] | None = None


@runtime_checkable
class PlatformAdapter(Protocol):
    """Narrow typed interface implemented by a specific platform adapter."""

    @property
    def identity(self) -> PlatformIdentity:
        ...

    def capabilities(self) -> tuple[Capability, ...]:
        ...

    def describe_operation(self, operation_id: str) -> OperationSpec | None:
        ...

    def execute(self, request: OperationRequest) -> OperationResult:
        """Execute only after the host permission broker authorizes the request."""
        ...


def missing_capabilities(
    operation: OperationSpec,
    available: tuple[Capability, ...],
) -> tuple[str, ...]:
    """Return required capabilities not currently reported as supported."""
    states = {item.capability_id: item.state for item in available}
    return tuple(sorted(
        capability
        for capability in operation.required_capabilities
        if states.get(capability) != CapabilityState.SUPPORTED
    ))
