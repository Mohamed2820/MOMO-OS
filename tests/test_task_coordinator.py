import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence.runtime.momo_runtime import Approval, CapabilityGrant, Risk, TaskStatus
from intelligence.runtime.orchestrator import AgentRegistry, AgentSpec, Plan, PlanStep
from intelligence.runtime.task_coordinator import TaskCoordinator
from intelligence.execution.step_journal import StepExecutionStatus
from intelligence.runtime.approval_store import ApprovalStore
from intelligence.runtime.execution_gate import ExecutionGate
ARGS_PAYLOAD = b'{"operation":"inspect","version":1}'


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

    def _grant(self, task, subject, action, risk):
        self.coordinator.permissions.add_grant(CapabilityGrant(
            subject=subject, action=action, resource=task.task_id, risk=risk,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), max_uses=1,
        ))

    def _start_low_risk(self, task, plan, step_id):
        """Gate-mediated start for R0-R2 work: task execution, then grant-backed step."""
        gate = ExecutionGate(self.coordinator)
        gate.start_task_execution(task.task_id, plan)
        return gate.start_step(task.task_id, plan, step_id, ARGS_PAYLOAD)

    def test_create_task_validates_and_persists_lifecycle(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.assertEqual(task.status, TaskStatus.PLANNED)
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.PLANNED)

    def test_create_task_registers_all_plan_steps(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        execution = self.coordinator.get_step_execution(task.task_id, "inspect")
        self.assertEqual(execution.status, StepExecutionStatus.READY)
        self.assertEqual(execution.attempt, 0)
        self.assertEqual(execution.risk, Risk.R1)
        self.assertEqual(
            len(self.coordinator.get_step_execution_events(task.task_id, "inspect")), 1
        )

    def test_task_plan_and_step_records_are_atomic(self):
        with sqlite3.connect(self.task_db) as connection:
            connection.execute("""
                CREATE TRIGGER reject_step BEFORE INSERT ON task_step_executions
                BEGIN SELECT RAISE(ABORT, 'injected step insert failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.assertEqual(self.coordinator.tasks.list_tasks(), [])
        with sqlite3.connect(self.task_db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM task_plans").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM task_step_executions").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM task_step_events").fetchone()[0], 0)

    def test_restart_recovery_quarantines_coordinator_step(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self._grant(task, "researcher", "research", Risk.R1)
        self._start_low_risk(task, self.plan, "inspect")
        restarted = TaskCoordinator(self.registry, self.task_db, self.permission_db)
        recovered = restarted.recover_interrupted_steps()
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].status, StepExecutionStatus.NEEDS_REVIEW)

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

    def test_ready_steps_follow_persisted_successful_dependencies(self):
        plan = Plan("Inspect then summarize", (
            PlanStep("inspect", "Inspect public status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
            PlanStep("summarize", "Summarize inspected status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1, depends_on=("inspect",)),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R1, plan)
        first_ready = self.coordinator.get_ready_steps(task.task_id, plan)
        self.assertEqual([step.step_id for step in first_ready], ["inspect"])

        self._grant(task, "researcher", "research", Risk.R1)
        self._start_low_risk(task, plan, "inspect")
        self.coordinator.execution.finish_step(task.task_id, "inspect", True)
        second_ready = self.coordinator.get_ready_steps(task.task_id, plan)
        self.assertEqual([step.step_id for step in second_ready], ["summarize"])

    def test_caller_cannot_forge_dependency_completion(self):
        plan = Plan("Inspect then summarize", (
            PlanStep("inspect", "Inspect public status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
            PlanStep("summarize", "Summarize inspected status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1, depends_on=("inspect",)),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R1, plan)
        with self.assertRaises(TypeError):
            self.coordinator.get_ready_steps(task.task_id, plan, {"inspect"})

    def test_failed_dependency_does_not_unblock_downstream_step(self):
        plan = Plan("Inspect then summarize", (
            PlanStep("inspect", "Inspect public status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
            PlanStep("summarize", "Summarize inspected status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1, depends_on=("inspect",)),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R1, plan)
        self._grant(task, "researcher", "research", Risk.R1)
        self._start_low_risk(task, plan, "inspect")
        self.coordinator.execution.finish_step(
            task.task_id, "inspect", False, error="read failed"
        )
        self.assertEqual(self.coordinator.get_ready_steps(task.task_id, plan), ())

    def test_corrupt_event_chain_blocks_ready_step_scheduling(self):
        task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        with sqlite3.connect(self.task_db) as connection:
            connection.execute("DROP TRIGGER task_step_events_no_update")
            connection.execute(
                "UPDATE task_step_events SET reason = 'tampered' "
                "WHERE task_id = ? AND step_id = 'inspect'",
                (task.task_id,),
            )
        with self.assertRaisesRegex(ValueError, "hash-chain verification"):
            self.coordinator.get_ready_steps(task.task_id, self.plan)

    def test_needs_review_dependency_does_not_unblock_downstream_step(self):
        plan = Plan("Inspect device then summarize", (
            PlanStep("device-check", "Inspect device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
            PlanStep("summarize", "Summarize device state", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1, depends_on=("device-check",)),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R3, plan)
        approvals = ApprovalStore(self.coordinator)
        gate = ExecutionGate(self.coordinator)
        task_token = approvals.issue(task.task_id, plan, "owner", 300)
        gate.start_task_execution(task.task_id, plan, approval_token=task_token)
        step_token = approvals.issue_for_arguments(
            task.task_id, plan, "owner", 300,
            step_id="device-check", args_payload=ARGS_PAYLOAD,
        )
        gate.start_step(task.task_id, plan, "device-check", ARGS_PAYLOAD, approval_token=step_token)
        self.coordinator.execution.finish_step(
            task.task_id, "device-check", False, error="device operation outcome unknown"
        )
        self.assertEqual(self.coordinator.get_step_execution(
            task.task_id, "device-check"
        ).status, StepExecutionStatus.NEEDS_REVIEW)
        self.assertEqual(self.coordinator.get_ready_steps(task.task_id, plan), ())

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
        # Previously asserted that a caller-built Approval(approved=True) allowed
        # an R3 step. That is the forgery path closed by this change: plain
        # Approval objects and R3/R4 steps are refused here; approvals are
        # issued tokens consumed only by ExecutionGate (see test_execution_gate).
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
        forged = self.coordinator.authorize_step(
            task.task_id, plan, "inspect", approval=approval
        )
        self.assertFalse(forged.allowed)
        self.assertIn("not accepted", forged.reason)

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
