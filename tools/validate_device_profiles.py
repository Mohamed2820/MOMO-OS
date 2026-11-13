"""Validate MOMO device profiles against the checked-in JSON Schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "manifests/device-profile.schema.json"
PROFILE_DIR = ROOT / "manifests/device-profiles"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    profiles = sorted(PROFILE_DIR.glob("*.json"))
    if not profiles:
        print("No device profiles found.", file=sys.stderr)
        return 1

    failures = 0
    for path in profiles:
        instance = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            failures += 1
            for error in errors:
                location = ".".join(str(part) for part in error.path) or "<root>"
                print(f"{path}: {location}: {error.message}", file=sys.stderr)
        else:
            print(f"Valid device profile: {path.relative_to(ROOT)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
