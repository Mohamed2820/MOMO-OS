"""MOMO's provider-neutral, capability-mediated task runtime core.

This module deliberately contains no model SDK, Android bridge, shell executor,
or ambient device authority. It models task state and permission decisions only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable
from uuid import uuid4


class Risk(str, Enum):
    R0 = "R0"  # public/read-only
    R1 = "R1"  # scoped private read
    R2 = "R2"  # reversible write
    R3 = "R3"  # external side effect
    R4 = "R4"  # destructive/security/device integrity


class TaskStatus(str, Enum):
    RECEIVED = "received"
    CLASSIFIED = "classified"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = {
    TaskStatus.COMPLETED,
    TaskStatus.PARTIALLY_COMPLETED,
    TaskStatus.BLOCKED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}

_ALLOWED: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.RECEIVED: {TaskStatus.CLASSIFIED, TaskStatus.CANCELLED},
    TaskStatus.CLASSIFIED: {TaskStatus.PLANNED, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.PLANNED: {
        TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING,
        TaskStatus.BLOCKED, TaskStatus.CANCELLED,
    },
    TaskStatus.AWAITING_APPROVAL: {
        TaskStatus.EXECUTING, TaskStatus.BLOCKED, TaskStatus.CANCELLED,
    },
    TaskStatus.EXECUTING: {
        TaskStatus.VERIFYING, TaskStatus.PARTIALLY_COMPLETED,
        TaskStatus.FAILED, TaskStatus.CANCELLED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.COMPLETED, TaskStatus.PARTIALLY_COMPLETED,
        TaskStatus.FAILED,
    },
}


@dataclass(frozen=True)
class TaskEvent:
    at: datetime
    previous: TaskStatus
    current: TaskStatus
    reason: str


@dataclass
class Task:
    goal: str
    risk: Risk
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.RECEIVED
    events: list[TaskEvent] = field(default_factory=list)

    def transition(self, target: TaskStatus, reason: str) -> None:
        if self.status in TERMINAL:
            raise ValueError(f"Task is terminal: {self.status.value}")
        if target not in _ALLOWED.get(self.status, set()):
            raise ValueError(
                f"Invalid task transition: {self.status.value} -> {target.value}"
            )
        if (
            self.status == TaskStatus.PLANNED
            and target == TaskStatus.EXECUTING
            and self.risk in {Risk.R3, Risk.R4}
        ):
            raise ValueError("R3/R4 tasks must enter awaiting_approval before execution")
        if not reason.strip():
            raise ValueError("A transition reason is required")
        previous = self.status
        self.status = target
        self.events.append(
            TaskEvent(datetime.now(timezone.utc), previous, target, reason.strip())
        )


@dataclass(frozen=True)
class CapabilityGrant:
    subject: str
    action: str
    resource: str
    risk: Risk
    expires_at: datetime
    approval_mode: str = "per_call"
    max_uses: int = 1
    grant_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Approval:
    subject: str
    action: str
    resource: str
    approved: bool


@dataclass(frozen=True)
class ToolRequest:
    subject: str
    action: str
    resource: str
    risk: Risk


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    grant_id: str | None = None


class PermissionBroker:
    """In-process policy evaluator; platform adapters must enforce OS permissions."""

    _APPROVAL_MODES = {"per_call", "standing_scoped", "never_allowed"}

    def __init__(self) -> None:
        self._usage: dict[str, int] = {}
        self._revoked: set[str] = set()

    def revoke(self, grant_id: str) -> bool:
        """Revoke a grant immediately for this broker instance."""
        if not grant_id:
            raise ValueError("Grant ID must not be empty")
        self._revoked.add(grant_id)
        return True

    def authorize(
        self,
        request: ToolRequest,
        grants: Iterable[CapabilityGrant],
        approval: Approval | None = None,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            return AuthorizationDecision(False, "Authorization time must be timezone-aware")

        if request.risk in {Risk.R3, Risk.R4}:
            if approval is None or not approval.approved:
                return AuthorizationDecision(False, "Explicit per-action approval required")
            if (
                approval.subject != request.subject
                or approval.action != request.action
                or approval.resource != request.resource
            ):
                return AuthorizationDecision(False, "Approval does not match this request")

        for grant in grants:
            if grant.grant_id in self._revoked:
                continue
            if grant.approval_mode not in self._APPROVAL_MODES:
                continue
            if grant.approval_mode == "never_allowed":
                continue
            if not grant.grant_id or grant.max_uses < 1:
                continue
            if grant.expires_at.tzinfo is None or grant.expires_at.utcoffset() is None:
                continue
            if grant.expires_at <= now:
                continue
            if self._usage.get(grant.grant_id, 0) >= grant.max_uses:
                continue
            if (
                grant.subject == request.subject
                and grant.action == request.action
                and grant.resource == request.resource
                and grant.risk == request.risk
            ):
                self._usage[grant.grant_id] = self._usage.get(grant.grant_id, 0) + 1
                return AuthorizationDecision(
                    True, "Matching scoped capability grant", grant.grant_id
                )
        return AuthorizationDecision(False, "No active matching capability grant")
