"""Policy-aware bridge between durable tasks, plans and capability grants."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .momo_runtime import (
    Approval, AuthorizationDecision, Risk, Task, TaskStatus, ToolRequest,
)
from .orchestrator import AgentRegistry, Plan, PlanStep, PlanValidator, ready_steps
from .persistent_permission_broker import PersistentPermissionBroker
from .task_store import TaskStore
from intelligence.execution.step_journal import (
    StepExecution, StepExecutionEvent, StepExecutionJournal, StepExecutionStatus,
)


_RISK_LEVEL = {Risk.R0: 0, Risk.R1: 1, Risk.R2: 2, Risk.R3: 3, Risk.R4: 4}


def _plan_document(plan: Plan) -> dict:
    """Canonical, JSON-safe representation used to bind a plan to its task."""
    return {
        "goal": plan.goal.strip(),
        "max_steps": plan.max_steps,
        "max_delegation_depth": plan.max_delegation_depth,
        "steps": [
            {
                "step_id": step.step_id,
                "description": step.description,
                "agent_role": step.agent_role,
                "domain": step.domain,
                "required_capabilities": sorted(step.required_capabilities),
                "risk": step.risk.value,
                "depends_on": list(step.depends_on),
                "delegation_depth": step.delegation_depth,
            }
            for step in plan.steps
        ],
    }


def _canonical_plan_json(plan: Plan) -> str:
    return json.dumps(
        _plan_document(plan), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _plan_digest(plan: Plan) -> tuple[str, str]:
    encoded = _canonical_plan_json(plan)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), encoded


def _plan_from_document(document: dict) -> Plan:
    try:
        steps = tuple(
            PlanStep(
                step_id=item["step_id"],
                description=item["description"],
                agent_role=item["agent_role"],
                domain=item["domain"],
                required_capabilities=frozenset(item["required_capabilities"]),
                risk=Risk(item["risk"]),
                depends_on=tuple(item["depends_on"]),
                delegation_depth=int(item["delegation_depth"]),
            )
            for item in document["steps"]
        )
        return Plan(
            goal=document["goal"],
            steps=steps,
            max_steps=int(document["max_steps"]),
            max_delegation_depth=int(document["max_delegation_depth"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Persisted task plan has an invalid structure") from exc


class TaskCoordinator:
    """Validate, atomically persist, schedule and authorize plans; never dispatch tools."""

    def __init__(
        self,
        registry: AgentRegistry,
        task_database: str | Path = "/var/lib/momo/tasks.sqlite3",
        permission_database: str | Path = "/var/lib/momo/permissions.sqlite3",
    ) -> None:
        self.validator = PlanValidator(registry)
        self.tasks = TaskStore(task_database)
        self.permissions = PersistentPermissionBroker(permission_database)
        self.execution = StepExecutionJournal(self.tasks.database)
        with sqlite3.connect(str(self.tasks.database), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_plans (
                    task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
                    plan_sha256 TEXT NOT NULL,
                    plan_json TEXT NOT NULL
                )
                """
            )

    def create_task(self, goal: str, risk: Risk, plan: Plan) -> Task:
        """Persist task, accepted plan and initial lifecycle events atomically."""
        self.validator.validate(plan)
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("Task goal must not be empty")
        if not isinstance(risk, Risk):
            raise ValueError("Task risk must be a Risk value")
        if plan.goal.strip() != goal.strip():
            raise ValueError("Task goal must match the validated plan goal")
        if any(_RISK_LEVEL[step.risk] > _RISK_LEVEL[risk] for step in plan.steps):
            raise ValueError("A plan step exceeds the task risk ceiling")

        digest, encoded = _plan_digest(plan)
        task = Task(goal=goal.strip(), risk=risk)
        created_at = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(str(self.tasks.database), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO tasks(task_id, goal, risk, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task.task_id, task.goal, task.risk.value, task.status.value,
                 created_at, created_at),
            )
            connection.execute(
                "INSERT INTO task_plans(task_id, plan_sha256, plan_json) VALUES (?, ?, ?)",
                (task.task_id, digest, encoded),
            )

            self.execution.register_plan_steps(
                connection,
                task.task_id,
                digest,
                tuple((step.step_id, step.risk) for step in plan.steps),
            )

            task.transition(
                TaskStatus.CLASSIFIED,
                "Plan passed structural and agent-policy validation",
            )
            task.transition(
                TaskStatus.PLANNED,
                "Validated plan accepted by task coordinator",
            )
            if risk in {Risk.R3, Risk.R4}:
                task.transition(
                    TaskStatus.AWAITING_APPROVAL,
                    "High-risk task requires explicit approval before execution",
                )

            updated_at = task.events[-1].at.isoformat()
            connection.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                (task.status.value, updated_at, task.task_id),
            )
            connection.executemany(
                """
                INSERT INTO task_events(task_id, at, previous, current, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (task.task_id, event.at.isoformat(), event.previous.value,
                     event.current.value, event.reason)
                    for event in task.events
                ],
            )
            connection.commit()
        return self.tasks.get_task(task.task_id)

    def get_persisted_plan(self, task_id: str) -> Plan:
        """Load the exact accepted plan after restart and verify its stored digest."""
        with sqlite3.connect(str(self.tasks.database), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT plan_sha256, plan_json FROM task_plans WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise ValueError("No persisted plan exists for this task")

        encoded = row["plan_json"]
        actual_digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_digest, row["plan_sha256"]):
            raise ValueError("Persisted task plan digest verification failed")

        try:
            document = json.loads(encoded)
        except json.JSONDecodeError as exc:
            raise ValueError("Persisted task plan is not valid JSON") from exc
        plan = _plan_from_document(document)
        if _canonical_plan_json(plan) != encoded:
            raise ValueError("Persisted task plan is not in canonical form")
        self.validator.validate(plan)
        return plan

    def get_ready_steps(
        self, task_id: str, plan: Plan
    ) -> tuple[PlanStep, ...]:
        """Derive readiness only from durable, verified step execution records."""
        task = self.tasks.get_task(task_id)
        if task.status not in {
            TaskStatus.PLANNED, TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING
        }:
            raise ValueError(f"Task is not schedulable in state: {task.status.value}")
        self._validate_task_plan(task, plan)

        records = self.execution.list_steps(task_id)
        by_id = {record.step_id: record for record in records}
        expected = {step.step_id: step for step in plan.steps}
        if set(by_id) != set(expected):
            raise ValueError("Persisted execution ledger does not match the immutable plan")
        for step_id, step in expected.items():
            if by_id[step_id].risk != step.risk:
                raise ValueError(f"Persisted risk does not match plan step: {step_id}")

        completed = {
            step_id for step_id, record in by_id.items()
            if record.status is StepExecutionStatus.SUCCEEDED
        }
        dependency_ready = ready_steps(plan, completed)
        return tuple(
            step for step in dependency_ready
            if by_id[step.step_id].status is StepExecutionStatus.READY
        )

    def authorize_step(
        self,
        task_id: str,
        plan: Plan,
        step_id: str,
        approval: Approval | None = None,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        """Check a LOW-risk (R0-R2) grant for one step. Never starts anything.

        Plain Approval objects are refused: an approval is valid only as a
        server-issued token consumed by ExecutionGate. R3/R4 steps are refused
        here for the same reason.
        """
        task = self.tasks.get_task(task_id)
        if task.status not in {
            TaskStatus.PLANNED, TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING
        }:
            return AuthorizationDecision(False, f"Task is not authorizable: {task.status.value}")
        self._validate_task_plan(task, plan)
        step = next((item for item in plan.steps if item.step_id == step_id), None)
        if step is None:
            return AuthorizationDecision(False, "Step is not part of the validated plan")
        if approval is not None:
            return AuthorizationDecision(
                False,
                "Plain approval objects are not accepted; approvals must be issued "
                "tokens consumed through ExecutionGate",
            )
        if step.risk in {Risk.R3, Risk.R4}:
            return AuthorizationDecision(
                False, "R3/R4 steps require ExecutionGate with an issued approval token"
            )

        request = ToolRequest(
            subject=step.agent_role,
            action=step.domain,
            resource=task_id,
            risk=step.risk,
        )
        return self.permissions.authorize(request, approval=None, now=now)

    def _validate_task_plan(self, task: Task, plan: Plan) -> None:
        self.validator.validate(plan)
        if task.goal != plan.goal.strip():
            raise ValueError("Supplied plan does not belong to this task")
        if any(_RISK_LEVEL[step.risk] > _RISK_LEVEL[task.risk] for step in plan.steps):
            raise ValueError("A plan step exceeds the persisted task risk ceiling")
        stored = self.get_persisted_plan(task.task_id)
        supplied_digest, _ = _plan_digest(plan)
        stored_digest, _ = _plan_digest(stored)
        if not hmac.compare_digest(supplied_digest, stored_digest):
            raise ValueError("Supplied plan does not match the immutable task plan")

    def get_step_execution(self, task_id: str, step_id: str) -> StepExecution:
        """Return the durable execution record for one accepted plan step."""
        task = self.tasks.get_task(task_id)
        self.get_persisted_plan(task_id)
        return self.execution.get_step(task.task_id, step_id)

    def get_step_execution_events(
        self, task_id: str, step_id: str
    ) -> tuple[StepExecutionEvent, ...]:
        """Return append-only execution history for one accepted plan step."""
        self.get_step_execution(task_id, step_id)
        return self.execution.list_events(task_id, step_id)

    def recover_interrupted_steps(self) -> tuple[StepExecution, ...]:
        """Quarantine in-flight step records after a confirmed service restart."""
        return self.execution.recover_interrupted()
