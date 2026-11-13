import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence.runtime.momo_runtime import Approval, CapabilityGrant, Risk, ToolRequest
from intelligence.runtime.persistent_permission_broker import PersistentPermissionBroker


class PersistentPermissionBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "permissions.sqlite3"
        self.broker = PersistentPermissionBroker(self.database)
        self.now = datetime.now(timezone.utc)
        self.request = ToolRequest("agent:secretary", "calendar.read", "calendar:primary", Risk.R1)
        self.grant = CapabilityGrant(
            subject=self.request.subject,
            action=self.request.action,
            resource=self.request.resource,
            risk=self.request.risk,
            expires_at=self.now + timedelta(minutes=5),
            max_uses=1,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_grant_use_limit_survives_broker_restart(self):
        self.broker.add_grant(self.grant)
        self.assertTrue(self.broker.authorize(self.request, now=self.now).allowed)
        restarted = PersistentPermissionBroker(self.database)
        replay = restarted.authorize(self.request, now=self.now)
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.reason, "No active matching capability grant")

    def test_revocation_survives_restart(self):
        self.broker.add_grant(self.grant)
        self.assertTrue(self.broker.revoke(self.grant.grant_id))
        restarted = PersistentPermissionBroker(self.database)
        self.assertFalse(restarted.authorize(self.request, now=self.now).allowed)

    def test_expired_grant_is_denied_and_audited(self):
        expired = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.now - timedelta(seconds=1)
        )
        self.broker.add_grant(expired)
        result = self.broker.authorize(self.request, now=self.now)
        self.assertFalse(result.allowed)
        self.assertEqual(self.broker.list_events()[0]["allowed"], 0)

    def test_high_risk_requires_exact_approval_and_matching_grant(self):
        request = ToolRequest("agent:secretary", "message.send", "contact:42", Risk.R3)
        grant = CapabilityGrant(
            request.subject, request.action, request.resource, request.risk,
            self.now + timedelta(minutes=5)
        )
        self.broker.add_grant(grant)
        self.assertFalse(self.broker.authorize(request, now=self.now).allowed)
        wrong = Approval(request.subject, request.action, "contact:99", True)
        self.assertFalse(self.broker.authorize(request, wrong, now=self.now).allowed)
        exact = Approval(request.subject, request.action, request.resource, True)
        self.assertTrue(self.broker.authorize(request, exact, now=self.now).allowed)

    def test_never_allowed_grant_cannot_be_used(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.grant.expires_at, approval_mode="never_allowed"
        )
        self.broker.add_grant(grant)
        self.assertFalse(self.broker.authorize(self.request, now=self.now).allowed)

    def test_timezone_naive_expiry_is_rejected(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, datetime.now()
        )
        with self.assertRaises(ValueError):
            self.broker.add_grant(grant)

    def test_naive_authorization_time_is_denied(self):
        self.broker.add_grant(self.grant)
        result = self.broker.authorize(self.request, now=datetime.now())
        self.assertFalse(result.allowed)

    def test_multi_use_grant_is_bounded(self):
        grant = CapabilityGrant(
            self.grant.subject, self.grant.action, self.grant.resource,
            self.grant.risk, self.grant.expires_at, max_uses=2
        )
        self.broker.add_grant(grant)
        self.assertTrue(self.broker.authorize(self.request, now=self.now).allowed)
        self.assertTrue(self.broker.authorize(self.request, now=self.now).allowed)
        self.assertFalse(self.broker.authorize(self.request, now=self.now).allowed)

    def test_authorization_events_are_append_only_from_public_api(self):
        self.broker.add_grant(self.grant)
        self.broker.authorize(self.request, now=self.now)
        events = self.broker.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["grant_id"], self.grant.grant_id)

    def test_audit_limit_is_validated(self):
        with self.assertRaises(ValueError):
            self.broker.list_events(0)


if __name__ == "__main__":
    unittest.main()
