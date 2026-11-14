"""MOMO CELL: bounded, read-only self-maintenance supervisor.

The first release detects repository health issues and emits repair proposals.
It deliberately cannot mutate source files or bypass the MOMO execution gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import ast
import json
from pathlib import Path
import time
from typing import Callable, Iterable


@dataclass(frozen=True)
class Finding:
    cell: str
    code: str
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class RepairProposal:
    finding_code: str
    path: str
    action: str
    requires_approval: bool = True


@dataclass(frozen=True)
class ScanReport:
    version: int
    scanned_files: int
    findings: tuple[Finding, ...]
    proposals: tuple[RepairProposal, ...]
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "scanned_files": self.scanned_files,
            "findings": [asdict(item) for item in self.findings],
            "proposals": [asdict(item) for item in self.proposals],
            "duration_ms": self.duration_ms,
            "mutation_performed": False,
        }


Checker = Callable[[Path, str, bytes], Iterable[Finding]]


class CellRegistry:
    """Registry of bounded specialist cells; no dynamic code loading."""

    def __init__(self) -> None:
        self._checkers: dict[str, Checker] = {}

    def register(self, name: str, checker: Checker) -> None:
        if not name or name in self._checkers:
            raise ValueError("cell name must be non-empty and unique")
        self._checkers[name] = checker

    def run(self, root: Path, relative: str, payload: bytes) -> list[Finding]:
        findings: list[Finding] = []
        for name, checker in tuple(self._checkers.items()):
            findings.extend(checker(root, relative, payload))
        return findings

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._checkers))


def _python_cell(_root: Path, relative: str, payload: bytes) -> Iterable[Finding]:
    if not relative.endswith(".py"):
        return ()
    try:
        ast.parse(payload.decode("utf-8"), filename=relative)
    except (SyntaxError, UnicodeDecodeError) as exc:
        return (Finding("builder", "PYTHON_SYNTAX", "error", relative, str(exc)),)
    return ()


def _json_cell(_root: Path, relative: str, payload: bytes) -> Iterable[Finding]:
    if not relative.endswith(".json"):
        return ()
    try:
        json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return (Finding("contract", "INVALID_JSON", "error", relative, str(exc)),)
    return ()


def _required_docs_cell(root: Path, _relative: str, _payload: bytes) -> Iterable[Finding]:
    required = ("README.md", "docs/ARCHITECTURE.md", "docs/SECURITY.md")
    return tuple(
        Finding("guardian", "REQUIRED_FILE_MISSING", "error", item, "Required project contract is missing.")
        for item in required
        if not (root / item).is_file()
    )


def default_registry() -> CellRegistry:
    registry = CellRegistry()
    registry.register("builder", _python_cell)
    registry.register("contract", _json_cell)
    registry.register("guardian", _required_docs_cell)
    return registry


class MomoCell:
    """Read-only health scan that converts findings into gated repair proposals."""

    EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}
    MAX_FILES = 5000
    MAX_FILE_BYTES = 2 * 1024 * 1024

    def __init__(self, registry: CellRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def scan(self, root: str | Path) -> ScanReport:
        started = time.monotonic()
        base = Path(root).resolve(strict=True)
        if not base.is_dir():
            raise ValueError("scan root must be a directory")
        findings: list[Finding] = []
        count = 0
        for path in sorted(base.rglob("*")):
            if any(part in self.EXCLUDED for part in path.relative_to(base).parts):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            count += 1
            if count > self.MAX_FILES:
                findings.append(Finding("guardian", "SCAN_LIMIT", "warning", ".", "File limit reached; scan was bounded."))
                break
            try:
                if path.stat().st_size > self.MAX_FILE_BYTES:
                    continue
                payload = path.read_bytes()
            except OSError as exc:
                findings.append(Finding("guardian", "READ_FAILED", "warning", str(path.relative_to(base)), str(exc)))
                continue
            relative = path.relative_to(base).as_posix()
            findings.extend(self.registry.run(base, relative, payload))

        # Root-level invariants run once, independently of whether files were found.
        findings.extend(self.registry.run(base, "__momo_root_scan__.txt", b""))
        proposals = tuple(
            RepairProposal(
                finding_code=item.code,
                path=item.path,
                action="create_reviewed_repair_patch",
                requires_approval=True,
            )
            for item in findings
            if item.severity in {"error", "warning"}
        )
        return ScanReport(
            version=1,
            scanned_files=count,
            findings=tuple(findings),
            proposals=proposals,
            duration_ms=int((time.monotonic() - started) * 1000),
        )


def write_report(report: ScanReport, destination: str | Path) -> None:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
