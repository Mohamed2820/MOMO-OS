"""Durable step-execution journal; deliberately does not execute tools.

The journal records intent and outcomes around an external executor. A process
found running after a restart is moved to NEEDS_REVIEW, never replayed.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from intelligence.runtime.momo_runtime import Risk


class StepExecutionStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class StepExecution:
    task_id: str
    step_id: str
    risk: Risk
    status: StepExecutionStatus
    attempt: int
    retry_limit: int
    idempotency_key: str
    cancel_requested: bool
    last_error: str | None
    result_sha256: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StepExecutionEvent:
    event_id: int
    task_id: str
    step_id: str
    at: str
    previous: str | None
    current: str
    reason: str


class StepExecutionNotFoundError(KeyError):
    """Raised when a task step has no execution record."""


class StepExecutionJournal:
    """Transactional step ledger sharing the TaskStore SQLite database."""

    MAX_RETRIES = 5

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        if not self.database.is_file():
            raise FileNotFoundError(
                "TaskStore must initialize the task database before the execution journal"
            )
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_step_executions (
                    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                    step_id TEXT NOT NULL CHECK(length(trim(step_id)) > 0),
                    risk TEXT NOT NULL CHECK(risk IN ('R0','R1','R2','R3','R4')),
                    status TEXT NOT NULL CHECK(status IN
                        ('ready','running','succeeded','failed','needs_review','cancelled')),
                    attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt >= 0),
                    retry_limit INTEGER NOT NULL DEFAULT 0
                        CHECK(retry_limit >= 0 AND retry_limit <= 5),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                        CHECK(cancel_requested IN (0,1)),
                    last_error TEXT,
                    result_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(task_id, step_id)
                );

                CREATE TABLE IF NOT EXISTS task_step_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    at TEXT NOT NULL,
                    previous TEXT,
                    current TEXT NOT NULL,
                    reason TEXT NOT NULL CHECK(length(trim(reason)) > 0),
                    FOREIGN KEY(task_id, step_id)
                        REFERENCES task_step_executions(task_id, step_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_step_events_task
                    ON task_step_events(task_id, step_id, event_id);
                CREATE INDEX IF NOT EXISTS idx_step_execution_status
                    ON task_step_executions(status, updated_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _record(row: sqlite3.Row) -> StepExecution:
        return StepExecution(
            task_id=row["task_id"],
            step_id=row["step_id"],
            risk=Risk(row["risk"]),
            status=StepExecutionStatus(row["status"]),
            attempt=row["attempt"],
            retry_limit=row["retry_limit"],
            idempotency_key=row["idempotency_key"],
            cancel_requested=bool(row["cancel_requested"]),
            last_error=row["last_error"],
            result_sha256=row["result_sha256"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        task_id: str,
        step_id: str,
        previous: str | None,
        current: str,
        reason: str,
        at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO task_step_events(task_id, step_id, at, previous, current, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, step_id, at, previous, current, reason.strip()),
        )

    def register_step(
        self,
        task_id: str,
        step_id: str,
        risk: Risk,
        idempotency_key: str,
        retry_limit: int = 0,
    ) -> StepExecution:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Task ID must not be empty")
        if not isinstance(step_id, str) or not step_id.strip():
            raise ValueError("Step ID must not be empty")
        if not isinstance(risk, Risk):
            raise ValueError("Risk must be a Risk value")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("A stable idempotency key is required")
        if len(idempotency_key) > 256:
            raise ValueError("Idempotency key exceeds 256 characters")
        if not isinstance(retry_limit, int) or not 0 <= retry_limit <= self.MAX_RETRIES:
            raise ValueError("Retry limit must be between 0 and 5")
        if risk not in {Risk.R0, Risk.R1} and retry_limit:
            raise ValueError("Automatic retries are restricted to R0/R1 read-only work")

        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO task_step_executions(
                    task_id, step_id, risk, status, attempt, retry_limit,
                    idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, 'ready', 0, ?, ?, ?, ?)
                """,
                (task_id, step_id, risk.value, retry_limit, idempotency_key, now, now),
            )
            self._event(connection, task_id, step_id, None, "ready", "Step registered", now)
            connection.commit()
        return self.get_step(task_id, step_id)

    def get_step(self, task_id: str, step_id: str) -> StepExecution:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
        if row is None:
            raise StepExecutionNotFoundError((task_id, step_id))
        return self._record(row)

    def list_events(self, task_id: str, step_id: str) -> tuple[StepExecutionEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, task_id, step_id, at, previous, current, reason
                FROM task_step_events WHERE task_id = ? AND step_id = ?
                ORDER BY event_id
                """,
                (task_id, step_id),
            ).fetchall()
        return tuple(StepExecutionEvent(**dict(row)) for row in rows)

    def start_step(self, task_id: str, step_id: str, retry: bool = False) -> StepExecution:
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
            if row is None:
                raise StepExecutionNotFoundError((task_id, step_id))
            status = StepExecutionStatus(row["status"])
            if status == StepExecutionStatus.READY:
                if retry:
                    raise ValueError("A ready step is not a retry")
            elif status == StepExecutionStatus.FAILED:
                if not retry:
                    raise ValueError("Retry must be explicitly requested")
                if Risk(row["risk"]) not in {Risk.R0, Risk.R1}:
                    raise ValueError("Side-effecting steps cannot be automatically retried")
                if row["attempt"] > row["retry_limit"]:
                    raise ValueError("Retry budget exhausted")
            else:
                raise ValueError(f"Step cannot start from state: {status.value}")

            connection.execute(
                """
                UPDATE task_step_executions
                SET status = 'running', attempt = attempt + 1,
                    cancel_requested = 0, last_error = NULL, updated_at = ?
                WHERE task_id = ? AND step_id = ?
                """,
                (now, task_id, step_id),
            )
            self._event(connection, task_id, step_id, status.value, "running",
                        "Step attempt started", now)
            connection.commit()
        return self.get_step(task_id, step_id)

    def finish_step(
        self,
        task_id: str,
        step_id: str,
        success: bool,
        result_sha256: str | None = None,
        error: str | None = None,
    ) -> StepExecution:
        if not isinstance(success, bool):
            raise ValueError("Success must be boolean")
        if result_sha256 is not None:
            if (not isinstance(result_sha256, str) or len(result_sha256) != 64
                    or any(char not in "0123456789abcdef" for char in result_sha256.lower())):
                raise ValueError("Result digest must be a SHA-256 hex string")
        if not success and (not isinstance(error, str) or not error.strip()):
            raise ValueError("A failed attempt requires an error summary")

        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
            if row is None:
                raise StepExecutionNotFoundError((task_id, step_id))
            if row["status"] != StepExecutionStatus.RUNNING.value:
                raise ValueError("Only a running step can be finished")

            if success:
                target = StepExecutionStatus.SUCCEEDED
                reason = "Step completed and result recorded"
                stored_error = None
            elif Risk(row["risk"]) in {Risk.R0, Risk.R1}:
                target = StepExecutionStatus.FAILED
                reason = "Read-only step failed: " + error.strip()
                stored_error = error.strip()[:2000]
            else:
                target = StepExecutionStatus.NEEDS_REVIEW
                reason = "Side-effecting step failed; outcome requires reconciliation: " + error.strip()
                stored_error = error.strip()[:2000]

            connection.execute(
                """
                UPDATE task_step_executions
                SET status = ?, result_sha256 = ?, last_error = ?, updated_at = ?
                WHERE task_id = ? AND step_id = ?
                """,
                (target.value, result_sha256 if success else None, stored_error,
                 now, task_id, step_id),
            )
            self._event(connection, task_id, step_id, "running", target.value, reason, now)
            connection.commit()
        return self.get_step(task_id, step_id)

    def request_cancel(self, task_id: str, step_id: str) -> StepExecution:
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
            if row is None:
                raise StepExecutionNotFoundError((task_id, step_id))
            status = StepExecutionStatus(row["status"])
            if status == StepExecutionStatus.READY:
                connection.execute(
                    """
                    UPDATE task_step_executions SET status = 'cancelled', updated_at = ?
                    WHERE task_id = ? AND step_id = ?
                    """,
                    (now, task_id, step_id),
                )
                self._event(connection, task_id, step_id, "ready", "cancelled",
                            "Cancelled before execution began", now)
            elif status == StepExecutionStatus.RUNNING:
                if not row["cancel_requested"]:
                    connection.execute(
                        """
                        UPDATE task_step_executions SET cancel_requested = 1, updated_at = ?
                        WHERE task_id = ? AND step_id = ?
                        """,
                        (now, task_id, step_id),
                    )
                    self._event(connection, task_id, step_id, "running", "running",
                                "Cancellation requested; executor must acknowledge safely", now)
            else:
                raise ValueError(f"Step cannot be cancelled from state: {status.value}")
            connection.commit()
        return self.get_step(task_id, step_id)

    def acknowledge_cancel(
        self, task_id: str, step_id: str, confirmed_no_side_effect: bool
    ) -> StepExecution:
        if confirmed_no_side_effect is not True:
            raise ValueError("Cancellation requires confirmation that no side effect occurred")
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM task_step_executions WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
            if row is None:
                raise StepExecutionNotFoundError((task_id, step_id))
            if row["status"] != "running" or not row["cancel_requested"]:
                raise ValueError("No pending cancellation exists for this running step")
            connection.execute(
                """
                UPDATE task_step_executions SET status = 'cancelled', updated_at = ?
                WHERE task_id = ? AND step_id = ?
                """,
                (now, task_id, step_id),
            )
            self._event(connection, task_id, step_id, "running", "cancelled",
                        "Executor confirmed cancellation before side effects", now)
            connection.commit()
        return self.get_step(task_id, step_id)

    def recover_interrupted(self) -> tuple[StepExecution, ...]:
        """Quarantine all in-flight steps after restart; never replay them."""
        now = self._now()
        recovered: list[tuple[str, str]] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT task_id, step_id FROM task_step_executions
                WHERE status = 'running'
                ORDER BY task_id, step_id
                """
            ).fetchall()
            for row in rows:
                task_id, step_id = row["task_id"], row["step_id"]
                connection.execute(
                    """
                    UPDATE task_step_executions
                    SET status = 'needs_review', updated_at = ?
                    WHERE task_id = ? AND step_id = ?
                    """,
                    (now, task_id, step_id),
                )
                self._event(
                    connection, task_id, step_id, "running", "needs_review",
                    "Process restart interrupted execution; reconcile before any retry", now,
                )
                recovered.append((task_id, step_id))
            connection.commit()
        return tuple(self.get_step(task_id, step_id) for task_id, step_id in recovered)
