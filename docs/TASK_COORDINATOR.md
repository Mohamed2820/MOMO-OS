# Task Coordinator

**Status:** Implemented policy, immutable-plan persistence, step-journal integration and dependency scheduling. Not a tool executor or complete runtime scheduler.

## Implemented

- Validates plans against registered agent roles, domains, capabilities, risk ceilings, dependency graph and delegation budget.
- Atomically persists task creation, accepted canonical plan and initial lifecycle events.
- Reloads the accepted plan after restart and verifies its SHA-256 digest before use.
- Atomically registers accepted plan steps in the durable Step Execution Journal.
- Binds step records and idempotency keys to task/step identity and the accepted plan.
- Persists step state, attempt count, retry budget, cancellation request, result digest and transition events.
- Protects step event history with a SHA-256 hash chain and SQLite update/delete guards; integrity failures fail closed.
- Derives dependency readiness from durable succeeded step records rather than caller-supplied completion claims.
- Quarantines restart-interrupted steps and ambiguous side-effecting outcomes as `needs_review`; it never automatically replays them.
- Requests per-step authorization through the persistent permission broker using exact subject/action/task-resource/risk scope.
- Requires matching explicit per-action approval for R3/R4 operations according to broker policy.
- Source runtime modules are mirrored into the Buildroot root filesystem overlay and covered by parity tests.

## Security boundary

The coordinator never dispatches a tool, calls a model, creates a grant, or approves an action. A successful authorization decision is not execution permission at the Linux kernel boundary; native service identity, IPC authentication, OS sandboxing and platform permissions are still mandatory.

## Not yet implemented

- Tool execution adapters and sandboxed process/container execution.
- Authenticated IPC and executor identity.
- Linux namespaces, seccomp and LSM policy enforcement; Android Binder/AIDL, SELinux and AppOps enforcement.
- Complete deadline scheduling, backoff, concurrency quotas and resource budgets.
- Cancellation propagation to a real running executor.
- Independent result verification, external outcome reconciliation and safe resolution of `needs_review`.
- Production-grade service supervision and cross-service recovery.

The coordinator must not be described as an autonomous execution engine until these separate milestones are implemented and tested. The integrated revision's fresh QEMU image acceptance is still pending.
