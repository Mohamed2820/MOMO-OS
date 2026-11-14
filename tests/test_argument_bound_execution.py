"""End-to-end tests for deriving approval bindings from exact JSON arguments."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from intelligence.runtime.approval_store import ApprovalStore
from intelligence.runtime.execution_gate import AuthorizationDenied, ExecutionGate
from intelligence.runtime.momo_runtime import Risk, TaskStatus
from intelligence.runtime.orchestrator import AgentRegistry, AgentSpec, Plan, PlanStep
from intelligence.runtime.task_coordinator import TaskCoordinator
from intelligence.runtime.argument_binding import canonical_arguments


class ArgumentBoundExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        registry = AgentRegistry()
        registry.register(AgentSpec(
            role="operator",
            domains=frozenset({"device"}),
            capabilities=frozenset({"device.inspect"}),
            max_risk=Risk.R4,
        ))
        self.plan = Plan("Inspect device", (
            PlanStep(
                "device-check", "Check device", "operator", "device",
                frozenset({"device.inspect"}), Risk.R3,
            ),
        ))
        self.coordinator = TaskCoordinator(
            registry, root / "tasks.sqlite3", root / "permissions.sqlite3",
        )
        self.approvals = ApprovalStore(self.coordinator)
        self.gate = ExecutionGate(self.coordinator)
        self.task = self.coordinator.create_task(self.plan.goal, Risk.R3, self.plan)
        task_token = self.approvals.issue(
            self.task.task_id, self.plan, "local-owner", 300,
        )
        self.gate.start_task_execution(
            self.task.task_id, self.plan, approval_token=task_token,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_approval_and_start_derive_same_digest_from_payload(self):
        payload = b'{"mode":"inspect","device":"local"}'
        token = self.approvals.issue_for_arguments(
            self.task.task_id, self.plan, "local-owner", 300,
            "device-check", payload,
        )
        started = self.gate.start_step_with_arguments(
            self.task.task_id, self.plan, "device-check", payload,
            approval_token=token,
        )
        _encoded, expected_digest = canonical_arguments({
            "mode": "inspect", "device": "local",
        })
        self.assertEqual(started.args_sha256, expected_digest)
        self.assertEqual(started.arguments, {
            "mode": "inspect", "device": "local",
        })
        self.assertEqual(started.execution.status.value, "running")

    def test_changed_payload_cannot_reuse_approval(self):
        approved = b'{"device":"local","mode":"inspect"}'
        changed = b'{"device":"remote","mode":"inspect"}'
        token = self.approvals.issue_for_arguments(
            self.task.task_id, self.plan, "local-owner", 300,
            "device-check", approved,
        )
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step_with_arguments(
                self.task.task_id, self.plan, "device-check", changed,
                approval_token=token,
            )
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "device-check"
            ).status.value,
            "ready",
        )

    def test_duplicate_keys_are_rejected_before_approval_is_issued(self):
        with self.assertRaises(ValueError):
            self.approvals.issue_for_arguments(
                self.task.task_id, self.plan, "local-owner", 300,
                "device-check", b'{"device":"local","device":"remote"}',
            )

    def test_malformed_arguments_are_rejected_before_step_start(self):
        with self.assertRaises(AuthorizationDenied):
            self.gate.start_step_with_arguments(
                self.task.task_id, self.plan, "device-check",
                b'{"mode":NaN}',
            )
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "device-check"
            ).status.value,
            "ready",
        )

    def test_returned_arguments_are_deeply_immutable(self):
        payload = b'{"nested":{"items":[1,2]}}'
        token = self.approvals.issue_for_arguments(
            self.task.task_id, self.plan, "local-owner", 300,
            "device-check", payload,
        )
        started = self.gate.start_step_with_arguments(
            self.task.task_id, self.plan, "device-check", payload,
            approval_token=token,
        )
        with self.assertRaises(TypeError):
            started.arguments["nested"] = {}
        with self.assertRaises(TypeError):
            started.arguments["nested"]["items"] = ()
        self.assertEqual(started.arguments["nested"]["items"], (1, 2))

    def test_key_order_does_not_change_approval_binding(self):
        first = b'{"a":1,"b":2}'
        second = b'{"b":2,"a":1}'
        token = self.approvals.issue_for_arguments(
            self.task.task_id, self.plan, "local-owner", 300,
            "device-check", first,
        )
        started = self.gate.start_step_with_arguments(
            self.task.task_id, self.plan, "device-check", second,
            approval_token=token,
        )
        self.assertEqual(
            started.args_sha256,
            hashlib.sha256(b'{"a":1,"b":2}').hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
