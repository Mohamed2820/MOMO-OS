"""Integration tests for the first narrow read-only typed executor."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence.runtime.execution_gate import ExecutionGate
from intelligence.runtime.momo_runtime import CapabilityGrant, Risk
from intelligence.runtime.orchestrator import AgentRegistry, AgentSpec, Plan, PlanStep
from intelligence.runtime.task_coordinator import TaskCoordinator
from intelligence.runtime.typed_executor import (
    OperationDenied, OperationRegistry, OperationSpec, TypedExecutor,
    default_read_only_registry,
)


class TypedExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        registry = AgentRegistry()
        registry.register(AgentSpec(
            role="system-reader",
            domains=frozenset({"system"}),
            capabilities=frozenset({"system.status.read"}),
            max_risk=Risk.R1,
        ))
        self.plan = Plan("Read system status", (
            PlanStep(
                "read-status", "Read minimal system status", "system-reader",
                "system", frozenset({"system.status.read"}), Risk.R1,
            ),
        ))
        self.coordinator = TaskCoordinator(
            registry, root / "tasks.sqlite3", root / "permissions.sqlite3",
        )
        self.task = self.coordinator.create_task(self.plan.goal, Risk.R1, self.plan)
        self.coordinator.permissions.add_grant(CapabilityGrant(
            subject="system-reader",
            action="system",
            resource=self.task.task_id,
            risk=Risk.R1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            max_uses=1,
        ))
        self.gate = ExecutionGate(self.coordinator)
        self.gate.start_task_execution(self.task.task_id, self.plan)
        self.registry = default_read_only_registry()
        self.executor = TypedExecutor(self.coordinator, self.gate, self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def test_registered_status_operation_executes_and_records_digest(self):
        result = self.executor.execute(
            self.task.task_id, self.plan, "read-status",
            "system.status.read", b"{}",
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.result["state"], "ready")
        self.assertEqual(len(result.result_sha256), 64)
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "read-status"
            ).status.value,
            "succeeded",
        )

    def test_unknown_operation_is_denied_before_step_start(self):
        with self.assertRaises(OperationDenied):
            self.executor.execute(
                self.task.task_id, self.plan, "read-status",
                "system.shell.execute", b"{}",
            )
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "read-status"
            ).status.value,
            "ready",
        )

    def test_operation_schema_rejects_unexpected_arguments(self):
        with self.assertRaises(OperationDenied):
            self.executor.execute(
                self.task.task_id, self.plan, "read-status",
                "system.status.read", b'{"include_secrets":true}',
            )
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "read-status"
            ).status.value,
            "ready",
        )

    def test_operation_must_match_planned_domain_and_capability(self):
        wrong = OperationRegistry()
        wrong.register(OperationSpec(
            operation_id="network.status.read",
            domain="network",
            required_capability="network.status.read",
            risk=Risk.R1,
            argument_types={},
            handler=lambda _args: {"state": "ready"},
        ))
        executor = TypedExecutor(self.coordinator, self.gate, wrong)
        with self.assertRaises(OperationDenied):
            executor.execute(
                self.task.task_id, self.plan, "read-status",
                "network.status.read", b"{}",
            )

    def test_handler_failure_is_recorded_as_failed_read_only_step(self):
        failing = OperationRegistry()
        def fail(_arguments):
            raise OSError("status provider unavailable")
        failing.register(OperationSpec(
            operation_id="system.status.fail",
            domain="system",
            required_capability="system.status.read",
            risk=Risk.R1,
            argument_types={},
            handler=fail,
        ))
        executor = TypedExecutor(self.coordinator, self.gate, failing)
        from intelligence.runtime.typed_executor import OperationExecutionError
        with self.assertRaises(OperationExecutionError):
            executor.execute(
                self.task.task_id, self.plan, "read-status",
                "system.status.fail", b"{}",
            )
        self.assertEqual(
            self.coordinator.get_step_execution(
                self.task.task_id, "read-status"
            ).status.value,
            "failed",
        )

    def test_registry_refuses_explicit_side_effecting_operation(self):
        with self.assertRaises(ValueError):
            self.registry.register(OperationSpec(
                operation_id="system.settings.write",
                domain="system",
                required_capability="system.settings.write",
                risk=Risk.R1,
                argument_types={},
                handler=lambda _args: {},
                side_effects=True,
            ))

    def test_registry_refuses_side_effecting_risk_levels(self):
        with self.assertRaises(ValueError):
            self.registry.register(OperationSpec(
                operation_id="system.settings.write",
                domain="system",
                required_capability="system.settings.write",
                risk=Risk.R3,
                argument_types={},
                handler=lambda _args: {},
            ))

    def test_result_is_immutable(self):
        result = self.executor.execute(
            self.task.task_id, self.plan, "read-status",
            "system.status.read", b"{}",
        )
        with self.assertRaises(TypeError):
            result.result["state"] = "spoofed"


if __name__ == "__main__":
    unittest.main()
