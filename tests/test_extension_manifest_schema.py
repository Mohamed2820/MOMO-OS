"""Validation tests for the declarative MOMO extension manifest contract."""
import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "security/extension-manifest.schema.json").read_text(encoding="utf-8"))


def valid_manifest():
    return {
        "schema_version": 1,
        "extension_id": "momo.example-inspector",
        "version": "1.2.3",
        "runtime": "wasm32-wasi",
        "entrypoint": "extension.wasm",
        "artifact_sha256": "a" * 64,
        "capabilities": ["repo.read", "test.run"],
        "permissions": [
            {
                "capability": "repo.read",
                "scope": "workspace/**",
                "risk": "R1",
                "approval_mode": "standing_scoped",
                "reason": "Read source files in the assigned workspace",
            },
            {
                "capability": "test.run",
                "scope": "workspace/tests/**",
                "risk": "R3",
                "approval_mode": "per_call",
                "reason": "Run the declared test suite in an ephemeral workspace",
            },
        ],
        "data_classification": "public",
        "network": {"mode": "none", "hosts": []},
        "workspace": {"mode": "ephemeral", "read_only": False},
    }


class ExtensionManifestSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Draft202012Validator.check_schema(SCHEMA)
        cls.validator = Draft202012Validator(SCHEMA)

    def test_accepts_least_privilege_ephemeral_extension(self):
        self.validator.validate(valid_manifest())

    def test_rejects_r3_permission_without_per_call_approval(self):
        manifest = valid_manifest()
        manifest["permissions"][1]["approval_mode"] = "standing_scoped"
        self.assertTrue(list(self.validator.iter_errors(manifest)))

    def test_rejects_path_traversal_entrypoint(self):
        manifest = valid_manifest()
        manifest["entrypoint"] = "../outside.wasm"
        self.assertTrue(list(self.validator.iter_errors(manifest)))

    def test_rejects_network_hosts_when_network_is_disabled(self):
        manifest = valid_manifest()
        manifest["network"] = {"mode": "none", "hosts": ["example.com"]}
        self.assertTrue(list(self.validator.iter_errors(manifest)))

    def test_rejects_missing_or_malformed_artifact_digest(self):
        manifest = valid_manifest()
        manifest["artifact_sha256"] = "not-a-sha256"
        self.assertTrue(list(self.validator.iter_errors(manifest)))

    def test_rejects_unknown_manifest_fields(self):
        manifest = valid_manifest()
        manifest["shell_access"] = True
        self.assertTrue(list(self.validator.iter_errors(manifest)))


if __name__ == "__main__":
    unittest.main()
