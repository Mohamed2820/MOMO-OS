"""Adversarial safety tests for the MOMO autonomous patch worker."""
from pathlib import Path
import tempfile
import unittest

from intelligence.autonomy.runner import _allowed, _validate_patch, WorkerError


def text_patch(path="intelligence/runtime/example.py"):
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n-old\n+new\n"
    )


class AutonomyPolicyTests(unittest.TestCase):
    def test_allows_scoped_source_and_test_files(self):
        self.assertTrue(_allowed("intelligence/runtime/example.py"))
        self.assertTrue(_allowed("tests/test_example.py"))
        self.assertTrue(_allowed("docs/USER_GUIDE.md"))
        self.assertTrue(_allowed("platform_adapters/example.py"))

    def test_blocks_protected_contracts_and_security_paths(self):
        for path in (
            ".github/workflows/ci.yml",
            ".git/config",
            "security/capability.schema.json",
            "intelligence/autonomy/runner.py",
            "intelligence/runtime/execution_gate.py",
            "platform_adapters/typed_executor.py",
            "docs/ROADMAP.md",
            "docs/ARCHITECTURE.md",
            "docs/MOMO_CELL.md",
            "docs/MASTER_EXECUTION_PLAN.md",
            "docs/SRS.md",
            "docs/REQUIREMENTS_TRACEABILITY.md",
            "docs/decisions/ADR-001.md",
            "docs/contracts/task.json",
            "docs/SECURITY.md",
            "board/momo/kernel.config",
            "board/momo/rootfs-overlay/etc/init.d/S99init",
            "secrets/provider.key",
        ):
            with self.subTest(path=path):
                self.assertFalse(_allowed(path))

    def test_blocks_traversal_absolute_ambiguous_and_control_paths(self):
        for path in (
            "../README.md", "/tmp/payload.py", "intelligence/../security/p.py",
            "intelligence//runtime/a.py", "intelligence/./runtime/a.py",
            "intelligence/runtime/a.py\n",
            "intelligence/runtime/a b.py", "intelligence/runtime/a\\b.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(_allowed(path))

    def test_accepts_small_standard_in_place_text_patch(self):
        _validate_patch(text_patch())

    def test_rejects_protected_path_even_in_patch_headers(self):
        for path in ("docs/ROADMAP.md", "docs/ARCHITECTURE.md", ".github/workflows/x.yml",
                     "security/policy.json", "intelligence/autonomy/runner.py"):
            with self.subTest(path=path):
                with self.assertRaises(WorkerError):
                    _validate_patch(text_patch(path))

    def test_rejects_symlink_and_file_mode_metadata(self):
        for metadata in (
            "new file mode 120000\n",
            "old mode 100644\nnew mode 100755\n",
            "index 1111111..2222222 120000\n",
            "index 1111111..2222222 100755\n",
        ):
            with self.subTest(metadata=metadata):
                patch = text_patch().replace("index 1111111..2222222 100644\n", metadata)
                with self.assertRaises(WorkerError):
                    _validate_patch(patch)

    def test_rejects_rename_copy_submodule_and_binary_metadata(self):
        for metadata in (
            "similarity index 100%\nrename from intelligence/runtime/a.py\nrename to intelligence/runtime/b.py\n",
            "copy from intelligence/runtime/a.py\ncopy to intelligence/runtime/b.py\n",
            "Submodule commit 1234567\n",
            "GIT binary patch\n",
            "Binary files a/x and b/x differ\n",
        ):
            with self.subTest(metadata=metadata):
                with self.assertRaises(WorkerError):
                    _validate_patch(text_patch().replace("index 1111111..2222222 100644\n", metadata))

    def test_rejects_creation_deletion_and_path_substitution(self):
        new_file = text_patch().replace("--- a/intelligence/runtime/example.py",
                                         "--- /dev/null")
        deleted = text_patch().replace("+++ b/intelligence/runtime/example.py",
                                       "+++ /dev/null")
        renamed = text_patch().replace("diff --git a/intelligence/runtime/example.py b/intelligence/runtime/example.py",
                                       "diff --git a/intelligence/runtime/example.py b/intelligence/runtime/other.py")
        for patch in (new_file, deleted, renamed):
            with self.subTest(patch=patch[:100]):
                with self.assertRaises(WorkerError):
                    _validate_patch(patch)

    def test_rejects_symlinked_patch_target_and_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            (outside / "target.py").write_text("safe", encoding="utf-8")
            (root / "intelligence").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(WorkerError):
                _validate_patch(text_patch("intelligence/target.py"), root)

    def test_rejects_mismatched_and_quoted_diff_headers(self):
        mismatch = text_patch().replace("--- a/intelligence/runtime/example.py",
                                        "--- a/intelligence/runtime/other.py")
        quoted = text_patch().replace(
            "diff --git a/intelligence/runtime/example.py b/intelligence/runtime/example.py",
            'diff --git "a/intelligence/runtime/example.py" "b/intelligence/runtime/example.py"',
        )
        for patch in (mismatch, quoted):
            with self.subTest(patch=patch[:100]):
                with self.assertRaises(WorkerError):
                    _validate_patch(patch)

    def test_rejects_oversized_empty_and_headerless_patches(self):
        for patch in ("", "x" * 50_000,
                      "--- a/intelligence/runtime/a.py\n+++ b/intelligence/runtime/a.py\n@@ -1 +1 @@\n-a\n+b\n"):
            with self.subTest(length=len(patch)):
                with self.assertRaises(WorkerError):
                    _validate_patch(patch)


if __name__ == "__main__":
    unittest.main()
