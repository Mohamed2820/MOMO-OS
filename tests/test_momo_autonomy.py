"""Safety tests for the MOMO autonomous patch worker."""
import unittest

from intelligence.autonomy.runner import _allowed, _validate_patch, WorkerError


class AutonomyPolicyTests(unittest.TestCase):
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
