# Task Coordinator

**Status:** Initial policy/scheduling layer; not a tool executor or complete runtime scheduler.

## Implemented
- Validates plans against registered agent roles, domains, capabilities, risk ceilings, dependency graph and delegation budget.
- Persists task lifecycle events through the SQLite task journal.
- Stores canonical plan JSON and SHA-256 digest, binding the plan to its task and rejecting later plan substitution.
- Returns deterministic dependency-ready steps.
- Requests per-step authorization through the persistent permission broker using exact subject/action/task-resource/risk scope.
- Requires matching explicit per-action approval for R3/R4 operations according to broker policy.
- Included in the Buildroot root filesystem overlay and covered by repository tests.

## Security boundary
The coordinator never dispatches a tool, calls a model, creates a grant, approves an action, or treats a model-produced plan as authority. A successful authorization decision means only that a matching grant was consumed; the platform adapter must still enforce native OS permissions and sandboxing. Model-generated plans are untrusted input and must pass validation.

## Not yet implemented
- Tool execution adapters and sandboxed process/container execution.
- Atomic task + plan persistence across database failure boundaries.
- Complete lifecycle transitions for running, waiting, retrying, cancelling, failed and completed tasks.
- Durable dependency completion records and crash recovery/reconciliation.
- Idempotency keys for side-effecting tools.
- Deadlines, bounded retries, backoff, concurrency quotas and resource budgets.
- Cancellation propagation to running adapters.
- Independent result verification and outcome evidence.
- IPC authentication and platform-native permission enforcement.

These are separate milestones. The coordinator must not be described as an autonomous execution engine until they are implemented and tested.
