import unittest

from intelligence.runtime.momo_runtime import Risk
from intelligence.runtime.orchestrator import (
    AgentRegistry, AgentSpec, Plan, PlanStep, PlanValidationError,
    PlanValidator, ready_steps,
)


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.registry.register(AgentSpec(
            role="researcher",
            domains=frozenset({"research"}),
            capabilities=frozenset({"web.read"}),
            max_risk=Risk.R1,
        ))
        self.registry.register(AgentSpec(
            role="writer",
            domains=frozenset({"writing"}),
            capabilities=frozenset({"document.write"}),
            max_risk=Risk.R2,
        ))
        self.validator = PlanValidator(self.registry)

    def test_valid_dag(self):
        plan = Plan("Prepare a sourced report", (
            PlanStep("research", "Gather sources", "researcher", "research",
                     frozenset({"web.read"})),
            PlanStep("draft", "Write report", "writer", "writing",
                     frozenset({"document.write"}), depends_on=("research",)),
        ))
        self.validator.validate(plan)

    def test_unknown_role_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "Do work", "unknown", "research"),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_capability_escalation_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "Read secrets", "researcher", "research",
                     frozenset({"device.root"})),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_domain_mismatch_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "Change settings", "researcher", "device"),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_risk_ceiling_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "Send message", "researcher", "research", risk=Risk.R3),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_dependency_cycle_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "A", "researcher", "research", depends_on=("b",)),
            PlanStep("b", "B", "writer", "writing", depends_on=("a",)),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_step_budget_enforced(self):
        plan = Plan("Task", (
            PlanStep("a", "A", "researcher", "research"),
            PlanStep("b", "B", "writer", "writing"),
        ), max_steps=1)
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_ready_steps_are_dependency_aware_and_sorted(self):
        plan = Plan("Task", (
            PlanStep("b", "B", "writer", "writing", depends_on=("a",)),
            PlanStep("c", "C", "writer", "writing"),
            PlanStep("a", "A", "researcher", "research"),
        ))
        ready = ready_steps(plan, set())
        self.assertEqual([step.step_id for step in ready], ["a", "c"])
        after_a = ready_steps(plan, {"a"})
        self.assertEqual([step.step_id for step in after_a], ["b", "c"])

    def test_delegation_depth_budget_enforced(self):
        plan = Plan("Task", (
            PlanStep("a", "Delegate too deeply", "researcher", "research",
                     delegation_depth=3),
        ), max_delegation_depth=2)
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_duplicate_step_ids_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "First", "researcher", "research"),
            PlanStep("a", "Duplicate", "writer", "writing"),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_unknown_dependency_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "Depends on missing", "researcher", "research",
                     depends_on=("missing",)),
        ))
        with self.assertRaises(PlanValidationError):
            self.validator.validate(plan)

    def test_unknown_completed_step_rejected(self):
        plan = Plan("Task", (
            PlanStep("a", "A", "researcher", "research"),
        ))
        with self.assertRaises(ValueError):
            ready_steps(plan, {"missing"})


if __name__ == "__main__":
    unittest.main()
