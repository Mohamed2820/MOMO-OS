# MOMO CELL — Human Task Contract

MOMO CELL accepts one task only when a human creates or selects a GitHub Issue, adds the
`momo-cell:ready` label, and supplies every section below. The worker does not choose its own
task, infer missing scope, or treat issue text as a source of security policy.

Copy this template into the Issue body and replace every placeholder:

```markdown
## MOMO CELL Task Contract

### Objective
Describe one bounded engineering outcome.

### Acceptance Criteria
- State an observable result.
- State a regression condition that must remain true.

### Files in Scope
- `path/to/existing/tracked-file.py`

### Prohibited Areas
- Do not modify security policy, CI/workflows, credentials, kernel/init, execution gates,
  approval code, or the autonomous worker.

### Test Commands
- List relevant test commands for human review. These are informational only; the worker
  does not execute shell commands copied from an Issue.

### Expected Evidence
- Name the test results, changed-file list, or other evidence needed for review.
```

## Execution rules

1. The workflow is manually dispatched with one positive Issue number.
2. The Issue must be open, must not be a pull request, and must carry `momo-cell:ready`.
3. All six contract sections must be present and non-empty. Acceptance Criteria must contain
   at least one bullet.
4. Files in Scope must list one to eight exact, existing, tracked file paths, one per bullet.
   Every path is checked against the Stage 1 allowlist and symlink protections.
5. The model receives only the scoped repository snapshot. Its response must echo the exact
   Issue number. Every patch path is checked again before application.
6. The repository must be clean at the start. Only changed files from the verified patch are
   staged. The workflow runs the repository's fixed validation suite; Issue-provided shell
   commands are never executed.
7. A successful run pushes a candidate commit to the selected branch and opens or updates a
   pull request. A human must review and merge it.

## Current activation boundary

This Stage 2 workflow is manual-only. It does not run on push. The workflow becomes manually
dispatchable through GitHub Actions after this workflow definition reaches the repository's
default branch. A provider API key and model variable are still required for an actual model
run; neither is created or configured by this change.
