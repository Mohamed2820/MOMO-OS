import unittest

from intelligence.providers.router import (
    DataClass, ModelRequest, ModelRouter, ProviderProfile, ProviderUnavailable,
)


class ModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter()
        self.local = ProviderProfile(
            "local-small", "local", frozenset({"summarize", "classify"}),
            frozenset(DataClass), 0.0, priority=50,
        )
        self.remote = ProviderProfile(
            "remote-strong", "remote", frozenset({"summarize", "reason"}),
            frozenset({DataClass.PUBLIC, DataClass.PERSONAL}), 0.002, priority=100,
        )

    def test_sensitive_data_never_routes_remote(self):
        request = ModelRequest("summarize", DataClass.SENSITIVE, 1.0)
        selected = self.router.select(request, [self.remote, self.local])
        self.assertEqual(selected.provider_id, "local-small")

    def test_restricted_data_requires_local_provider(self):
        request = ModelRequest("classify", DataClass.RESTRICTED, 1.0)
        selected = self.router.select(request, [self.remote, self.local])
        self.assertEqual(selected.locality, "local")

    def test_public_request_prefers_local_when_requested(self):
        request = ModelRequest("summarize", DataClass.PUBLIC, 1.0, prefer_local=True)
        selected = self.router.select(request, [self.remote, self.local])
        self.assertEqual(selected.locality, "local")

    def test_remote_can_be_selected_when_local_not_preferred(self):
        request = ModelRequest("reason", DataClass.PUBLIC, 1.0, prefer_local=False)
        selected = self.router.select(request, [self.remote, self.local])
        self.assertEqual(selected.provider_id, "remote-strong")

    def test_cost_limit_is_enforced(self):
        request = ModelRequest("reason", DataClass.PUBLIC, 0.001, prefer_local=False)
        with self.assertRaises(ProviderUnavailable):
            self.router.select(request, [self.remote])

    def test_capability_must_match(self):
        request = ModelRequest("translate", DataClass.PUBLIC, 1.0)
        with self.assertRaises(ProviderUnavailable):
            self.router.select(request, [self.local, self.remote])

    def test_disabled_provider_is_ignored(self):
        disabled = ProviderProfile(
            "off", "local", frozenset({"summarize"}), frozenset(DataClass),
            0.0, enabled=False,
        )
        request = ModelRequest("summarize", DataClass.PUBLIC, 1.0)
        with self.assertRaises(ProviderUnavailable):
            self.router.select(request, [disabled])

    def test_local_only_request_never_selects_remote(self):
        request = ModelRequest("summarize", DataClass.PERSONAL, 1.0, require_local=True)
        selected = self.router.select(request, [self.remote, self.local])
        self.assertEqual(selected.locality, "local")


if __name__ == "__main__":
    unittest.main()
