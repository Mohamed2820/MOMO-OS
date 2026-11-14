"""Safety tests for the MOMO autonomous patch worker."""
import unittest

from intelligence.autonomy.runner import (
    OVH_ANONYMOUS_API_URL,
    OVH_ANONYMOUS_MODEL,
    _allowed,
    _extract_completion_document,
    _provider_configuration,
    _validate_patch,
    WorkerError,
)


class AutonomyPolicyTests(unittest.TestCase):
    def test_keyless_mode_defaults_to_restricted_ovh_provider(self):
        url, model, key, keyless = _provider_configuration({})
        self.assertEqual(url, OVH_ANONYMOUS_API_URL)
        self.assertEqual(model, OVH_ANONYMOUS_MODEL)
        self.assertIsNone(key)
        self.assertTrue(keyless)

    def test_keyless_mode_accepts_ovh_base_url_only(self):
        url, model, key, keyless = _provider_configuration({
            "MOMO_AGENT_API_URL": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        })
        self.assertEqual(url, OVH_ANONYMOUS_API_URL)
        self.assertTrue(keyless)

    def test_keyless_mode_refuses_untrusted_or_arbitrary_providers(self):
        with self.assertRaises(WorkerError):
            _provider_configuration({
                "MOMO_AGENT_API_URL": "https://example.com/v1/chat/completions",
            })

    def test_authenticated_mode_requires_model_and_preserves_provider_config(self):
        with self.assertRaises(WorkerError):
            _provider_configuration({"MOMO_AGENT_API_KEY": "test-secret"})
        url, model, key, keyless = _provider_configuration({
            "MOMO_AGENT_API_KEY": "test-secret",
            "MOMO_AGENT_MODEL": "provider/model",
            "MOMO_AGENT_API_URL": "https://gateway.example/v1/chat/completions",
        })
        self.assertEqual(url, "https://gateway.example/v1/chat/completions")
        self.assertEqual(model, "provider/model")
        self.assertEqual(key, "test-secret")
        self.assertFalse(keyless)

    def test_extracts_plain_json_completion(self):
        document = _extract_completion_document({
            "choices": [{"message": {"role": "assistant", "content": '{"status":"blocked","task":"none","summary":"No safe task","patch":""}'}}],
        })
        self.assertEqual(document["status"], "blocked")

    def test_extracts_fenced_json_completion(self):
        document = _extract_completion_document({
            "choices": [{"message": {"role": "assistant", "content": ' ```json\\n{"status":"blocked","patch":""}\\n``` '}}],
        })
        self.assertEqual(document["status"], "blocked")

    def test_extracts_text_segments_from_compatible_content_array(self):
        document = _extract_completion_document({
            "choices": [{"message": {"role": "assistant", "content": [
                {"type": "text", "text": '{"status":"blocked",'},
                {"type": "output_text", "text": '"patch":""}'},
            ]}}],
        })
        self.assertEqual(document["status"], "blocked")

    def test_rejects_reasoning_only_or_truncated_completion(self):
        with self.assertRaises(WorkerError):
            _extract_completion_document({
                "choices": [{"finish_reason": "length", "message": {"role": "assistant", "reasoning": "not a final answer"}}],
            })

    def test_allows_source_and_test_files(self):
        self.assertTrue(_allowed("intelligence/runtime/example.py"))
        self.assertTrue(_allowed("tests/test_example.py"))
        self.assertTrue(_allowed("docs/ROADMAP.md"))

    def test_blocks_policy_and_workflow_files(self):
        for path in (
            ".github/workflows/ci.yml",
            "security/capability.schema.json",
            "intelligence/autonomy/runner.py",
            "docs/SECURITY.md",
            "docs/MASTER_EXECUTION_PLAN.md",
            "board/momo/kernel.config",
        ):
            with self.subTest(path=path):
                self.assertFalse(_allowed(path))

    def test_blocks_path_traversal_and_absolute_paths(self):
        self.assertFalse(_allowed("../README.md"))
        self.assertFalse(_allowed("/tmp/payload.py"))

    def test_accepts_small_source_patch(self):
        patch = (
            "--- a/intelligence/runtime/example.py\n"
            "+++ b/intelligence/runtime/example.py\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        _validate_patch(patch)

    def test_rejects_security_patch(self):
        patch = (
            "--- a/security/policy.json\n"
            "+++ b/security/policy.json\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        with self.assertRaises(WorkerError):
            _validate_patch(patch)

    def test_rejects_oversized_or_empty_patch(self):
        with self.assertRaises(WorkerError):
            _validate_patch("")
        with self.assertRaises(WorkerError):
            _validate_patch("x" * 50_000)


if __name__ == "__main__":
    unittest.main()
