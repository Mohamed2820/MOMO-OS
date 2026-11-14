"""Durable SQLite-backed task journal for the MOMO runtime.

This store persists task state and transition events. It does not execute tools,
grant capabilities, or replace platform-level authorization.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .momo_runtime import GATE_AUTHORITY, Risk, Task, TaskEvent, TaskStatus


class TaskNotFoundError(KeyError):
    """Raised when a requested task does not exist."""


class TaskStore:
    """Transactional task persistence with an append-only transition journal."""

    SCHEMA_VERSION = 1

    def __init__(self, database: str | Path = "/var/lib/momo/tasks.sqlite3") -> None:
        self.database = Path(database)
        self.database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._initialize()
        try:
            os.chmod(self.database, 0o600)
        except OSError:
            # The caller may use a read-only or specially managed filesystem.
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Task database schema {version} is newer than supported "
                    f"schema {self.SCHEMA_VERSION}"
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL CHECK(length(trim(goal)) > 0),
                    risk TEXT NOT NULL CHECK(risk IN ('R0','R1','R2','R3','R4')),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(task_id),
                    at TEXT NOT NULL,
                    previous TEXT NOT NULL,
                    current TEXT NOT NULL,
                    reason TEXT NOT NULL CHECK(length(trim(reason)) > 0)
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_updated
                    ON tasks(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_task_events_task
                    ON task_events(task_id, event_id);
                """
            )
            connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @staticmethod
    def _task_from_rows(task_row: sqlite3.Row, event_rows: Iterable[sqlite3.Row]) -> Task:
        task = Task(
            goal=task_row["goal"],
            risk=Risk(task_row["risk"]),
            task_id=task_row["task_id"],
            status=TaskStatus(task_row["status"]),
        )
        task.events = [
            TaskEvent(
                at=datetime.fromisoformat(row["at"]),
                previous=TaskStatus(row["previous"]),
                current=TaskStatus(row["current"]),
                reason=row["reason"],
            )
            for row in event_rows
        ]
        return task

    def create_task(self, goal: str, risk: Risk) -> Task:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("Task goal must not be empty")
        if not isinstance(risk, Risk):
            raise ValueError("Task risk must be a Risk value")
        task = Task(goal=goal.strip(), risk=risk)
        now = datetime.now().astimezone().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(task_id, goal, risk, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task.task_id, task.goal, task.risk.value, task.status.value, now, now),
            )
        return task

    def get_task(self, task_id: str) -> Task:
        with self._connect() as connection:
            task_row = connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if task_row is None:
                raise TaskNotFoundError(task_id)
            event_rows = connection.execute(
                "SELECT at, previous, current, reason FROM task_events "
                "WHERE task_id = ? ORDER BY event_id",
                (task_id,),
            ).fetchall()
        return self._task_from_rows(task_row, event_rows)

    def list_tasks(self, limit: int = 100) -> list[Task]:
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Task list limit must be between 1 and 1000")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC, task_id LIMIT ?",
                (limit,),
            ).fetchall()
            result = []
            for row in rows:
                events = connection.execute(
                    "SELECT at, previous, current, reason FROM task_events "
                    "WHERE task_id = ? ORDER BY event_id",
                    (row["task_id"],),
                ).fetchall()
                result.append(self._task_from_rows(row, events))
        return result

    @staticmethod
    def _plan_bound(connection: sqlite3.Connection, task_id: str) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'task_plans'"
        ).fetchone()
        if exists is None:
            return False
        return connection.execute(
            "SELECT 1 FROM task_plans WHERE task_id = ?", (task_id,)
        ).fetchone() is not None

    def transition(self, task_id: str, target: TaskStatus, reason: str) -> Task:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._transition_locked(connection, task_id, target, reason, authority=None)
            connection.commit()
        return self.get_task(task_id)

    def _transition_locked(
        self,
        connection: sqlite3.Connection,
        task_id: str,
        target: TaskStatus,
        reason: str,
        authority=None,
    ) -> None:
        """Apply one transition inside the caller's open write transaction.

        Entering EXECUTING is reserved for ExecutionGate: R3/R4 tasks and any
        plan-bound task are refused unless the gate authority is presented.
        """
        row = connection.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        if target is TaskStatus.EXECUTING and authority is not GATE_AUTHORITY:
            if Risk(row["risk"]) in {Risk.R3, Risk.R4}:
                raise ValueError("R3/R4 tasks can start execution only through ExecutionGate")
            if self._plan_bound(connection, task_id):
                raise ValueError("Plan-bound tasks can start execution only through ExecutionGate")

        events = connection.execute(
            "SELECT at, previous, current, reason FROM task_events "
            "WHERE task_id = ? ORDER BY event_id",
            (task_id,),
        ).fetchall()
        task = self._task_from_rows(row, events)
        task.transition(target, reason)
        event = task.events[-1]
        updated_at = event.at.isoformat()

        connection.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
            (task.status.value, updated_at, task_id),
        )
        connection.execute(
            """
            INSERT INTO task_events(task_id, at, previous, current, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, updated_at, event.previous.value, event.current.value, event.reason),
        )
