import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence.runtime.momo_runtime import Approval, CapabilityGrant, Risk, TaskStatus
from intelligence.runtime.orchestrator import AgentRegistry, AgentSpec, Plan, PlanStep
from intelligence.runtime.task_coordinator import TaskCoordinator


class TaskCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        registry = AgentRegistry()
        registry.register(AgentSpec(
            role="researcher", domains=frozenset({"research"}),
            capabilities=frozenset({"web.read"}), max_risk=Risk.R1,
        ))
        registry.register(AgentSpec(
            role="operator", domains=frozenset({"device"}),
            capabilities=frozenset({"device.inspect"}), max_risk=Risk.R4,
        ))
        self.task_db = root / "tasks.sqlite3"
        self.permission_db = root / "permissions.sqlite3"
        self.registry = registry
        self.coordinator = TaskCoordinator(registry, self.task_db, self.permission_db)
        self.plan = Plan("Inspect public system status", (
            PlanStep("inspect", "Inspect system status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
        ))

    def tearDown(self):
        self.temp.cleanup()

    def test_create_task_validates_and_persists_lifecycle(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.assertEqual(task.status, TaskStatus.PLANNED)
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.PLANNED)

    def test_task_and_plan_are_committed_atomically(self):
        with sqlite3.connect(self.task_db) as connection:
            connection.execute("""
                CREATE TRIGGER reject_plan BEFORE INSERT ON task_plans
                BEGIN SELECT RAISE(ABORT, 'injected plan insert failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.assertEqual(self.coordinator.tasks.list_tasks(), [])

    def test_persisted_plan_round_trips_after_coordinator_restart(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        restarted = TaskCoordinator(self.registry, self.task_db, self.permission_db)
        self.assertEqual(restarted.get_persisted_plan(task.task_id), self.plan)

    def test_persisted_plan_digest_detects_database_tampering(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        with sqlite3.connect(self.task_db) as connection:
            connection.execute(
                "UPDATE task_plans SET plan_json = ? WHERE task_id = ?",
                ('{"goal":"tampered"}', task.task_id),
            )
        with self.assertRaisesRegex(ValueError, "digest verification"):
            self.coordinator.get_persisted_plan(task.task_id)

    def test_high_risk_task_waits_for_approval(self):
        plan = Plan("Inspect device", (
            PlanStep("inspect", "Inspect device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R3, plan)
        self.assertEqual(task.status, TaskStatus.AWAITING_APPROVAL)

    def test_task_goal_must_match_plan(self):
        with self.assertRaises(ValueError):
            self.coordinator.create_task("Different goal", Risk.R1, self.plan)

    def test_step_cannot_exceed_task_risk(self):
        with self.assertRaises(ValueError):
            self.coordinator.create_task(self.plan.goal, Risk.R0, self.plan)

    def test_ready_steps_follow_dependencies(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        ready = self.coordinator.get_ready_steps(task.task_id, self.plan)
        self.assertEqual([step.step_id for step in ready], ["inspect"])

    def test_step_is_denied_without_capability_grant(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        decision = self.coordinator.authorize_step(task.task_id, self.plan, "inspect")
        self.assertFalse(decision.allowed)

    def test_matching_scoped_grant_authorizes_one_step(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.coordinator.permissions.add_grant(CapabilityGrant(
            subject="researcher", action="research", resource=task.task_id,
            risk=Risk.R1, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            max_uses=1,
        ))
        first = self.coordinator.authorize_step(task.task_id, self.plan, "inspect")
        second = self.coordinator.authorize_step(task.task_id, self.plan, "inspect")
        self.assertTrue(first.allowed)
        self.assertFalse(second.allowed)

    def test_high_risk_step_requires_matching_explicit_approval(self):
        plan = Plan("Inspect device", (
            PlanStep("inspect", "Inspect device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R3, plan)
        self.coordinator.permissions.add_grant(CapabilityGrant(
            subject="operator", action="device", resource=task.task_id,
            risk=Risk.R3, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))
        denied = self.coordinator.authorize_step(task.task_id, plan, "inspect")
        self.assertFalse(denied.allowed)
        approval = Approval("operator", "device", task.task_id, True)
        allowed = self.coordinator.authorize_step(
            task.task_id, plan, "inspect", approval=approval
        )
        self.assertTrue(allowed.allowed)

    def test_plan_from_another_task_is_rejected(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        other = Plan("Different task", (
            PlanStep("inspect", "Inspect", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
        ))
        with self.assertRaises(ValueError):
            self.coordinator.get_ready_steps(task.task_id, other)

    def test_same_goal_but_modified_plan_is_rejected(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        altered = Plan(self.plan.goal, (
            PlanStep("inspect", "Different operation", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
        ))
        with self.assertRaises(ValueError):
            self.coordinator.authorize_step(task.task_id, altered, "inspect")


if __name__ == "__main__":
    unittest.main()
