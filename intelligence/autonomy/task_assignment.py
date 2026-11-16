"""Validate a human-assigned GitHub Issue as one bounded MOMO CELL task."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from intelligence.autonomy.policy import WorkerError, _allowed

READY_LABEL = "momo-cell:ready"
REQUIRED_SECTIONS = (
    "Objective", "Acceptance Criteria", "Files in Scope",
    "Prohibited Areas", "Test Commands", "Expected Evidence",
)


def _parse_sections(body: str) -> dict[str, str]:
    headings = list(re.finditer(r"^###[ \t]+(.+?)[ \t]*$", body, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).strip()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        if name in sections:
            raise WorkerError("Duplicate task-contract section: " + name)
        sections[name] = body[heading.end():end].strip()
    return sections


def parse_task_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Reject anything except one open, labeled, fully specified GitHub Issue."""
    if not isinstance(issue, dict):
        raise WorkerError("Assigned task payload is malformed")
    number = issue.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise WorkerError("Assigned task has an invalid issue number")
    if issue.get("state") != "open" or issue.get("pull_request"):
        raise WorkerError("Assigned task must be an open GitHub Issue, not a pull request")
    labels = issue.get("labels")
    if not isinstance(labels, list) or READY_LABEL not in {
        label.get("name") for label in labels if isinstance(label, dict)
    }:
        raise WorkerError("Assigned task is not labeled momo-cell:ready")
    title, body = issue.get("title"), issue.get("body")
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise WorkerError("Assigned task title is missing or malformed")
    if not isinstance(body, str) or not body.strip() or len(body.encode("utf-8")) > 24000:
        raise WorkerError("Assigned task brief is missing or exceeds 24 KB")
    if "## MOMO CELL Task Contract" not in body:
        raise WorkerError("Missing MOMO CELL Task Contract marker")

    sections = _parse_sections(body)
    missing = [name for name in REQUIRED_SECTIONS if not sections.get(name)]
    if missing:
        raise WorkerError("Task contract is missing: " + ", ".join(missing))

    files: list[str] = []
    for line in sections["Files in Scope"].splitlines():
        match = re.fullmatch(r"[ \t]*[-*][ \t]+([A-Za-z0-9._/-]+)[ \t]*", line)
        if not match:
            raise WorkerError("Files in Scope must list exact repository paths, one per bullet")
        path = match.group(1)
        if not _allowed(path):
            raise WorkerError("Task scope contains a path prohibited by Stage 1: " + path)
        if path in files:
            raise WorkerError("Task scope contains a duplicate path: " + path)
        files.append(path)
    if not files or len(files) > 8:
        raise WorkerError("Task must name between one and eight exact files")

    criteria = [
        line.strip()[2:].strip()
        for line in sections["Acceptance Criteria"].splitlines()
        if line.strip().startswith(("- ", "* "))
    ]
    if not criteria:
        raise WorkerError("At least one bullet-point acceptance criterion is required")

    immutable_brief = "\n".join((str(number), title.strip(), body.strip()))
    return {
        "task_id": number,
        "title": title.strip(),
        "objective": sections["Objective"],
        "acceptance_criteria": criteria,
        "files_in_scope": files,
        "prohibited_areas": sections["Prohibited Areas"],
        "test_commands": sections["Test Commands"],
        "expected_evidence": sections["Expected Evidence"],
        "brief_sha256": hashlib.sha256(immutable_brief.encode("utf-8")).hexdigest(),
    }


def validate_task_response(document: Any, task: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("status") not in {"patch", "blocked"}:
        raise WorkerError("Provider response did not satisfy the JSON task contract")
    if str(document.get("task_id", "")) != str(task["task_id"]):
        raise WorkerError("Provider response task ID differs from the assigned Issue")
    if not isinstance(document.get("task"), str) or not isinstance(document.get("summary"), str):
        raise WorkerError("Provider response is missing task or summary text")
    if document["status"] == "patch" and not isinstance(document.get("patch"), str):
        raise WorkerError("Provider patch must be a string")
    if document["status"] == "blocked" and document.get("patch") not in (None, ""):
        raise WorkerError("Blocked provider response must not contain a patch")
    return document
