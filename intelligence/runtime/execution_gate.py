"""The single authorization point for starting tasks and steps.

Every transition into EXECUTING and every RUNNING step start for a plan-bound
task goes through ExecutionGate. Each call re-verifies the persisted plan,
checks the current task/step state, consumes the required approval or grant,
and applies the state change inside ONE SQLite write transaction. A failure at
any point rolls the whole operation back, including the approval consumption.

Known limits (see the audit report): R0-R2 grants live in a separate
permission database, so a grant can be consumed before the step start
transaction. That ordering fails closed (a grant may be spent without a start,
never a start without a grant). A process with write access to the database
files can still bypass the gate; OS-level separation is a later milestone.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from types import MappingProxyType
from contextlib import contextmanager
from datetime import datetime, timezone

from intelligence.execution.step_journal import StepExecution
from intelligence.runtime.approval_store import (
    TASK_ACTION, ApprovalDenied, ApprovalStore, binding_digest, is_sha256_hex,
)
from intelligence.runtime.momo_runtime import GATE_AUTHORITY, Risk, Task, TaskStatus
from intelligence.runtime.argument_binding import parse_and_bind

_LOW_RISK = frozenset({Risk.R0, Risk.R1, Risk.R2})
_HIGH_RISK = frozenset({Risk.R3, Risk.R4})


class AuthorizationDenied(ValueError):
    """Raised when the gate refuses to start a task or step."""


def _utc(now: datetime | None) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Authorization time must be timezone-aware")
    return now.astimezone(timezone.utc)


@dataclass(frozen=True)
class AuthorizedStepStart:
    """A durable step start paired with the exact validated arguments."""

    execution: StepExecution
    arguments: object
    canonical_json: str
    args_sha256: str


class ExecutionGate:
    def __init__(self, coordinator, clock=None) -> None:
        self.coordinator = coordinator
        self.database = coordinator.tasks.database
        # Trusted clock; per-call time is deliberately not accepted (see ApprovalStore).
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @contextmanager
    def _write(self):
        connection = sqlite3.connect(str(self.database), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def start_task_execution(
        self, task_id: str, plan, approval_token: str | None = None,
    ) -> Task:
        """Move a task to EXECUTING. R3/R4 tasks require a task-level approval."""
        from intelligence.runtime.task_coordinator import _plan_digest

        at = _utc(self._clock())
        task = self.coordinator.tasks.get_task(task_id)
        self.coordinator._validate_task_plan(task, plan)
        plan_sha256 = _plan_digest(plan)[0]

        with self._write() as connection:
            row = connection.execute(
                "SELECT status, risk FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise AuthorizationDenied("Task does not exist")
            status, risk = TaskStatus(row[0]), Risk(row[1])
            if status not in {TaskStatus.PLANNED, TaskStatus.AWAITING_APPROVAL}:
                raise AuthorizationDenied(f"Task cannot start execution from {status.value}")
            if risk in _HIGH_RISK or approval_token is not None:
                binding = binding_digest(
                    task_id, None, TASK_ACTION, task_id, risk.value, plan_sha256, plan_sha256,
                )
                try:
                    ApprovalStore.consume(connection, approval_token, binding, at)
                except ApprovalDenied as error:
                    raise AuthorizationDenied(str(error)) from error
            self.coordinator.tasks._transition_locked(
                connection, task_id, TaskStatus.EXECUTING,
                "ExecutionGate authorized task execution", authority=GATE_AUTHORITY,
            )
        return self.coordinator.tasks.get_task(task_id)

    def start_step_with_arguments(
        self, task_id: str, plan, step_id: str, args_payload: str | bytes,
        approval_token: str | None = None,
    ) -> AuthorizedStepStart:
        """Validate exact JSON arguments, derive their digest, then authorize start.

        The returned parsed arguments are the same values whose canonical digest
        was bound to approval. A future executor must consume this object rather
        than reparsing caller-controlled input after authorization.
        """
        try:
            arguments, canonical_json, args_sha256 = parse_and_bind(args_payload)
        except ValueError as error:
            raise AuthorizationDenied(f"Invalid step arguments: {error}") from error
        execution = self._start_step_with_digest(
            task_id, plan, step_id, args_sha256, approval_token=approval_token,
        )
        return AuthorizedStepStart(
            execution, MappingProxyType(arguments), canonical_json, args_sha256,
        )

    def start_step(
        self, task_id: str, plan, step_id: str, args_payload: str | bytes,
        approval_token: str | None = None,
    ) -> StepExecution:
        """Public start API: accept raw arguments, never a caller-supplied digest."""
        return self.start_step_with_arguments(
            task_id, plan, step_id, args_payload, approval_token=approval_token,
        ).execution

    def _start_step_with_digest(
        self, task_id: str, plan, step_id: str, args_sha256: str,
        approval_token: str | None = None,
    ) -> StepExecution:
        """Start one ready step. R3/R4 steps need a step-bound approval token."""
        from intelligence.runtime.task_coordinator import _plan_digest

        at = _utc(self._clock())
        if not is_sha256_hex(args_sha256):
            raise AuthorizationDenied("A SHA-256 digest of the step arguments is required")
        task = self.coordinator.tasks.get_task(task_id)
        self.coordinator._validate_task_plan(task, plan)
        step = next((item for item in plan.steps if item.step_id == step_id), None)
        if step is None:
            raise AuthorizationDenied("Step is not part of the validated plan")
        plan_sha256 = _plan_digest(plan)[0]

        if step.risk in _LOW_RISK:
            # Grant consumption is in the permission database: it happens before
            # the write below. A later failure burns the grant (fail closed).
            decision = self.coordinator.authorize_step(task_id, plan, step_id)
            if not decision.allowed:
                raise AuthorizationDenied(decision.reason)
        elif not isinstance(approval_token, str) or not approval_token:
            raise AuthorizationDenied("R3/R4 steps require an issued approval token")

        with self._write() as connection:
            row = connection.execute(
                "SELECT status FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None or TaskStatus(row[0]) is not TaskStatus.EXECUTING:
                raise AuthorizationDenied("Task must be executing before its steps start")
            for dependency in step.depends_on:
                dep = connection.execute(
                    "SELECT status FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                    (task_id, dependency),
                ).fetchone()
                if dep is None or dep[0] != "succeeded":
                    raise AuthorizationDenied(f"Dependency is not durably succeeded: {dependency}")
            state = connection.execute(
                "SELECT status, risk FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
            if state is None or state[0] != "ready" or Risk(state[1]) is not step.risk:
                raise AuthorizationDenied("Step is not ready for start")
            if step.risk in _HIGH_RISK:
                binding = binding_digest(
                    task_id, step_id, step.domain, task_id, step.risk.value,
                    plan_sha256, args_sha256,
                )
                try:
                    ApprovalStore.consume(connection, approval_token, binding, at)
                except ApprovalDenied as error:
                    raise AuthorizationDenied(str(error)) from error
            self.coordinator.execution._start_locked(
                connection, task_id, step_id, False, at.isoformat(),
            )
        return self.coordinator.execution.get_step(task_id, step_id)
