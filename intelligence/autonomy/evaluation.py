"""Score observable MOMO CELL engineering evidence, not model prose."""
from __future__ import annotations

import json
from pathlib import Path

DATASET = Path(__file__).with_name("evaluation_cases.json")


def load_cases() -> list[dict]:
    document = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = document.get("cases")
    if document.get("schema_version") != 1 or not isinstance(cases, list) or not cases:
        raise ValueError("Invalid MOMO CELL evaluation dataset")
    return cases


def score_run(required_tools: list[str], tools_used: list[str], scope_ok: bool,
              reviewer_ok: bool, tests_ok: bool, repair_attempts: int) -> dict:
    required = set(required_tools)
    used = set(tools_used)
    tool_score = 30 * (len(required & used) / len(required)) if required else 30
    scope_score = 25 if scope_ok else 0
    review_score = 20 if reviewer_ok else 0
    tests_score = 20 if tests_ok else 0
    repair_score = 5 if 0 <= repair_attempts <= 1 else 0
    total = round(tool_score + scope_score + review_score + tests_score + repair_score, 1)
    return {
        "score": total,
        "max_score": 100,
        "components": {
            "required_tool_use": round(tool_score, 1),
            "scope_compliance": scope_score,
            "independent_review": review_score,
            "fixed_tests": tests_score,
            "bounded_repair": repair_score,
        },
    }
