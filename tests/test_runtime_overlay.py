import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from intelligence.execution.step_journal import StepExecutionJournal, StepExecutionStatus
from intelligence.runtime.momo_runtime import Risk
from intelligence.runtime.task_store import TaskStore


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "board/momo/rootfs-overlay"
RUNTIME_SOURCE = ROOT / "intelligence/runtime"
RUNTIME_TARGET = OVERLAY / "usr/lib/momo/intelligence/runtime"
BIN = OVERLAY / "usr/bin"


class RuntimeOverlayIntegrationTests(unittest.TestCase):
    def test_runtime_modules_match_the_source_of_truth(self):
        for name in (
            "momo_runtime.py",
            "task_store.py",
            "device_inventory.py",
            "persistent_permission_broker.py",
            "task_coordinator.py",
            "orchestrator.py",
            "approval_store.py",
            "execution_gate.py",
            "argument_binding.py",
            "typed_executor.py",
        ):
            with self.subTest(module=name):
                self.assertEqual(
                    (RUNTIME_SOURCE / name).read_text(encoding="utf-8"),
                    (RUNTIME_TARGET / name).read_text(encoding="utf-8"),
                )

    def test_execution_modules_match_the_source_of_truth(self):
        source = ROOT / "intelligence/execution"
        target = OVERLAY / "usr/lib/momo/intelligence/execution"
        for name in ("__init__.py", "step_journal.py"):
            with self.subTest(module=name):
                self.assertEqual(
                    (source / name).read_text(encoding="utf-8"),
                    (target / name).read_text(encoding="utf-8"),
                )

    def test_python_overlay_commands_compile(self):
        for name in ("momo-task", "momo-device", "momo-permissions"):
            with self.subTest(command=name):
                source = (BIN / name).read_text(encoding="utf-8")
                compile(source, str(BIN / name), "exec")

    def test_momoctl_shell_syntax_is_valid(self):
        result = subprocess.run(
            ["sh", "-n", str(BIN / "momoctl")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_device_command_emits_conservative_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(BIN / "momo-device")],
            env=env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("architecture", payload["identity"])
        self.assertEqual(payload["profile_status"], "not_found")
        self.assertTrue(all(
            capability["status"] == "unknown"
            for capability in payload["capabilities"].values()
        ))

    def test_task_recovery_command_quarantines_interrupted_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.sqlite3"
            store = TaskStore(database)
            task = store.create_task("Recover interrupted step", Risk.R1)
            journal = StepExecutionJournal(database)
            journal.register_step(
                task.task_id, "inspect", Risk.R1, "test:recover:inspect"
            )
            journal.start_step(task.task_id, "inspect")

            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            env["MOMO_TASK_DB"] = str(database)
            recovered = subprocess.run(
                [sys.executable, str(BIN / "momo-task"), "recover"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            payload = json.loads(recovered.stdout)
            self.assertEqual(payload["recovered_count"], 1)
            self.assertEqual(payload["steps"][0]["status"], "needs_review")
            self.assertEqual(
                journal.get_step(task.task_id, "inspect").status,
                StepExecutionStatus.NEEDS_REVIEW,
            )

            repeated = subprocess.run(
                [sys.executable, str(BIN / "momo-task"), "recover"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["recovered_count"], 0)

    def test_boot_check_invokes_recovery_before_readiness(self):
        source = (BIN / "momoctl").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/momo-task recover", source)

    def test_permission_cli_initializes_and_reads_isolated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "permissions.sqlite3"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            env["MOMO_PERMISSION_DB"] = str(database)
            doctor = subprocess.run(
                [sys.executable, str(BIN / "momo-permissions"), "doctor"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertTrue(database.is_file())

            audit = subprocess.run(
                [sys.executable, str(BIN / "momo-permissions"), "audit"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertEqual(json.loads(audit.stdout), [])

    def test_momo_cell_overlay_matches_source(self):
        source = ROOT / "intelligence/cell"
        target = OVERLAY / "usr/lib/momo/intelligence/cell"
        for name in ("__init__.py", "cli.py"):
            with self.subTest(module=name):
                self.assertEqual(
                    (source / name).read_text(encoding="utf-8"),
                    (target / name).read_text(encoding="utf-8"),
                )

    def test_momo_cell_boot_service_and_command_have_valid_shell_syntax(self):
        for path in (
            OVERLAY / "etc/init.d/S97momo-cell",
            BIN / "momo-cell",
        ):
            with self.subTest(path=path.name):
                result = subprocess.run(
                    ["sh", "-n", str(path)], capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_system_scan_does_not_require_repository_documents(self):
        from intelligence.cell import MomoCell
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "service.py").write_text("value = 1\\n", encoding="utf-8")
            report = MomoCell(include_repository_contracts=False).scan(root)
            self.assertEqual(report.findings, ())
            self.assertEqual(report.proposals, ())


if __name__ == "__main__":
    unittest.main()
