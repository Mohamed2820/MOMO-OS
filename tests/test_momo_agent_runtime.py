"""Deterministic tests for MOMO CELL's typed tool runtime."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from intelligence.autonomy.agent_runtime import (
    MEMORY_PATH, TOOLS, _execute_tool, _list_files, _read_file, _search_repo,
    _serialize_tool_result,
    append_memory, load_memory, review_patch, run_agent_cycle,
)
from intelligence.autonomy.policy import WorkerError
from intelligence.autonomy.runner import _validate_patch


def make_repo(root: Path) -> None:
    target = root / "intelligence/runtime/demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 'old'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "intelligence/runtime/demo.py"], check=True)


def sample_task():
    return {
        "task_id": 901,
        "title": "Update demo value",
        "objective": "Change the existing value",
        "acceptance_criteria": ["VALUE must equal new"],
        "files_in_scope": ["intelligence/runtime/demo.py"],
        "prohibited_areas": "No other paths",
        "test_commands": "Fixed suite only",
        "expected_evidence": "Valid diff",
        "brief_sha256": "a" * 64,
    }


def sample_patch():
    return (
        "diff --git a/intelligence/runtime/demo.py b/intelligence/runtime/demo.py\n"
        "--- a/intelligence/runtime/demo.py\n"
        "+++ b/intelligence/runtime/demo.py\n"
        "@@ -1 +1 @@\n"
        "-VALUE = 'old'\n"
        "+VALUE = 'new'\n"
    )


class AgentToolRuntimeTests(unittest.TestCase):
    def test_only_policy_readable_tracked_files_are_listed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            result = _list_files(root, "intelligence/")
            self.assertEqual(result["files"], ["intelligence/runtime/demo.py"])
            self.assertFalse(_list_files(root, "security/")["files"])

    def test_search_and_read_return_bounded_source_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            found = _search_repo(root, "VALUE")
            self.assertEqual(found["matches"][0]["path"], "intelligence/runtime/demo.py")
            read = _read_file(root, "intelligence/runtime/demo.py")
            self.assertIn("VALUE = 'old'", read["content"])

    def test_protected_untracked_and_symlink_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            with self.assertRaises(WorkerError):
                _read_file(root, "security/policy.py")
            extra = root / "intelligence/runtime/untracked.py"
            extra.write_text("secret = 'not tracked'", encoding="utf-8")
            with self.assertRaises(WorkerError):
                _read_file(root, "intelligence/runtime/untracked.py")
            outside = root / "outside.py"
            outside.write_text("outside", encoding="utf-8")
            link = root / "intelligence/runtime/link.py"
            link.symlink_to(outside)
            subprocess.run(["git", "-C", str(root), "add", "intelligence/runtime/link.py"], check=True)
            with self.assertRaises(WorkerError):
                _read_file(root, "intelligence/runtime/link.py")

    def test_unknown_tool_and_arbitrary_command_are_never_executed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            with self.assertRaises(WorkerError):
                _execute_tool("run_shell", {"command": "touch pwned"}, root, sample_task(), _validate_patch)
            self.assertFalse((root / "pwned").exists())

    def test_tool_schema_is_small_and_has_no_shell_or_write_tool(self):
        names = [item["function"]["name"] for item in TOOLS]
        self.assertEqual(names, ["list_repo_files", "search_repo", "read_repo_file", "run_fixed_tests", "validate_patch", "get_recent_ci_runs", "get_ci_run_jobs"])
        self.assertNotIn("run_shell", names)
        self.assertNotIn("write_file", names)

    def test_tool_loop_reads_source_validates_patch_then_returns_proposal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            task = sample_task()
            patch_text = sample_patch()
            responses = [
                {"model": "builder-model", "choices": [{"message": {
                    "role": "assistant", "content": None, "tool_calls": [{
                        "id": "read-1", "type": "function", "function": {
                            "name": "read_repo_file",
                            "arguments": json.dumps({"path": "intelligence/runtime/demo.py"}),
                        }}]}}]},
                {"model": "builder-model", "choices": [{"message": {
                    "role": "assistant", "content": None, "tool_calls": [{
                        "id": "validate-1", "type": "function", "function": {
                            "name": "validate_patch",
                            "arguments": json.dumps({"patch": patch_text}),
                        }}]}}]},
                {"model": "builder-model", "choices": [{"message": {
                    "role": "assistant", "content": json.dumps({
                        "task_id": 901, "status": "patch", "task": "Update demo value",
                        "summary": "Changed the value", "patch": patch_text,
                    })}}]},
            ]
            with patch("intelligence.autonomy.agent_runtime._request_json", side_effect=responses):
                result = run_agent_cycle(
                    root, task, "brief", "no memory", "fake-key",
                    "https://example.invalid/chat", "builder-model", (), _validate_patch,
                )
            self.assertEqual(result["status"], "patch")
            self.assertEqual(result["tool_calls"], 2)
            self.assertEqual(result["tools_used"], ["read_repo_file", "validate_patch"])

    def test_patch_validation_failure_returns_current_numbered_source_for_one_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            task = sample_task()
            bad_patch = (
                "diff --git a/intelligence/runtime/demo.py b/intelligence/runtime/demo.py\n"
                "--- a/intelligence/runtime/demo.py\n"
                "+++ b/intelligence/runtime/demo.py\n"
                "@@ -1 +1 @@\n"
                "-VALUE = 'stale'\n"
                "+VALUE = 'new'\n"
            )
            good_patch = sample_patch()

            def tool_call(call_id, name, arguments):
                return {"id": call_id, "type": "function", "function": {
                    "name": name, "arguments": json.dumps(arguments),
                }}

            def response(call):
                return {"model": "builder-model", "choices": [{"message": {
                    "role": "assistant", "content": None, "tool_calls": [call],
                }}]}

            final = {"model": "builder-model", "choices": [{"message": {
                "role": "assistant", "content": json.dumps({
                    "task_id": 901, "status": "patch", "task": "Update demo value",
                    "summary": "Corrected the diff using current source evidence.", "patch": good_patch,
                }),
            }}]}
            responses = [
                response(tool_call("read-1", "read_repo_file", {"path": "intelligence/runtime/demo.py"})),
                response(tool_call("validate-1", "validate_patch", {"patch": bad_patch})),
                response(tool_call("validate-2", "validate_patch", {"patch": good_patch})),
                final,
            ]
            with patch("intelligence.autonomy.agent_runtime._request_json", side_effect=responses) as request:
                result = run_agent_cycle(
                    root, task, "brief", "no memory", "fake-key",
                    "https://example.invalid/chat", "builder-model", (), _validate_patch,
                )
            self.assertEqual(result["status"], "patch")
            self.assertEqual(result["tool_calls"], 3)
            self.assertEqual(request.call_count, 4)
            repair_messages = request.call_args_list[2].args[2]["messages"]
            repair_payload = json.dumps(repair_messages, ensure_ascii=False)
            self.assertIn("attempts_remaining", repair_payload)
            self.assertIn("current_file_lines", repair_payload)
            self.assertIn("VALUE = 'old'", repair_payload)

    def test_patch_validation_stops_after_two_rejected_submissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            task = sample_task()
            bad_patch = "not a unified diff"

            def tool_call(call_id, name, arguments):
                return {"id": call_id, "type": "function", "function": {
                    "name": name, "arguments": json.dumps(arguments),
                }}

            def response(call):
                return {"model": "builder-model", "choices": [{"message": {
                    "role": "assistant", "content": None, "tool_calls": [call],
                }}]}

            responses = [
                response(tool_call("read-1", "read_repo_file", {"path": "intelligence/runtime/demo.py"})),
                response(tool_call("validate-1", "validate_patch", {"patch": bad_patch})),
                response(tool_call("validate-2", "validate_patch", {"patch": bad_patch})),
            ]
            with patch("intelligence.autonomy.agent_runtime._request_json", side_effect=responses) as request:
                with self.assertRaisesRegex(WorkerError, "after the two permitted submissions"):
                    run_agent_cycle(
                        root, task, "brief", "no memory", "fake-key",
                        "https://example.invalid/chat", "builder-model", (), _validate_patch,
                    )
            self.assertEqual(request.call_count, 3)
            self.assertFalse((root / "pwned").exists())

    def test_tool_result_serialization_preserves_full_reads_and_never_breaks_json(self):
        content = "x" * 9000
        encoded = _serialize_tool_result({"path": "tests/example.py", "content": content})
        self.assertEqual(json.loads(encoded)["content"], content)

        oversized = _serialize_tool_result({"content": "y" * 30000})
        result = json.loads(oversized)
        self.assertTrue(result["truncated"])
        self.assertIn("safe message limit", result["error"])
        self.assertLess(len(oversized), 3000)

    def test_memory_is_persistent_bounded_and_does_not_require_model_control(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            append_memory(root, {
                "task_id": 901, "summary": "A safe fix", "tests_passed": True,
                "served_model": "builder", "reviewer_model": "reviewer",
            })
            self.assertTrue((root / MEMORY_PATH).is_file())
            memory = load_memory(root)
            self.assertIn("A safe fix", memory)
            self.assertIn("reviewer", memory)

    def test_independent_reviewer_must_be_a_different_model(self):
        task = sample_task()
        good = {"model": "critic-model", "choices": [{"message": {
            "content": json.dumps({"verdict": "approve", "findings": [], "summary": "Scope and logic look sound."})
        }}]}
        with patch.dict("os.environ", {"MOMO_AGENT_REVIEW_MODEL": "critic-model"}):
            with patch("intelligence.autonomy.agent_runtime._request_json", return_value=good):
                result = review_patch(task, sample_patch(), "builder-model", "fake-key", "https://example.invalid")
        self.assertTrue(result["approved"])
        same = dict(good, model="builder-model")
        with patch.dict("os.environ", {"MOMO_AGENT_REVIEW_MODEL": "critic-model"}):
            with patch("intelligence.autonomy.agent_runtime._request_json", return_value=same):
                with self.assertRaises(WorkerError):
                    review_patch(task, sample_patch(), "builder-model", "fake-key", "https://example.invalid")

    def test_github_actions_tools_are_read_only_and_repository_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_repo(root)
            task = sample_task()
            runs = {"workflow_runs": [{"id": 123, "name": "Repository validation", "event": "pull_request", "head_branch": "feature", "status": "completed", "conclusion": "success", "html_url": "https://github.com/Mohamed2820/MOMO-OS/actions/runs/123", "updated_at": "2026-11-16T00:00:00Z"}]}
            with patch("intelligence.autonomy.agent_runtime._github_get", return_value=runs) as get:
                result = _execute_tool("get_recent_ci_runs", {}, root, task, _validate_patch)
            get.assert_called_once_with("actions/runs")
            self.assertEqual(result["runs"][0]["conclusion"], "success")
            jobs = {"jobs": [{"id": 456, "name": "validate", "status": "completed", "conclusion": "success", "steps": [{"name": "Run tests", "status": "completed", "conclusion": "success"}]}]}
            with patch("intelligence.autonomy.agent_runtime._github_get", return_value=jobs) as get:
                result = _execute_tool("get_ci_run_jobs", {"run_id": 123}, root, task, _validate_patch)
            get.assert_called_once_with("actions/runs/123/jobs")
            self.assertEqual(result["jobs"][0]["steps"][0]["name"], "Run tests")
            with self.assertRaises(WorkerError):
                _execute_tool("get_ci_run_jobs", {"run_id": True}, root, task, _validate_patch)

    def test_reviewer_retries_once_when_first_response_is_malformed(self):
        task = sample_task()
        malformed = {"model": "critic-model", "choices": [{"finish_reason": "stop",
            "message": {"content": "I approve this patch, but here is no JSON."}}]}
        valid = {"model": "critic-model", "choices": [{"finish_reason": "stop",
            "message": {"content": json.dumps({"verdict": "approve", "findings": [],
                                                "summary": "Reviewed successfully."})}}]}
        with patch.dict("os.environ", {"MOMO_AGENT_REVIEW_MODEL": "critic-model"}):
            with patch("intelligence.autonomy.agent_runtime._request_json",
                       side_effect=[malformed, valid]) as request:
                result = review_patch(task, sample_patch(), "builder-model", "fake-key",
                                      "https://example.invalid")
        self.assertTrue(result["approved"])
        self.assertEqual(result["served_model"], "critic-model")
        self.assertEqual(request.call_count, 2)
        self.assertIn("Return ONLY one valid JSON object",
                      request.call_args.args[2]["messages"][-1]["content"])

    def test_reviewer_fails_closed_after_two_malformed_responses(self):
        task = sample_task()
        malformed = {"model": "critic-model", "choices": [{"finish_reason": "length",
            "message": {"content": "not valid JSON"}}]}
        with patch.dict("os.environ", {"MOMO_AGENT_REVIEW_MODEL": "critic-model"}):
            with patch("intelligence.autonomy.agent_runtime._request_json",
                       side_effect=[malformed, malformed]) as request:
                with self.assertRaisesRegex(WorkerError, "after one retry"):
                    review_patch(task, sample_patch(), "builder-model", "fake-key",
                                 "https://example.invalid")
        self.assertEqual(request.call_count, 2)

    def test_reviewer_rejection_is_not_retried_or_approved(self):
        task = sample_task()
        rejected = {"model": "critic-model", "choices": [{"message": {
            "content": json.dumps({"verdict": "reject", "findings": ["unsafe change"],
                                   "summary": "Rejected."})}}]}
        with patch.dict("os.environ", {"MOMO_AGENT_REVIEW_MODEL": "critic-model"}):
            with patch("intelligence.autonomy.agent_runtime._request_json",
                       return_value=rejected) as request:
                with self.assertRaisesRegex(WorkerError, "Independent review rejected"):
                    review_patch(task, sample_patch(), "builder-model", "fake-key",
                                 "https://example.invalid")
        request.assert_called_once()

    def test_evaluation_dataset_and_weighted_score_are_deterministic(self):
        from intelligence.autonomy.evaluation import load_cases, score_run

        cases = load_cases()
        self.assertGreaterEqual(len(cases), 6)
        self.assertIn("prompt-injection", {case["id"] for case in cases})
        score = score_run(
            ["read_repo_file", "validate_patch"],
            ["read_repo_file", "validate_patch"],
            True, True, True, 0,
        )
        self.assertEqual(score["score"], 100)
        failed = score_run(["read_repo_file", "validate_patch"], ["read_repo_file"], False, False, False, 2)
        self.assertLess(failed["score"], 50)


if __name__ == "__main__":
    unittest.main()
