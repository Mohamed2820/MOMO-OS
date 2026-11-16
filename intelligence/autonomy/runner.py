"""One-shot, policy-bounded autonomous repository repair worker."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import urllib.error
import urllib.request

from intelligence.autonomy.policy import WorkerError, _allowed
from intelligence.autonomy.task_assignment import parse_task_issue, validate_task_response

def _run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], check=check, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30,
    )


API_URL = os.environ.get("MOMO_AGENT_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.environ.get("MOMO_AGENT_MODEL", "")
FALLBACK_MODELS = tuple(dict.fromkeys(
    model.strip()
    for model in os.environ.get(
        "MOMO_AGENT_FALLBACK_MODELS", "openrouter/free"
    ).split(",")
    if model.strip()
))
MAX_CONTEXT_BYTES = 110_000
MAX_PATCH_BYTES = 48_000
MAX_FILES = 24
MAX_FILE_BYTES = 18_000


def _safe_regular_file(root: Path, relative: str) -> Path | None:
    """Resolve a tracked regular file without traversing symlink components."""
    candidate = root
    for part in PurePosixPath(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return None
    return candidate if candidate.is_file() else None


def _snapshot(root: Path, allowed_files: set[str] | None = None) -> str:
    listing = _run_git("ls-files", "-z").stdout.split("\0")
    chunks: list[str] = []
    used = 0
    count = 0
    for relative in listing:
        if not relative or not _allowed(relative) or (allowed_files is not None and relative not in allowed_files):
            continue
        path = _safe_regular_file(root, relative)
        if path is None:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) > MAX_FILE_BYTES:
            continue
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        block = f"\n--- FILE: {relative} ---\n{decoded}\n"
        encoded_size = len(block.encode("utf-8"))
        if used + encoded_size > MAX_CONTEXT_BYTES or count >= MAX_FILES:
            break
        chunks.append(block)
        used += encoded_size
        count += 1
    return "".join(chunks)


MAX_PROJECT_BRIEF_CHARS = 6_000


def _project_brief(root: Path) -> str:
    # Keep reference material bounded so small-context/low-credit models can
    # still receive the actual assigned file and task contract.
    limits = (
        ("docs/MASTER_EXECUTION_PLAN.md", 2_500),
        ("docs/ROADMAP.md", 1_500),
        ("docs/ARCHITECTURE.md", 1_000),
    )
    parts = []
    for name, limit in limits:
        path = _safe_regular_file(root, name)
        if path is not None:
            content = path.read_text(encoding="utf-8")
            parts.append(f"\n--- PROJECT PLAN: {name} ---\n{content[-limit:]}\n")
    return "".join(parts)[:MAX_PROJECT_BRIEF_CHARS]


def _parse_model_document(content: object) -> dict:
    """Parse a JSON object even when a provider wraps it in prose or fences."""
    if isinstance(content, dict):
        # Some OpenAI-compatible providers wrap text or parsed JSON in an object.
        if isinstance(content.get("text"), str):
            content = content["text"]
        elif isinstance(content.get("json"), str):
            content = content["json"]
        elif isinstance(content.get("content"), str):
            content = content["content"]
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str) or not content.strip():
        raise WorkerError("Provider returned empty or unsupported message content")
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", candidate, flags=re.IGNORECASE)
    try:
        document = json.loads(candidate)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        document = None
        for index, character in enumerate(candidate):
            if character == "{":
                try:
                    value, _ = decoder.raw_decode(candidate[index:])
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    document = value
                    break
    if not isinstance(document, dict):
        raise WorkerError("Provider response did not contain a valid JSON object")
    return document


def _recover_raw_diff(content: object, task: dict) -> dict | None:
    """Recover a plain unified diff when a model omits the requested JSON wrapper."""
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str):
        return None
    start = content.find("diff --git ")
    if start < 0:
        return None
    patch = content[start:].strip()
    return {
        "task_id": task["task_id"],
        "status": "patch",
        "task": task["title"],
        "summary": "Recovered a plain unified diff from the provider response.",
        "patch": patch,
    }


def _request_patch(context: str, brief: str, task: dict, api_key: str,
                   root: Path | None = None, feedback: str = "") -> dict:
    """Run the bounded tool-calling agent loop; the model never writes files directly."""
    from intelligence.autonomy.agent_runtime import load_memory, run_agent_cycle

    workspace = root or Path.cwd()
    return run_agent_cycle(
        workspace, task, brief, load_memory(workspace), api_key,
        API_URL, MODEL, FALLBACK_MODELS, _validate_patch, feedback, context,
    )


def _validate_patch(patch: str, root: Path | None = None, allowed_files: set[str] | None = None) -> None:
    """Accept only ordinary in-place text edits to explicitly allowed files."""
    if not isinstance(patch, str) or not patch.strip():
        raise WorkerError("The proposed patch is empty")
    if len(patch.encode("utf-8")) > MAX_PATCH_BYTES:
        raise WorkerError("The proposed patch exceeds the size budget")
    if "\x00" in patch or "\r" in patch:
        raise WorkerError("The patch contains unsupported control characters")

    sections: list[tuple[str, str, str]] = []
    current: dict[str, object] | None = None
    in_hunk = False
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            if current is not None:
                if not current.get("old") or not current.get("new") or not current.get("hunk"):
                    raise WorkerError("Incomplete unified diff section")
                sections.append((str(current["old"]), str(current["new"]), str(current["path"])))
            parts = line.split(" ")
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise WorkerError("Malformed or quoted git diff header")
            old_path, new_path = parts[2][2:], parts[3][2:]
            if old_path != new_path:
                raise WorkerError("Renames and path substitutions are not accepted")
            current = {"old": "", "new": "", "path": old_path, "index": False, "hunk": False}
            in_hunk = False
            continue
        if current is None:
            raise WorkerError("Patch content appears before a git diff header")
        if line.startswith(("old mode ", "new mode ", "new file mode ", "deleted file mode ",
                            "similarity index ", "dissimilarity index ", "rename from ",
                            "rename to ", "copy from ", "copy to ", "GIT binary patch",
                            "Binary files ", "Submodule ")):
            raise WorkerError("Binary, rename, copy, symlink, mode and submodule changes are not accepted")
        if in_hunk:
            if line.startswith((" ", "+", "-", "\\ No newline at end of file")):
                continue
            raise WorkerError("Unsupported metadata inside or after a text hunk")
        if line.startswith("index "):
            if current["index"] or not re.fullmatch(r"index [0-9a-f]{7,40}\.\.[0-9a-f]{7,40} 100644", line):
                raise WorkerError("Only regular non-executable file mode 100644 is accepted")
            current["index"] = True
        elif line.startswith("--- "):
            # The git index line is optional in a valid unified diff. Path,
            # scope, file-existence, and git-apply checks remain authoritative.
            if current["old"]:
                raise WorkerError("Malformed unified diff old-path header")
            value = line[4:]
            if not value.startswith("a/"):
                raise WorkerError("File creation/deletion and unsupported old paths are not accepted")
            current["old"] = value[2:]
        elif line.startswith("+++ "):
            if not current["old"] or current["new"]:
                raise WorkerError("Malformed unified diff new-path header")
            value = line[4:]
            if not value.startswith("b/"):
                raise WorkerError("File creation/deletion and unsupported new paths are not accepted")
            current["new"] = value[2:]
        elif line.startswith("@@ "):
            if not current["old"] or not current["new"] or current["old"] != current["new"]:
                raise WorkerError("Each patch section must modify an existing file in place")
            if current["path"] != current["old"]:
                raise WorkerError("Git diff path and unified diff paths do not match")
            if not _allowed(str(current["old"])):
                raise WorkerError("Patch violates path policy: " + str(current["old"]))
            if allowed_files is not None and str(current["old"]) not in allowed_files:
                raise WorkerError("Patch modifies a file outside the assigned task scope: " + str(current["old"]))
            if root is not None:
                target = root
                for part in PurePosixPath(str(current["old"])).parts:
                    target = target / part
                    if target.is_symlink():
                        raise WorkerError("Symlink targets and symlink parent directories are not accepted")
                if not target.is_file():
                    raise WorkerError("Only existing regular files may be modified")
            current["hunk"] = True
            in_hunk = True
        else:
            raise WorkerError("Unsupported or ambiguous patch metadata")

    if current is not None:
        if not current.get("old") or not current.get("new") or not current.get("hunk"):
            raise WorkerError("Incomplete unified diff section")
        sections.append((str(current["old"]), str(current["new"]), str(current["path"])))
    if not sections:
        raise WorkerError("The patch contains no standard git diff sections")
    if len(sections) > 8:
        raise WorkerError("The patch changes more than eight files")
    seen: set[str] = set()
    for old_path, new_path, diff_path in sections:
        if not old_path or old_path != new_path or diff_path != old_path:
            raise WorkerError("Each patch section must modify one existing path in place")
        if old_path in seen:
            raise WorkerError("Duplicate file sections are not accepted")
        seen.add(old_path)
        if not _allowed(old_path):
            raise WorkerError("Patch violates path policy: " + old_path)
        if allowed_files is not None and old_path not in allowed_files:
            raise WorkerError("Patch modifies a file outside the assigned task scope: " + old_path)

def _fetch_assigned_issue(number: str, repository: str, token: str) -> dict:
    if not re.fullmatch(r"[1-9][0-9]{0,8}", number or ""):
        raise WorkerError("MOMO_TASK_ISSUE_NUMBER must be a positive issue number.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository or ""):
        raise WorkerError("GITHUB_REPOSITORY is missing or malformed.")
    if not token:
        raise WorkerError("GITHUB_TOKEN is unavailable; issue lookup is disabled.")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    request = urllib.request.Request(
        f"{api}/repos/{repository}/issues/{number}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"}, method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read(300_000).decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorkerError(f"Assigned GitHub Issue could not be retrieved: {type(exc).__name__}") from exc


def run(root: Path) -> int:
    api_key = os.environ.get("MOMO_AGENT_API_KEY", "")
    if not api_key or not MODEL:
        raise WorkerError("Configure MOMO_AGENT_API_KEY secret and MOMO_AGENT_MODEL variable.")
    task = parse_task_issue(_fetch_assigned_issue(
        os.environ.get("MOMO_TASK_ISSUE_NUMBER", ""),
        os.environ.get("GITHUB_REPOSITORY", ""),
        os.environ.get("GITHUB_TOKEN", ""),
    ))
    allowed_files = set(task["files_in_scope"])
    for relative in allowed_files:
        if _safe_regular_file(root, relative) is None:
            raise WorkerError("Assigned task scope must name existing regular files: " + relative)
    if _run_git("status", "--porcelain").stdout.strip():
        raise WorkerError("Repository must be clean before the assigned task starts.")
    related_context = {
        "tests/test_momo_task_assignment.py": {"intelligence/autonomy/task_assignment.py"},
        "tests/test_momo_autonomy.py": {"intelligence/autonomy/runner.py", "intelligence/autonomy/policy.py"},
        "tests/test_momo_agent_runtime.py": {"intelligence/autonomy/agent_runtime.py", "intelligence/autonomy/evaluation.py"},
    }
    context_files = set(allowed_files)
    for relative in allowed_files:
        context_files.update(related_context.get(relative, set()))
    context = _snapshot(root, context_files)
    brief = _project_brief(root)
    if not context or not brief:
        raise WorkerError("Required repository context is unavailable.")

    from intelligence.autonomy.agent_runtime import append_memory, review_patch, run_fixed_tests
    from intelligence.autonomy.evaluation import load_cases, score_run

    def apply_candidate(candidate: dict) -> tuple[str, list[str]]:
        patch_text = candidate.get("patch")
        _validate_patch(patch_text, root, allowed_files)
        patch_file = root / ".momo-cell-proposal.patch"
        try:
            patch_file.write_text(patch_text, encoding="utf-8")
            _run_git("apply", "--check", str(patch_file))
            _run_git("apply", str(patch_file))
            _run_git("diff", "--check")
            files = sorted(set(_run_git("diff", "--name-only").stdout.splitlines()))
            if not files or not set(files).issubset(allowed_files):
                raise WorkerError("Applied diff does not match the exact assigned task scope.")
            return patch_text, files
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise WorkerError("Patch failed validation/application; no commit was created.") from exc
        finally:
            patch_file.unlink(missing_ok=True)

    proposal = _request_patch(context, brief, task, api_key, root=root)
    if proposal["status"] == "blocked":
        print(json.dumps({
            "status": "blocked", "task_id": task["task_id"],
            "model": str(proposal.get("served_model", MODEL))[:160],
            "reason": str(proposal.get("summary", "No safe task available"))[:1000],
            "tools_used": proposal.get("tools_used", []),
        }))
        return 2

    patch = proposal.get("patch")
    reviewer = review_patch(task, patch, proposal.get("served_model", MODEL), api_key, API_URL)
    patch, changed_files = apply_candidate(proposal)
    verification = run_fixed_tests(root)
    repair_lesson = ""
    if not verification["passed"]:
        failure = json.dumps(verification, ensure_ascii=False)[:6500]
        repair_lesson = "Initial candidate failed fixed verification; a bounded repair was requested."
        _run_git("restore", "--", *changed_files)
        feedback = (
            "Previous candidate diff (do not blindly repeat):\n" + patch[:18000] +
            "\nFixed verification failure evidence:\n" + failure +
            "\nRepair the underlying defect minimally. Re-inspect current files, validate the new patch, "
            "and do not claim that the failed run passed."
        )
        proposal = _request_patch(context, brief, task, api_key, root=root, feedback=feedback)
        if proposal.get("status") != "patch":
            raise WorkerError("Bounded repair attempt was blocked after test failure")
        patch = proposal.get("patch")
        reviewer = review_patch(task, patch, proposal.get("served_model", MODEL), api_key, API_URL)
        patch, changed_files = apply_candidate(proposal)
        verification = run_fixed_tests(root)
        if not verification["passed"]:
            _run_git("restore", "--", *changed_files)
            raise WorkerError("Fixed tests still fail after the single permitted repair attempt")

    changed_files = sorted(set(_run_git("diff", "--name-only").stdout.splitlines()))
    if not changed_files or not set(changed_files).issubset(allowed_files):
        raise WorkerError("Final candidate changed files outside the assigned task scope.")
    benchmark_cases = load_cases()
    required_tools = next(
        (case["required_tools"] for case in benchmark_cases if case["id"] == "repo-navigation"),
        ["read_repo_file", "validate_patch"],
    )
    evaluation_score = score_run(
        required_tools, proposal.get("tools_used", []), True, True, True,
        1 if repair_lesson else 0,
    )
    append_memory(root, {
        "task_id": task["task_id"], "title": task["title"],
        "served_model": proposal.get("served_model", MODEL),
        "reviewer_model": reviewer.get("served_model"),
        "summary": str(proposal.get("summary", ""))[:1000],
        "tests_passed": True, "changed_files": changed_files,
        "tool_calls": proposal.get("tool_calls", 0),
        "tools_used": proposal.get("tools_used", []),
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        "evaluation_score": evaluation_score,
        "lessons": repair_lesson or "Patch passed independent review and fixed verification on first attempt.",
    })
    print(json.dumps({
        "status": "patch_applied", "task_id": task["task_id"],
        "task": str(proposal.get("task", ""))[:200],
        "summary": str(proposal.get("summary", ""))[:1000],
        "model": str(proposal.get("served_model", MODEL))[:160],
        "reviewer_model": reviewer.get("served_model"),
        "review": reviewer.get("summary", ""),
        "tool_calls": proposal.get("tool_calls", 0),
        "tools_used": proposal.get("tools_used", []),
        "verification_passed": verification["passed"],
        "evaluation_score": evaluation_score,
        "repair_used": bool(repair_lesson),
        "changed_files": changed_files,
    }, ensure_ascii=False))
    return 0


def main() -> int:
    try:
        return run(Path.cwd().resolve())
    except WorkerError as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
