"""Single-use, expiring, binding-checked approval tokens.

An approval exists only as a row written by ApprovalStore.issue(). The caller
receives an unguessable token once; the database keeps only its SHA-256 hash,
the binding digest of the exact operation, the expiry and the consumption
time. A bare Python object (for example Approval(approved=True)) carries no
server-side row and therefore cannot satisfy the gate.

Consumption happens inside the gate's write transaction, so a failed step
start rolls the approval back, and two concurrent consumers cannot both win.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timezone

from intelligence.runtime.momo_runtime import Risk
from intelligence.runtime.argument_binding import parse_and_bind

TASK_ACTION = "task.execute"
MAX_TTL_SECONDS = 15 * 60
_HEX = frozenset("0123456789abcdef")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_tokens (
    token_hash TEXT PRIMARY KEY CHECK(length(token_hash) = 64),
    binding TEXT NOT NULL CHECK(length(binding) = 64),
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    step_id TEXT,
    approver TEXT NOT NULL CHECK(length(trim(approver)) > 0),
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
"""


class ApprovalDenied(ValueError):
    """Raised when an approval is missing, forged, mismatched, expired or reused."""


def _utc(now: datetime | None) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Authorization time must be timezone-aware")
    return now.astimezone(timezone.utc)


def is_sha256_hex(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def binding_digest(
    task_id: str, step_id: str | None, action: str, resource: str,
    risk: str, plan_sha256: str, args_sha256: str,
) -> str:
    """Digest of every fact an approval is bound to."""
    document = {
        "task_id": task_id,
        "step_id": step_id,
        "action": action,
        "resource": resource,
        "risk": risk,
        "plan_sha256": plan_sha256,
        "args_sha256": args_sha256,
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ApprovalStore:
    """Issues approval tokens bound to the persisted plan of one task."""

    def __init__(self, coordinator, clock=None) -> None:
        self.coordinator = coordinator
        self.database = coordinator.tasks.database
        # Trusted clock. Callers cannot supply "now" per call: that would let a
        # caller backdate or extend an approval's lifetime. Tests inject a clock here.
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        with sqlite3.connect(str(self.database), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(_SCHEMA)

    def issue(
        self,
        task_id: str,
        plan,
        approver: str,
        ttl_seconds: int,
        step_id: str | None = None,
        args_sha256: str | None = None,
    ) -> str:
        """Return a one-time token for exactly one task, step or plan.

        Task-level approval (step_id=None) binds the accepted plan digest.
        Step-level approval binds the step, its action/resource/risk and the
        caller-declared arguments digest.
        """
        from intelligence.runtime.task_coordinator import _plan_digest

        issued = _utc(self._clock())
        if not isinstance(approver, str) or not approver.strip():
            raise ValueError("An approver identity is required")
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
            raise ValueError("Approval TTL must be between 1 second and 15 minutes")

        task = self.coordinator.tasks.get_task(task_id)
        self.coordinator._validate_task_plan(task, plan)
        plan_sha256 = _plan_digest(plan)[0]

        if step_id is None:
            action, resource, risk = TASK_ACTION, task_id, task.risk.value
            args = plan_sha256
        else:
            step = next((item for item in plan.steps if item.step_id == step_id), None)
            if step is None:
                raise ValueError("Step is not part of the validated plan")
            if not is_sha256_hex(args_sha256):
                raise ValueError("Step approval requires a SHA-256 arguments digest")
            action, resource, risk = step.domain, task_id, step.risk.value
            args = args_sha256

        binding = binding_digest(task_id, step_id, action, resource, risk, plan_sha256, args)
        token = secrets.token_urlsafe(32)
        expires = issued.timestamp() + ttl_seconds
        with sqlite3.connect(str(self.database), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute(
                """
                INSERT INTO approval_tokens(
                    token_hash, binding, task_id, step_id, approver,
                    issued_at, expires_at, consumed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    _token_hash(token), binding, task_id, step_id, approver.strip(),
                    issued.isoformat(),
                    datetime.fromtimestamp(expires, timezone.utc).isoformat(),
                ),
            )
            connection.commit()
        return token

    def issue_for_arguments(
        self,
        task_id: str,
        plan,
        approver: str,
        ttl_seconds: int,
        step_id: str,
        args_payload: str | bytes,
    ) -> str:
        """Issue a step approval using a digest computed from exact strict-JSON input."""
        if not isinstance(step_id, str) or not step_id:
            raise ValueError("A step identifier is required")
        _arguments, _canonical_json, args_sha256 = parse_and_bind(args_payload)
        return self.issue(
            task_id, plan, approver, ttl_seconds,
            step_id=step_id, args_sha256=args_sha256,
        )

    @staticmethod
    def consume(connection: sqlite3.Connection, token: object, binding: str, now: datetime) -> None:
        """Atomically validate and consume one approval inside an open transaction.

        A mismatched binding is refused without consuming the token, so a caller
        cannot burn someone else's approval by presenting it for another operation.
        """
        if not isinstance(token, str) or not token:
            raise ApprovalDenied("An issued approval token is required")
        row = connection.execute(
            "SELECT binding, expires_at, consumed_at FROM approval_tokens WHERE token_hash = ?",
            (_token_hash(token),),
        ).fetchone()
        if row is None:
            raise ApprovalDenied("Unknown approval token")
        if not hmac.compare_digest(row[0], binding):
            raise ApprovalDenied(
                "Approval does not match this task, step, action, resource, risk, plan or arguments"
            )
        if row[2] is not None:
            raise ApprovalDenied("Approval token was already consumed")
        if datetime.fromisoformat(row[1]) <= now:
            raise ApprovalDenied("Approval token has expired")
        cursor = connection.execute(
            "UPDATE approval_tokens SET consumed_at = ? WHERE token_hash = ? AND consumed_at IS NULL",
            (now.isoformat(), _token_hash(token)),
        )
        if cursor.rowcount != 1:
            raise ApprovalDenied("Approval token was already consumed")
