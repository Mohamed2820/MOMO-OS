import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
