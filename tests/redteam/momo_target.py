"""Private HTTP adapter around the real MOMO CELL host-side functions.

This is a test-only adapter, not a production MOMO API. It imports the actual
checked-out repository modules from a read-only bind mount and exposes their
validation/tool functions to ARTEX over an internal-only Docker network.
"""
from __future__ import annotations

import json
import os
import subprocess
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(os.environ.get("MOMO_ROOT", "/workspace")).resolve()
LABEL = os.environ.get("TARGET_LABEL", "unknown")
PORT = int(os.environ.get("PORT", "8080"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("PYTHONPYCACHEPREFIX", "/tmp/pycache")

if not (ROOT / "intelligence" / "autonomy" / "agent_runtime.py").is_file():
    raise SystemExit(f"MOMO source tree not found at {ROOT}")

from intelligence.autonomy import policy
from intelligence.autonomy import agent_runtime
from intelligence.autonomy import runner
from intelligence.autonomy.task_assignment import parse_task_issue, validate_task_response


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "MOMO-HostTool-TestAdapter/1.0"

    def log_message(self, fmt, *args):
        print(f"{LABEL} " + (fmt % args), flush=True)

    def send_json(self, status: int, value):
        body = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 2 or length > 100_000:
            raise ValueError("request body must be between 2 and 100000 bytes")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            return self.send_json(200, {"ok": True, "label": LABEL, "ref": os.environ.get("TARGET_REF", "")})
        if parsed.path == "/":
            return self.send_json(200, {
                "service": "MOMO CELL red-team adapter",
                "label": LABEL,
                "warning": "test-only adapter; the imported functions are the real MOMO source modules",
                "routes": [
                    "GET /v1/meta", "GET /v1/manifest", "GET /v1/policy/allowed?path=...",
                    "POST /v1/tools/execute", "POST /v1/task/parse",
                    "POST /v1/task/response/validate", "POST /v1/patch/validate",
                ],
            })
        if parsed.path == "/v1/meta":
            return self.send_json(200, {
                "label": LABEL,
                "ref": os.environ.get("TARGET_REF", ""),
                "repo_root": str(ROOT),
                "source_is_read_only": True,
                "tool_names": [item["function"]["name"] for item in agent_runtime.TOOLS],
                "default_one_file_tools": [
                    item["function"]["name"]
                    for item in agent_runtime._select_tools({"files_in_scope": ["tests/test_momo_task_assignment.py"]})
                ],
                "policy_allowed_prefixes": list(policy.ALLOWED_PREFIXES),
                "note": "This adapter invokes real MOMO functions; it is not a production network API.",
            })
        if parsed.path == "/v1/manifest":
            tracked = agent_runtime._tracked(ROOT)
            allowed = [p for p in tracked if policy._allowed(p)]
            return self.send_json(200, {
                "tracked_files": len(tracked),
                "policy_readable_files": len(allowed),
                "policy_readable_preview": allowed[:120],
            })
        if parsed.path == "/v1/policy/allowed":
            path = parse_qs(parsed.query).get("path", [""])[0]
            return self.send_json(200, {"path": path, "allowed": policy._allowed(path)})
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        try:
            data = self.read_body()
            path = urlparse(self.path).path
            if path == "/v1/tools/execute":
                name = data.get("name")
                args = data.get("arguments", {})
                task = data.get("task", {
                    "task_id": 76,
                    "title": "Red-team narrow-scope adapter task",
                    "files_in_scope": ["tests/test_momo_task_assignment.py"],
                })
                if not isinstance(task, dict) or not isinstance(task.get("files_in_scope"), list):
                    return self.send_json(400, {"error": "task must include files_in_scope"})
                result = agent_runtime._execute_tool(
                    name, args, ROOT, task, runner._validate_patch
                )
                return self.send_json(200, {"ok": True, "label": LABEL, "result": result})
            if path == "/v1/task/parse":
                parsed = parse_task_issue(data.get("issue"))
                return self.send_json(200, {"ok": True, "task": parsed})
            if path == "/v1/task/response/validate":
                task = data.get("task")
                document = data.get("document")
                if not isinstance(task, dict):
                    return self.send_json(400, {"error": "task must be an object"})
                result = validate_task_response(document, task)
                return self.send_json(200, {"ok": True, "document": result})
            if path == "/v1/patch/validate":
                patch = data.get("patch")
                task = data.get("task", {"files_in_scope": ["tests/test_momo_task_assignment.py"]})
                if not isinstance(task, dict) or not isinstance(task.get("files_in_scope"), list):
                    return self.send_json(400, {"error": "task must include files_in_scope"})
                runner._validate_patch(patch, ROOT, set(task["files_in_scope"]))
                return self.send_json(200, {
                    "ok": True,
                    "label": LABEL,
                    "files_in_scope": sorted(set(task["files_in_scope"])),
                })
            return self.send_json(404, {"error": "not found"})
        except policy.WorkerError as exc:
            return self.send_json(400, {"ok": False, "error": str(exc), "label": LABEL})
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:300]})
        except Exception as exc:
            # Keep a bounded traceback for the red-team operator without exposing
            # environment variables or process credentials.
            return self.send_json(500, {
                "ok": False,
                "error": type(exc).__name__ + ": " + str(exc)[:300],
                "traceback": traceback.format_exc(limit=3)[-1600:],
            })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
