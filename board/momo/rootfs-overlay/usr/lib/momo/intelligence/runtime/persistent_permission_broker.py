"""SQLite-backed capability grant broker with durable replay limits.

This is a policy evaluator and audit journal. It does not execute tools or
replace native operating-system permission enforcement.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .momo_runtime import (
    Approval,
    AuthorizationDecision,
    CapabilityGrant,
    Risk,
    ToolRequest,
)


class PersistentPermissionBroker:
    """Persist grants, revocation, usage counters and authorization decisions."""

    SCHEMA_VERSION = 1
    APPROVAL_MODES = {"per_call", "standing_scoped", "never_allowed"}

    def __init__(self, database: str | Path = "/var/lib/momo/permissions.sqlite3"):
        self.database = Path(database)
        self.database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._initialize()
        try:
            os.chmod(self.database, 0o600)
        except OSError:
            # Some managed/read-only filesystems do not permit chmod.
            pass

    def _connect(self):
        connection = sqlite3.connect(str(self.database), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > self.SCHEMA_VERSION:
                raise RuntimeError("Permission database schema is newer than this runtime")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS capability_grants (
                    grant_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    risk TEXT NOT NULL CHECK(risk IN ('R0','R1','R2','R3','R4')),
                    expires_at TEXT NOT NULL,
                    approval_mode TEXT NOT NULL,
                    max_uses INTEGER NOT NULL CHECK(max_uses >= 1),
                    uses INTEGER NOT NULL DEFAULT 0 CHECK(uses >= 0),
                    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1))
                );

                CREATE TABLE IF NOT EXISTS authorization_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    allowed INTEGER NOT NULL CHECK(allowed IN (0,1)),
                    reason TEXT NOT NULL,
                    grant_id TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_grants_scope
                    ON capability_grants(subject, action, resource, risk);
                CREATE INDEX IF NOT EXISTS idx_authorization_events_time
                    ON authorization_events(event_id DESC);
                """
            )
            connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @staticmethod
    def _validate_grant(grant: CapabilityGrant) -> None:
        for name in ("grant_id", "subject", "action", "resource"):
            if not isinstance(getattr(grant, name), str) or not getattr(grant, name).strip():
                raise ValueError(f"Grant {name} must not be empty")
        if not isinstance(grant.risk, Risk):
            raise ValueError("Grant risk must be a Risk value")
        if grant.expires_at.tzinfo is None or grant.expires_at.utcoffset() is None:
            raise ValueError("Grant expiry must be timezone-aware")
        if grant.approval_mode not in PersistentPermissionBroker.APPROVAL_MODES:
            raise ValueError("Unsupported approval mode")
        if not isinstance(grant.max_uses, int) or grant.max_uses < 1:
            raise ValueError("Grant max_uses must be a positive integer")

    @staticmethod
    def _request_fields(request: ToolRequest):
        if not isinstance(request.risk, Risk):
            raise ValueError("Request risk must be a Risk value")
        for name in ("subject", "action", "resource"):
            if not isinstance(getattr(request, name), str) or not getattr(request, name).strip():
                raise ValueError(f"Request {name} must not be empty")
        return request.subject, request.action, request.resource, request.risk.value

    def add_grant(self, grant: CapabilityGrant) -> None:
        self._validate_grant(grant)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO capability_grants(
                    grant_id, subject, action, resource, risk, expires_at,
                    approval_mode, max_uses, uses, revoked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    grant.grant_id, grant.subject, grant.action, grant.resource,
                    grant.risk.value, grant.expires_at.isoformat(),
                    grant.approval_mode, grant.max_uses,
                ),
            )

    def revoke(self, grant_id: str) -> bool:
        if not isinstance(grant_id, str) or not grant_id.strip():
            raise ValueError("Grant ID must not be empty")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT subject, action, resource, risk FROM capability_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
            cursor = connection.execute(
                "UPDATE capability_grants SET revoked = 1 WHERE grant_id = ? AND revoked = 0",
                (grant_id,),
            )
            changed = cursor.rowcount > 0
            if changed and row is not None:
                connection.execute(
                    """
                    INSERT INTO authorization_events(
                        at, subject, action, resource, risk, allowed, reason, grant_id
                    ) VALUES (?, ?, ?, ?, ?, 0, 'Capability grant revoked', ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        row["subject"], row["action"], row["resource"],
                        row["risk"], grant_id,
                    ),
                )
            connection.commit()
        return changed

    def _audit(self, connection, request, allowed, reason, grant_id=None, at=None):
        connection.execute(
            """
            INSERT INTO authorization_events(
                at, subject, action, resource, risk, allowed, reason, grant_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (at or datetime.now(timezone.utc)).isoformat(),
                request.subject, request.action, request.resource, request.risk.value,
                1 if allowed else 0, reason, grant_id,
            ),
        )

    def authorize(
        self,
        request: ToolRequest,
        approval: Approval | None = None,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        self._request_fields(request)
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            reason = "Authorization time must be timezone-aware"
            with self._connect() as connection:
                self._audit(connection, request, False, reason)
            return AuthorizationDecision(False, reason)

        if request.risk in {Risk.R3, Risk.R4}:
            if approval is None or not approval.approved:
                reason = "Explicit per-action approval required"
                with self._connect() as connection:
                    self._audit(connection, request, False, reason, at=now)
                return AuthorizationDecision(False, reason)
            if (
                approval.subject != request.subject
                or approval.action != request.action
                or approval.resource != request.resource
            ):
                reason = "Approval does not match this request"
                with self._connect() as connection:
                    self._audit(connection, request, False, reason, at=now)
                return AuthorizationDecision(False, reason)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM capability_grants
                WHERE subject = ? AND action = ? AND resource = ? AND risk = ?
                  AND revoked = 0 AND uses < max_uses
                ORDER BY rowid
                """,
                self._request_fields(request),
            ).fetchall()

            for row in rows:
                if row["approval_mode"] not in self.APPROVAL_MODES:
                    continue
                if row["approval_mode"] == "never_allowed":
                    continue
                try:
                    expiry = datetime.fromisoformat(row["expires_at"])
                except ValueError:
                    continue
                if expiry.tzinfo is None or expiry.utcoffset() is None or expiry <= now:
                    continue

                updated = connection.execute(
                    """
                    UPDATE capability_grants SET uses = uses + 1
                    WHERE grant_id = ? AND uses < max_uses AND revoked = 0
                    """,
                    (row["grant_id"],),
                )
                if updated.rowcount == 1:
                    reason = "Matching active persistent capability grant"
                    self._audit(connection, request, True, reason, row["grant_id"], now)
                    connection.commit()
                    return AuthorizationDecision(True, reason, row["grant_id"])

            reason = "No active matching capability grant"
            self._audit(connection, request, False, reason, at=now)
            connection.commit()
        return AuthorizationDecision(False, reason)

    def list_events(self, limit: int = 100) -> list[dict]:
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Audit event limit must be between 1 and 1000")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, at, subject, action, resource, risk,
                       allowed, reason, grant_id
                FROM authorization_events ORDER BY event_id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
