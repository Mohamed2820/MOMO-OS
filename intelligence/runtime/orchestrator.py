"""Deterministic multi-agent plan validation and scheduling primitives.

No model calls or tool side effects happen here. The orchestrator validates a
bounded plan before an execution adapter is allowed to dispatch any step.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from intelligence.runtime.momo_runtime import Risk


_RISK_LEVEL = {Risk.R0: 0, Risk.R1: 1, Risk.R2: 2, Risk.R3: 3, Risk.R4: 4}


@dataclass(frozen=True)
class AgentSpec:
    role: str
    domains: frozenset[str]
    capabilities: frozenset[str]
    max_risk: Risk = Risk.R1


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    description: str
    agent_role: str
    domain: str
    required_capabilities: frozenset[str] = frozenset()
    risk: Risk = Risk.R0
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    goal: str
    steps: tuple[PlanStep, ...]
    max_steps: int = 20
    max_delegation_depth: int = 2


class PlanValidationError(ValueError):
    """Raised when a plan violates structural or agent capability policy."""


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}

    def register(self, agent: AgentSpec) -> None:
        if not agent.role.strip():
            raise ValueError("Agent role must not be empty")
        if agent.role in self._agents:
            raise ValueError(f"Agent role already registered: {agent.role}")
        self._agents[agent.role] = agent

    def get(self, role: str) -> AgentSpec:
        try:
            return self._agents[role]
        except KeyError as exc:
            raise PlanValidationError(f"Unknown agent role: {role}") from exc

    def roles(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))


class PlanValidator:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def validate(self, plan: Plan) -> None:
        if not plan.goal.strip():
            raise PlanValidationError("Plan goal must not be empty")
        if not plan.steps:
            raise PlanValidationError("Plan must contain at least one step")
        if plan.max_steps < 1 or len(plan.steps) > plan.max_steps:
            raise PlanValidationError("Plan exceeds its step budget")
        if plan.max_delegation_depth < 0:
            raise PlanValidationError("Delegation depth cannot be negative")

        by_id: dict[str, PlanStep] = {}
        for step in plan.steps:
            if not step.step_id.strip():
                raise PlanValidationError("Step ID must not be empty")
            if step.step_id in by_id:
                raise PlanValidationError(f"Duplicate step ID: {step.step_id}")
            if not step.description.strip():
                raise PlanValidationError(f"Step {step.step_id} has no description")
            if step.step_id in step.depends_on:
                raise PlanValidationError(f"Step {step.step_id} depends on itself")
            by_id[step.step_id] = step

        for step in plan.steps:
            missing = set(step.depends_on) - by_id.keys()
            if missing:
                raise PlanValidationError(
                    f"Step {step.step_id} has unknown dependencies: {sorted(missing)}"
                )
            agent = self.registry.get(step.agent_role)
            if step.domain not in agent.domains:
                raise PlanValidationError(
                    f"Agent {agent.role} is not approved for domain {step.domain}"
                )
            if not step.required_capabilities.issubset(agent.capabilities):
                absent = step.required_capabilities - agent.capabilities
                raise PlanValidationError(
                    f"Agent {agent.role} lacks capabilities: {sorted(absent)}"
                )
            if _RISK_LEVEL[step.risk] > _RISK_LEVEL[agent.max_risk]:
                raise PlanValidationError(
                    f"Step {step.step_id} exceeds agent risk ceiling"
                )

        self._validate_acyclic(by_id)

    @staticmethod
    def _validate_acyclic(steps: Mapping[str, PlanStep]) -> None:
        remaining = {key: set(step.depends_on) for key, step in steps.items()}
        completed: set[str] = set()
        while remaining:
            ready = {key for key, deps in remaining.items() if deps <= completed}
            if not ready:
                raise PlanValidationError("Plan contains a dependency cycle")
            completed.update(ready)
            for key in ready:
                del remaining[key]


def ready_steps(
    plan: Plan,
    completed_step_ids: Iterable[str],
) -> tuple[PlanStep, ...]:
    """Return deterministic ready steps whose dependencies have completed."""
    completed = set(completed_step_ids)
    known = {step.step_id for step in plan.steps}
    unknown = completed - known
    if unknown:
        raise ValueError(f"Unknown completed step IDs: {sorted(unknown)}")
    return tuple(
        sorted(
            (
                step for step in plan.steps
                if step.step_id not in completed
                and set(step.depends_on).issubset(completed)
            ),
            key=lambda step: step.step_id,
        )
    )
