# Task Coordinator

**Status:** Initial policy/scheduling layer; not a tool executor or complete runtime scheduler.

## Implemented
- Validates plans against registered agent roles, domains, capabilities, risk ceilings, dependency graph and delegation budget.
- Atomically persists task creation, the accepted canonical plan, every plan-step execution record and initial lifecycle events in one SQLite transaction.
- Exposes per-step execution records and append-only execution events through the coordinator.
- Recovers in-flight step records to `needs_review` through an explicit restart-recovery method; no interrupted step is replayed automatically.
- Persists unique plan-bound idempotency keys and bounded retry policy metadata; automatic retries remain restricted to R0/R1 read-only steps.
- Reloads the accepted plan after restart and verifies its SHA-256 digest before use.
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
- Durable dependency completion records and outcome reconciliation for `needs_review` steps.
- Boot/service-supervisor integration that invokes restart recovery exactly once per confirmed service restart.
- Idempotency keys for side-effecting tools.
- Deadlines, bounded retries, backoff, concurrency quotas and resource budgets.
- Cancellation propagation to running adapters.
- Independent result verification and outcome evidence.
- IPC authentication and platform-native permission enforcement.

These are separate milestones. The coordinator must not be described as an autonomous execution engine until they are implemented and tested.
