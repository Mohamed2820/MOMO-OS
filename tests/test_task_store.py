import tempfile
import unittest
from pathlib import Path

from intelligence.runtime.momo_runtime import Risk, TaskStatus
from intelligence.runtime.task_store import TaskNotFoundError, TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "momo" / "tasks.sqlite3"
        self.store = TaskStore(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_reopen_persists_task(self):
        created = self.store.create_task("Index local documents", Risk.R1)
        reopened = TaskStore(self.database).get_task(created.task_id)
        self.assertEqual(reopened.goal, "Index local documents")
        self.assertEqual(reopened.risk, Risk.R1)
        self.assertEqual(reopened.status, TaskStatus.RECEIVED)
        self.assertEqual(reopened.events, [])

    def test_transition_is_durable_and_journaled(self):
        task = self.store.create_task("Summarize a public page", Risk.R0)
        self.store.transition(task.task_id, TaskStatus.CLASSIFIED, "Intent classified")
        reopened = TaskStore(self.database).get_task(task.task_id)
        self.assertEqual(reopened.status, TaskStatus.CLASSIFIED)
        self.assertEqual(len(reopened.events), 1)
        self.assertEqual(reopened.events[0].reason, "Intent classified")

    def test_invalid_transition_does_not_change_database(self):
        task = self.store.create_task("Do not skip controls", Risk.R2)
        with self.assertRaises(ValueError):
            self.store.transition(task.task_id, TaskStatus.COMPLETED, "Invalid shortcut")
        unchanged = self.store.get_task(task.task_id)
        self.assertEqual(unchanged.status, TaskStatus.RECEIVED)
        self.assertEqual(unchanged.events, [])

    def test_high_risk_execution_still_requires_approval_state(self):
        task = self.store.create_task("Send a message", Risk.R3)
        self.store.transition(task.task_id, TaskStatus.CLASSIFIED, "Classified")
        self.store.transition(task.task_id, TaskStatus.PLANNED, "Draft prepared")
        with self.assertRaises(ValueError):
            self.store.transition(task.task_id, TaskStatus.EXECUTING, "Skip approval")
        waiting = self.store.transition(
            task.task_id, TaskStatus.AWAITING_APPROVAL, "Await user approval"
        )
        self.assertEqual(waiting.status, TaskStatus.AWAITING_APPROVAL)

    def test_missing_task_is_reported(self):
        with self.assertRaises(TaskNotFoundError):
            self.store.get_task("missing-task")

    def test_list_limit_is_validated(self):
        with self.assertRaises(ValueError):
            self.store.list_tasks(0)
        self.assertEqual(self.store.list_tasks(100), [])

    def test_task_list_returns_created_tasks(self):
        first = self.store.create_task("First", Risk.R0)
        second = self.store.create_task("Second", Risk.R1)
        ids = {task.task_id for task in self.store.list_tasks()}
        self.assertEqual(ids, {first.task_id, second.task_id})


if __name__ == "__main__":
    unittest.main()
