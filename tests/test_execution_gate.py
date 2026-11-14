"""Negative and positive tests for the execution gate and approval tokens.

These tests exercise the real SQLite state, the real CLI and the real module
boundaries. A green run here is evidence only for the in-process guard described
in the report; it is not an OS-level isolation proof.
"""
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from intelligence.execution.step_journal import StepExecutionStatus
from intelligence.runtime.approval_store import ApprovalDenied, ApprovalStore
from intelligence.runtime.execution_gate import AuthorizationDenied, ExecutionGate
from intelligence.runtime.momo_runtime import (
    Approval, CapabilityGrant, Risk, TaskStatus,
)
from intelligence.runtime.orchestrator import AgentRegistry, AgentSpec, Plan, PlanStep
from intelligence.runtime.task_coordinator import TaskCoordinator
from intelligence.runtime.task_store import TaskStore

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "board/momo/rootfs-overlay/usr/bin/momo-task"

ARGS_1 = hashlib.sha256(b"arguments v1").hexdigest()
ARGS_2 = hashlib.sha256(b"arguments v2 (changed)").hexdigest()


def _binding_for(task, plan, args):
    from intelligence.runtime.approval_store import binding_digest
    from intelligence.runtime.task_coordinator import _plan_digest
    return binding_digest(task.task_id, "device-check", "device", task.task_id,
                          "R3", _plan_digest(plan)[0], args)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ExecutionGateTests(unittest.TestCase):
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
        self.coordinator = TaskCoordinator(registry, self.task_db, root / "permissions.sqlite3")
        self.approvals = ApprovalStore(self.coordinator)
        self.gate = ExecutionGate(self.coordinator)
        self.low = Plan("Inspect public status", (
            PlanStep("inspect", "Inspect status", "researcher", "research",
                     frozenset({"web.read"}), Risk.R1),
        ))
        self.high = Plan("Inspect device", (
            PlanStep("device-check", "Check device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
        ))

    def tearDown(self):
        self.temp.cleanup()

    # helpers -------------------------------------------------------------
    def _grant_low(self, task):
        self.coordinator.permissions.add_grant(CapabilityGrant(
            subject="researcher", action="research", resource=task.task_id,
            risk=Risk.R1, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            max_uses=1,
        ))

    def _high_task(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        token = self.approvals.issue(task.task_id, self.high, "owner", 300)
        self.gate.start_task_execution(task.task_id, self.high, approval_token=token)
        return task

    def _step_token(self, task, args=ARGS_1, ttl=300):
        return self.approvals.issue(
            task.task_id, self.high, "owner", ttl,
            step_id="device-check", args_sha256=args,
        )

    def _row_count(self, table):
        with sqlite3.connect(self.task_db) as connection:
            return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    # 1. transition to executing without approval --------------------------
    def test_r3_task_cannot_enter_executing_without_approval(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_task_execution(task.task_id, self.high)
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.AWAITING_APPROVAL)

    def test_store_refuses_executing_for_plan_bound_task(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        with self.assertRaises(ValueError):
            self.coordinator.tasks.transition(task.task_id, TaskStatus.EXECUTING, "bypass")
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.PLANNED)

    def test_store_refuses_awaiting_to_executing_for_r3(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        with self.assertRaises(ValueError):
            self.coordinator.tasks.transition(task.task_id, TaskStatus.EXECUTING, "skip")

    def test_cli_cannot_transition_to_executing(self):
        store = TaskStore(self.task_db)
        task = store.create_task("cli bypass attempt", Risk.R3)
        store.transition(task.task_id, TaskStatus.CLASSIFIED, "c")
        store.transition(task.task_id, TaskStatus.PLANNED, "p")
        store.transition(task.task_id, TaskStatus.AWAITING_APPROVAL, "a")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["MOMO_TASK_DB"] = str(self.task_db)
        result = subprocess.run(
            [sys.executable, str(CLI), "transition", task.task_id, "executing", "--reason", "x"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("execution gate", result.stderr)
        self.assertEqual(store.get_task(task.task_id).status, TaskStatus.AWAITING_APPROVAL)

    # 2. start step without authorization ----------------------------------
    def test_step_cannot_start_without_grant(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        self.gate.start_task_execution(task.task_id, self.low)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.low, "inspect", ARGS_1)
        self.assertEqual(self.coordinator.get_step_execution(task.task_id, "inspect").status,
                         StepExecutionStatus.READY)

    def test_step_cannot_start_before_task_executes(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        self._grant_low(task)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.low, "inspect", ARGS_1)

    def test_journal_refuses_direct_start_for_plan_bound_task(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        with self.assertRaises(ValueError):
            self.coordinator.execution.start_step(task.task_id, "inspect")
        self.assertEqual(self.coordinator.get_step_execution(task.task_id, "inspect").status,
                         StepExecutionStatus.READY)

    def test_journal_refuses_registering_steps_outside_plan(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        with self.assertRaises(ValueError):
            self.coordinator.execution.register_step(
                task.task_id, "extra", Risk.R0, _digest("extra-step"),
            )

    def test_r3_step_cannot_start_while_task_awaits_approval(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        token = self._step_token(task)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                 approval_token=token)
        self.assertEqual(self._row_count("approval_tokens"), 1)  # issued, not consumed
        self.assertEqual(self.coordinator.get_step_execution(
            task.task_id, "device-check").status, StepExecutionStatus.READY)

    def test_r3_step_without_token_is_refused(self):
        task = self._high_task()
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1)

    # 3. arguments changed after approval ----------------------------------
    def test_changed_arguments_are_refused_and_token_is_not_burned(self):
        task = self._high_task()
        token = self._step_token(task, args=ARGS_1)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_2,
                                 approval_token=token)
        started = self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                       approval_token=token)
        self.assertEqual(started.status, StepExecutionStatus.RUNNING)

    # 4. reuse ---------------------------------------------------------------
    def test_approval_cannot_be_reused(self):
        task = self._high_task()
        token = self._step_token(task)
        self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                             approval_token=token)
        self.coordinator.execution.finish_step(
            task.task_id, "device-check", False, error="unknown outcome",
        )
        # The gate refuses on readiness before it touches the token (a finished
        # R3 step is never ready again), so the token is not even presented to
        # the consumption check here. Prove the token itself is spent:
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                 approval_token=token)
        with sqlite3.connect(self.task_db) as connection:
            with self.assertRaises(ApprovalDenied) as caught:
                ApprovalStore.consume(connection, token, _binding_for(task, self.high, ARGS_1),
                                      datetime.now(timezone.utc))
        self.assertIn("already consumed", str(caught.exception))

    # 5. expiry ---------------------------------------------------------------
    def test_expired_approval_is_refused(self):
        clock = {"now": datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)}
        approvals = ApprovalStore(self.coordinator, clock=lambda: clock["now"])
        gate = ExecutionGate(self.coordinator, clock=lambda: clock["now"])
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        task_token = approvals.issue(task.task_id, self.high, "owner", 300)
        gate.start_task_execution(task.task_id, self.high, approval_token=task_token)
        token = approvals.issue(task.task_id, self.high, "owner", 1,
                                step_id="device-check", args_sha256=ARGS_1)
        clock["now"] = clock["now"] + timedelta(seconds=2)
        with self.assertRaises(AuthorizationDenied) as caught:
            gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                            approval_token=token)
        self.assertIn("expired", str(caught.exception))
        self.assertEqual(self.coordinator.get_step_execution(
            task.task_id, "device-check").status, StepExecutionStatus.READY)

    def test_callers_cannot_supply_time_to_extend_or_replay_an_approval(self):
        # The public entry points take no per-call time: a caller cannot backdate
        # an approval or present a past time to revive an expired one.
        with self.assertRaises(TypeError):
            self.gate.start_step(
                "x", self.high, "device-check", ARGS_1, now=datetime.now(timezone.utc),
            )
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        with self.assertRaises(TypeError):
            self.approvals.issue(task.task_id, self.high, "owner", 300,
                                 now=datetime.now(timezone.utc))

    # 6. wrong task / wrong step ---------------------------------------------
    def test_approval_for_another_task_is_refused(self):
        task_a = self._high_task()
        task_b = self._high_task()
        token_for_a = self._step_token(task_a)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task_b.task_id, self.high, "device-check", ARGS_1,
                                 approval_token=token_for_a)

    def test_approval_for_another_step_is_refused(self):
        plan = Plan("Two device checks", (
            PlanStep("device-check", "Check device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
            PlanStep("device-audit", "Audit device", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
        ))
        task = self.coordinator.create_task(plan.goal, Risk.R3, plan)
        task_token = self.approvals.issue(task.task_id, plan, "owner", 300)
        self.gate.start_task_execution(task.task_id, plan, approval_token=task_token)
        token = self.approvals.issue(task.task_id, plan, "owner", 300,
                                     step_id="device-check", args_sha256=ARGS_1)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, plan, "device-audit", ARGS_1,
                                 approval_token=token)

    def test_task_approval_cannot_start_a_step(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        task_token = self.approvals.issue(task.task_id, self.high, "owner", 300)
        self.gate.start_task_execution(task.task_id, self.high, approval_token=task_token)
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                 approval_token=task_token)

    def test_plan_modified_after_approval_is_refused(self):
        task = self._high_task()
        token = self._step_token(task)
        altered = Plan(self.high.goal, (
            PlanStep("device-check", "Different operation", "operator", "device",
                     frozenset({"device.inspect"}), Risk.R3),
        ))
        with self.assertRaises(ValueError):
            self.gate.start_step(task.task_id, altered, "device-check", ARGS_1,
                                 approval_token=token)

    # 7. concurrency ----------------------------------------------------------
    def test_concurrent_consumers_of_one_approval_yield_exactly_one_winner(self):
        task = self._high_task()
        token = self._step_token(task)
        results, barrier = [], threading.Barrier(8)

        def attempt():
            gate = ExecutionGate(self.coordinator)
            barrier.wait()
            try:
                gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                approval_token=token)
                results.append("ok")
            except (AuthorizationDenied, ValueError) as error:
                results.append(type(error).__name__)

        threads = [threading.Thread(target=attempt) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(len(results), 8)
        self.assertEqual(self.coordinator.get_step_execution(
            task.task_id, "device-check").attempt, 1)

    def test_consumption_primitive_alone_admits_exactly_one_consumer(self):
        # Independent of step readiness: N connections race ApprovalStore.consume
        # on the same token and binding; only one may succeed.
        task = self._high_task()
        token = self._step_token(task)
        binding = _binding_for(task, self.high, ARGS_1)
        results, barrier = [], threading.Barrier(8)

        def consume_once():
            connection = sqlite3.connect(str(self.task_db), timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 10000")
            barrier.wait()
            try:
                connection.execute("BEGIN IMMEDIATE")
                ApprovalStore.consume(connection, token, binding, datetime.now(timezone.utc))
                connection.commit()
                results.append("ok")
            except ApprovalDenied:
                connection.rollback()
                results.append("denied")
            finally:
                connection.close()

        threads = [threading.Thread(target=consume_once) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(results.count("denied"), 7, results)

    # 8. direct module use and forged objects --------------------------------
    def test_plain_approval_object_is_not_a_token(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        with self.assertRaises(ValueError):
            self.gate.start_task_execution(
                task.task_id, self.high,
                approval_token=Approval("owner", "task.execute", task.task_id, True),
            )

    def test_forged_token_string_is_refused(self):
        task = self._high_task()
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                 approval_token="made-up-token")

    def test_token_is_not_stored_in_plaintext(self):
        task = self._high_task()
        token = self._step_token(task)
        with sqlite3.connect(self.task_db) as connection:
            stored = connection.execute("SELECT token_hash FROM approval_tokens").fetchall()
        self.assertNotIn(token, [row[0] for row in stored])

    def test_approval_cannot_be_issued_without_identity_or_bad_ttl(self):
        task = self.coordinator.create_task(self.high.goal, Risk.R3, self.high)
        with self.assertRaises(ValueError):
            self.approvals.issue(task.task_id, self.high, "  ", 300)
        with self.assertRaises(ValueError):
            self.approvals.issue(task.task_id, self.high, "owner", 0)
        with self.assertRaises(ValueError):
            self.approvals.issue(task.task_id, self.high, "owner", 3600)

    def test_failed_start_rolls_back_approval_consumption(self):
        task = self._high_task()
        token = self._step_token(task)
        with mock.patch.object(self.coordinator.execution, "_start_locked",
                               side_effect=RuntimeError("injected fault")):
            with self.assertRaises(RuntimeError):
                self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                     approval_token=token)
        started = self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                       approval_token=token)
        self.assertEqual(started.status, StepExecutionStatus.RUNNING)

    def test_approval_store_consume_rejects_mismatch_directly(self):
        task = self._high_task()
        token = self._step_token(task)
        with sqlite3.connect(self.task_db) as connection:
            with self.assertRaises(ApprovalDenied):
                ApprovalStore.consume(connection, token, _digest("wrong binding"),
                                      datetime.now(timezone.utc))

    # 9. positive paths -------------------------------------------------------
    def test_low_risk_path_runs_end_to_end_through_gate(self):
        task = self.coordinator.create_task(self.low.goal, Risk.R1, self.low)
        self._grant_low(task)
        self.gate.start_task_execution(task.task_id, self.low)
        running = self.gate.start_step(task.task_id, self.low, "inspect", ARGS_1)
        self.assertEqual(running.status, StepExecutionStatus.RUNNING)
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.EXECUTING)

    def test_high_risk_path_runs_end_to_end_with_issued_tokens(self):
        task = self._high_task()
        token = self._step_token(task)
        running = self.gate.start_step(task.task_id, self.high, "device-check", ARGS_1,
                                       approval_token=token)
        self.assertEqual(running.status, StepExecutionStatus.RUNNING)
        self.assertEqual(self.coordinator.tasks.get_task(task.task_id).status,
                         TaskStatus.EXECUTING)


if __name__ == "__main__":
    unittest.main()
