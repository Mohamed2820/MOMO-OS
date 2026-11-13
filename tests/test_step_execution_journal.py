import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from intelligence.execution.step_journal import (
    StepExecutionJournal,
    StepExecutionNotFoundError,
    StepExecutionStatus,
)
from intelligence.runtime.momo_runtime import Risk
from intelligence.runtime.task_store import TaskStore


class StepExecutionJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "tasks.sqlite3"
        self.tasks = TaskStore(self.database)
        self.task = self.tasks.create_task("Run bounded execution tests", Risk.R1)
        self.journal = StepExecutionJournal(self.database)

    def tearDown(self):
        self.temp.cleanup()

    def register(self, step_id="read-status", risk=Risk.R1, retry_limit=0):
        return self.journal.register_step(
            self.task.task_id, step_id, risk,
            f"{self.task.task_id}:{step_id}:v1", retry_limit,
        )

    def test_register_persists_ready_record_and_event(self):
        record = self.register()
        self.assertEqual(record.status, StepExecutionStatus.READY)
        self.assertEqual(record.attempt, 0)
        events = self.journal.list_events(self.task.task_id, "read-status")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].current, "ready")

    def test_successful_attempt_persists_result_digest(self):
        digest = hashlib.sha256(b"verified result").hexdigest()
        self.register()
        running = self.journal.start_step(self.task.task_id, "read-status")
        self.assertEqual(running.status, StepExecutionStatus.RUNNING)
        self.assertEqual(running.attempt, 1)
        done = self.journal.finish_step(
            self.task.task_id, "read-status", True, result_sha256=digest
        )
        self.assertEqual(done.status, StepExecutionStatus.SUCCEEDED)
        self.assertEqual(done.result_sha256, digest)

    def test_read_only_retry_is_explicit_and_bounded(self):
        self.register(retry_limit=1)
        self.journal.start_step(self.task.task_id, "read-status")
        failed = self.journal.finish_step(
            self.task.task_id, "read-status", False, error="temporary read failure"
        )
        self.assertEqual(failed.status, StepExecutionStatus.FAILED)
        with self.assertRaisesRegex(ValueError, "explicitly requested"):
            self.journal.start_step(self.task.task_id, "read-status")
        retried = self.journal.start_step(self.task.task_id, "read-status", retry=True)
        self.assertEqual(retried.attempt, 2)
        self.journal.finish_step(
            self.task.task_id, "read-status", False, error="second read failure"
        )
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.journal.start_step(self.task.task_id, "read-status", retry=True)

    def test_side_effecting_step_cannot_receive_automatic_retry_budget(self):
        with self.assertRaisesRegex(ValueError, "restricted to R0/R1"):
            self.register(risk=Risk.R2, retry_limit=1)

    def test_side_effecting_failure_requires_reconciliation(self):
        self.register(risk=Risk.R3)
        self.journal.start_step(self.task.task_id, "read-status")
        failed = self.journal.finish_step(
            self.task.task_id, "read-status", False, error="transport disconnected"
        )
        self.assertEqual(failed.status, StepExecutionStatus.NEEDS_REVIEW)
        with self.assertRaisesRegex(ValueError, "state"):
            self.journal.start_step(self.task.task_id, "read-status", retry=True)

    def test_restart_quarantines_running_step_without_replay(self):
        self.register()
        self.journal.start_step(self.task.task_id, "read-status")
        restarted = StepExecutionJournal(self.database)
        recovered = restarted.recover_interrupted()
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].status, StepExecutionStatus.NEEDS_REVIEW)
        with self.assertRaisesRegex(ValueError, "state"):
            restarted.start_step(self.task.task_id, "read-status", retry=True)

    def test_restart_recovery_is_idempotent(self):
        self.register()
        self.journal.start_step(self.task.task_id, "read-status")
        self.assertEqual(len(self.journal.recover_interrupted()), 1)
        self.assertEqual(self.journal.recover_interrupted(), ())

    def test_ready_step_can_be_cancelled_without_execution(self):
        self.register()
        cancelled = self.journal.request_cancel(self.task.task_id, "read-status")
        self.assertEqual(cancelled.status, StepExecutionStatus.CANCELLED)
        self.assertEqual(cancelled.attempt, 0)

    def test_running_cancel_requires_executor_confirmation(self):
        self.register()
        self.journal.start_step(self.task.task_id, "read-status")
        requested = self.journal.request_cancel(self.task.task_id, "read-status")
        self.assertTrue(requested.cancel_requested)
        with self.assertRaisesRegex(ValueError, "no side effect"):
            self.journal.acknowledge_cancel(
                self.task.task_id, "read-status", confirmed_no_side_effect=False
            )
        cancelled = self.journal.acknowledge_cancel(
            self.task.task_id, "read-status", confirmed_no_side_effect=True
        )
        self.assertEqual(cancelled.status, StepExecutionStatus.CANCELLED)

    def test_invalid_result_digest_is_rejected(self):
        self.register()
        self.journal.start_step(self.task.task_id, "read-status")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.journal.finish_step(
                self.task.task_id, "read-status", True, result_sha256="not-a-digest"
            )

    def test_duplicate_step_and_idempotency_key_are_rejected(self):
        self.register()
        with self.assertRaises(sqlite3.IntegrityError):
            self.register()
        self.journal.register_step(
            self.task.task_id, "another-step", Risk.R1,
            f"{self.task.task_id}:read-status:v1",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.journal.register_step(
                self.task.task_id, "third-step", Risk.R1,
                f"{self.task.task_id}:read-status:v1",
            )

    def test_unknown_step_is_reported(self):
        with self.assertRaises(StepExecutionNotFoundError):
            self.journal.get_step(self.task.task_id, "missing")


if __name__ == "__main__":
    unittest.main()
