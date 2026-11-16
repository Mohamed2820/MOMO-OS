"""Shared immutable Stage 1 worker safety policy."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

BLOCKED_PREFIXES = (
    ".github/", ".git/", "security/", "intelligence/autonomy/",
    "board/momo/kernel", "board/momo/rootfs-overlay/etc/",
    "docs/decisions/", "docs/contracts/",
)
BLOCKED_PATHS = {
    "docs/ROADMAP.md", "docs/ARCHITECTURE.md", "docs/MOMO_CELL.md",
    "docs/MASTER_EXECUTION_PLAN.md", "docs/SRS.md",
    "docs/REQUIREMENTS_TRACEABILITY.md",
}
BLOCKED_NAMES = {
    "SECURITY.md", "TOOL_AND_PERMISSION_MODEL.md", "AGENT_METHODOLOGY.md",
    "MASTER_EXECUTION_PLAN.md", "requirements.txt", "requirements-dev.txt",
    "SECURITY_POLICY.md", "EXECUTION_GATE.md", "execution_gate.py",
    "typed_executor.py", "approval_store.py", "task_coordinator.py",
    "permission_broker.py", "capability_broker.py",
}
ALLOWED_PREFIXES = (
    "intelligence/", "platform_adapters/", "tests/", "docs/",
    "board/momo/rootfs-overlay/usr/lib/momo/",
    "board/momo/rootfs-overlay/usr/bin/",
)


class WorkerError(RuntimeError):
    """Raised when the worker cannot safely produce or apply a patch."""


def _run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], check=check, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30,
    )


def _allowed(path: str) -> bool:
    if not isinstance(path, str) or not path or path != path.strip():
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        return False
    if "\\" in path or path.startswith("/") or "//" in path:
        return False
    segments = path.split("/")
    if any(part in {"", ".", ".."} for part in segments):
        return False
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", path):
        return False
    pure = PurePosixPath(path)
    if any(path.startswith(prefix) for prefix in BLOCKED_PREFIXES):
        return False
    if path in BLOCKED_PATHS:
        return False
    if pure.name in BLOCKED_NAMES or pure.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        return False
    return path.startswith(ALLOWED_PREFIXES)


from intelligence.autonomy.task_assignment import parse_task_issue, validate_task_response
