# MOMO CELL — Autonomous Maintenance Core

**Status:** Core v1 is installed in the MOMO root filesystem and runs a bounded, read-only system health scan during boot; the repository health cycle also runs in CI. Automatic source mutation and autonomous merge are deliberately not enabled.

## Purpose

MOMO CELL is the self-maintenance subsystem of MOMO OS. It is designed as a parent cell with registered specialist cells. Specialist registration is explicit and allowlisted; cells do not execute arbitrary downloaded code or spawn uncontrolled copies of themselves.

## First active capabilities

- Guardian cell: checks required project contracts and bounded repository traversal.
- Builder cell: parses Python source with the Python AST parser.
- Contract cell: validates JSON files.
- Generates a machine-readable health report and repair proposals.
- Runs in repository validation and on a scheduled GitHub Actions scan.

## Repair lifecycle

1. Scan a bounded repository snapshot.
2. Produce findings with stable codes and file paths.
3. Convert findings into repair proposals.
4. A future repair worker must create a dedicated branch and a patch limited by policy.
5. Run tests, security checks, and architecture-specific build/boot acceptance.
6. Open a Pull Request with evidence.
7. Human review is required before merging protected or security-sensitive changes.

## Non-negotiable controls

- No direct writes to source files in v1.
- No shell, arbitrary process execution, or request-supplied Python handlers.
- No self-granted permissions, credentials, or policy changes.
- No modification of security/, execution-gate code, kernel security policy, signing material, or workflow permissions without independent review.
- All future write operations must pass the task planner, authenticated principal checks, and ExecutionGate using a typed adapter.
- No automatic merge in the initial release.
- Scan limits: 5,000 files and 2 MiB per file; symlinks and generated/vendor directories are skipped.

## Growth model

"Cell division" means enabling another explicitly registered specialist module with a declared scope, tests, resource budget, and policy—not unbounded process replication. A child cell inherits the parent's restrictions and cannot widen them. New cells are inert until their tests and registration review pass.

## Current limitations

This release detects a small set of deterministic repository issues. It does not yet infer arbitrary defects, synthesize trustworthy code repairs, execute repair patches, operate on live devices, or autonomously merge GitHub changes. Those require a model-backed repair planner, isolated patch worker, authenticated GitHub identity, scoped write adapter, and adversarial security tests.

## Interface

Run locally or in CI:

    python3 -m intelligence.cell.cli --root . --output momo-cell-report.json

Exit code is non-zero when an error-level finding is present.
