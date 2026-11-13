import unittest
from datetime import datetime, timedelta, timezone

from intelligence.runtime.momo_runtime import (
    Approval, CapabilityGrant, PermissionBroker, Risk, Task, TaskStatus, ToolRequest
)


class TaskStateTests(unittest.TestCase):
    def test_happy_path(self):
        task = Task(goal="Summarize a document", risk=Risk.R0)
        task.transition(TaskStatus.CLASSIFIED, "Intent understood")
        task.transition(TaskStatus.PLANNED, "Plan created")
        task.transition(TaskStatus.EXECUTING, "No privileged actions required")
        task.transition(TaskStatus.VERIFYING, "Checking output")
        task.transition(TaskStatus.COMPLETED, "Verification passed")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(len(task.events), 5)

    def test_invalid_transition_rejected(self):
        task = Task(goal="Do something", risk=Risk.R1)
        with self.assertRaises(ValueError):
            task.transition(TaskStatus.COMPLETED, "Skip all controls")

    def test_high_risk_task_cannot_skip_approval(self):
        task = Task(goal="Send a message", risk=Risk.R3)
        task.transition(TaskStatus.CLASSIFIED, "Classified as external side effect")
        task.transition(TaskStatus.PLANNED, "Prepared a message draft")
        with self.assertRaises(ValueError):
            task.transition(TaskStatus.EXECUTING, "Attempt without approval")
        task.transition(TaskStatus.AWAITING_APPROVAL, "Waiting for user confirmation")
        task.transition(TaskStatus.EXECUTING, "User approved the exact action")
        self.assertEqual(task.status, TaskStatus.EXECUTING)

    def test_terminal_task_cannot_resume(self):
        task = Task(goal="Read public data", risk=Risk.R0)
        task.transition(TaskStatus.CLASSIFIED, "Classified")
        task.transition(TaskStatus.PLANNED, "Planned")
        task.transition(TaskStatus.EXECUTING, "Started")
        task.transition(TaskStatus.VERIFYING, "Verified")
        task.transition(TaskStatus.COMPLETED, "Done")
        with self.assertRaises(ValueError):
            task.transition(TaskStatus.EXECUTING, "Try again")


class PermissionBrokerTests(unittest.TestCase):
    def setUp(self):
        self.broker = PermissionBroker()
        self.now = datetime.now(timezone.utc)
        self.request = ToolRequest("agent:secretary", "calendar.read", "calendar:primary", Risk.R1)
        self.grant = CapabilityGrant(
            subject="agent:secretary",
            action="calendar.read",
            resource="calendar:primary",
            risk=Risk.R1,
            expires_at=self.now + timedelta(minutes=5),
        )

    def test_matching_active_grant_allows(self):
        result = self.broker.authorize(self.request, [self.grant], now=self.now)
        self.assertTrue(result.allowed)
        self.assertEqual(result.grant_id, self.grant.grant_id)

    def test_expired_grant_denies(self):
        expired = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.now - timedelta(seconds=1)
        )
        result = self.broker.authorize(self.request, [expired], now=self.now)
        self.assertFalse(result.allowed)

    def test_scope_mismatch_denies(self):
        other = CapabilityGrant(
            self.grant.subject, self.grant.action, "calendar:other",
            self.grant.risk, self.grant.expires_at
        )
        result = self.broker.authorize(self.request, [other], now=self.now)
        self.assertFalse(result.allowed)

    def test_external_side_effect_needs_matching_approval(self):
        request = ToolRequest("agent:secretary", "message.send", "contact:42", Risk.R3)
        grant = CapabilityGrant(
            request.subject, request.action, request.resource, request.risk,
            self.now + timedelta(minutes=5)
        )
        denied = self.broker.authorize(request, [grant], now=self.now)
        self.assertFalse(denied.allowed)
        approval = Approval(request.subject, request.action, request.resource, True)
        allowed = self.broker.authorize(request, [grant], approval, now=self.now)
        self.assertTrue(allowed.allowed)

    def test_wrong_approval_denies(self):
        request = ToolRequest("agent:secretary", "message.send", "contact:42", Risk.R3)
        approval = Approval("agent:secretary", "message.send", "contact:99", True)
        result = self.broker.authorize(request, [self.grant], approval, now=self.now)
        self.assertFalse(result.allowed)

    def test_single_use_grant_cannot_be_replayed(self):
        self.assertTrue(self.broker.authorize(self.request, [self.grant], now=self.now).allowed)
        replay = self.broker.authorize(self.request, [self.grant], now=self.now)
        self.assertFalse(replay.allowed)
        self.assertIn("No active", replay.reason)

    def test_multi_use_grant_stops_at_limit(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.grant.expires_at, max_uses=2
        )
        self.assertTrue(self.broker.authorize(self.request, [grant], now=self.now).allowed)
        self.assertTrue(self.broker.authorize(self.request, [grant], now=self.now).allowed)
        self.assertFalse(self.broker.authorize(self.request, [grant], now=self.now).allowed)

    def test_revoked_grant_is_denied(self):
        self.broker.revoke(self.grant.grant_id)
        result = self.broker.authorize(self.request, [self.grant], now=self.now)
        self.assertFalse(result.allowed)

    def test_never_allowed_grant_is_denied(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.grant.expires_at, approval_mode="never_allowed"
        )
        result = self.broker.authorize(self.request, [grant], now=self.now)
        self.assertFalse(result.allowed)

    def test_naive_expiry_is_denied(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, datetime.now()
        )
        result = self.broker.authorize(self.request, [grant], now=self.now)
        self.assertFalse(result.allowed)


if __name__ == "__main__":
    unittest.main()
