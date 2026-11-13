"""Policy-aware bridge between durable tasks, plans and capability grants.

This coordinator validates and schedules work but deliberately does not execute
tools, call models, or treat a plan as authorization. Every step still requires
a matching capability grant; R3/R4 steps additionally require per-action
approval through the permission broker.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .momo_runtime import (
    Approval,
    AuthorizationDecision,
    Risk,
    Task,
    TaskStatus,
    ToolRequest,
)
from .orchestrator import (
    AgentRegistry,
    Plan,
    PlanStep,
    PlanValidator,
    ready_steps,
)
from .persistent_permission_broker import PersistentPermissionBroker
from .task_store import TaskStore


_RISK_LEVEL = {Risk.R0: 0, Risk.R1: 1, Risk.R2: 2, Risk.R3: 3, Risk.R4: 4}


class TaskCoordinator:
    """Coordinate plan validation, task persistence and per-step authorization.

    Plans are supplied by the caller and revalidated on each authorization.
    This first version intentionally does not persist plans or dispatch tools.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        task_database: str | Path = "/var/lib/momo/tasks.sqlite3",
        permission_database: str | Path = "/var/lib/momo/permissions.sqlite3",
    ) -> None:
        self.validator = PlanValidator(registry)
        self.tasks = TaskStore(task_database)
        self.permissions = PersistentPermissionBroker(permission_database)

    def create_task(self, goal: str, risk: Risk, plan: Plan) -> Task:
        """Validate a bounded plan and persist its initial classified state."""
        self.validator.validate(plan)
        if plan.goal.strip() != goal.strip():
            raise ValueError("Task goal must match the validated plan goal")
        if any(_RISK_LEVEL[step.risk] > _RISK_LEVEL[risk] for step in plan.steps):
            raise ValueError("A plan step exceeds the task risk ceiling")

        task = self.tasks.create_task(goal, risk)
        task = self.tasks.transition(
            task.task_id, TaskStatus.CLASSIFIED, "Plan passed structural and agent-policy validation"
        )
        task = self.tasks.transition(
            task.task_id, TaskStatus.PLANNED, "Validated plan accepted by task coordinator"
        )
        if risk in {Risk.R3, Risk.R4}:
            task = self.tasks.transition(
                task.task_id, TaskStatus.AWAITING_APPROVAL,
                "High-risk task requires explicit approval before execution",
            )
        return task

    def get_ready_steps(
        self, task_id: str, plan: Plan, completed_step_ids: set[str] | None = None
    ) -> tuple[PlanStep, ...]:
        task = self.tasks.get_task(task_id)
        if task.status not in {
            TaskStatus.PLANNED, TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING
        }:
            raise ValueError(f"Task is not schedulable in state: {task.status.value}")
        self._validate_task_plan(task, plan)
        return ready_steps(plan, completed_step_ids or set())

    def authorize_step(
        self,
        task_id: str,
        plan: Plan,
        step_id: str,
        approval: Approval | None = None,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        """Consume one narrowly scoped grant; never execute the authorized step."""
        task = self.tasks.get_task(task_id)
        if task.status not in {
            TaskStatus.PLANNED, TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING
        }:
            return AuthorizationDecision(False, f"Task is not authorizable: {task.status.value}")
        self._validate_task_plan(task, plan)
        step = next((item for item in plan.steps if item.step_id == step_id), None)
        if step is None:
            return AuthorizationDecision(False, "Step is not part of the validated plan")

        request = ToolRequest(
            subject=step.agent_role,
            action=step.domain,
            resource=task_id,
            risk=step.risk,
        )
        return self.permissions.authorize(request, approval=approval, now=now)

    def _validate_task_plan(self, task: Task, plan: Plan) -> None:
        self.validator.validate(plan)
        if task.goal != plan.goal.strip():
            raise ValueError("Supplied plan does not belong to this task")
        if any(_RISK_LEVEL[step.risk] > _RISK_LEVEL[task.risk] for step in plan.steps):
            raise ValueError("A plan step exceeds the persisted task risk ceiling")
