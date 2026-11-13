import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


class DeviceProfileSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / "manifests/device-profile.schema.json").read_text()
        )
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema, format_checker=FormatChecker()
        )

    def test_template_is_valid(self):
        profile = json.loads(
            (ROOT / "manifests/device-profiles/template.json").read_text()
        )
        self.assertEqual(list(self.validator.iter_errors(profile)), [])

    def test_unknown_platform_is_rejected(self):
        profile = json.loads(
            (ROOT / "manifests/device-profiles/template.json").read_text()
        )
        profile["platform_track"] = "magic-universal"
        self.assertTrue(list(self.validator.iter_errors(profile)))

    def test_unknown_feature_state_is_rejected(self):
        profile = json.loads(
            (ROOT / "manifests/device-profiles/template.json").read_text()
        )
        profile["features"]["camera"] = "works-probably"
        self.assertTrue(list(self.validator.iter_errors(profile)))

    def test_extra_identity_fields_are_rejected(self):
        profile = json.loads(
            (ROOT / "manifests/device-profiles/template.json").read_text()
        )
        profile["identity"]["marketing_claim"] = "unverified"
        self.assertTrue(list(self.validator.iter_errors(profile)))


if __name__ == "__main__":
    unittest.main()
