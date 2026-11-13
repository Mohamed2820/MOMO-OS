# Task Coordinator

**Status:** Integrated policy, durable-plan and dependency-readiness coordinator. It is not a tool executor or a complete runtime scheduler.

## Implemented

- Validates plans against registered agent roles, domains, capabilities, risk ceilings, dependency graph and delegation budget.
- Atomically persists task creation, the accepted canonical plan, every plan-step execution record and initial lifecycle events in one SQLite transaction.
- Reloads the accepted plan after restart and verifies its SHA-256 digest before use.
- Persists per-step execution state, attempts, cancellation requests, result digests and unique plan-bound idempotency keys.
- Persists append-only per-step lifecycle events with a SHA-256 hash chain, SQLite update/delete guards and legacy-row migration.
- Verifies event-chain integrity before appending events, reading step state and deriving dependency readiness; corrupted history fails closed.
- Derives dependency completion only from durable succeeded records. Caller-supplied completion claims are not accepted.
- Returns a step as ready only when its dependencies are durably successful and its own journal state is ready.
- Quarantines interrupted running steps as needs_review during recovery; no interrupted operation is automatically replayed.
- The current init-managed Linux boot path invokes momo-task recover before the readiness check; repeated recovery is idempotent.
- Stores bounded retry-policy metadata. Explicit retries are restricted to R0/R1 read-only steps.
- Requests per-step authorization through the persistent permission broker using exact subject/action/task-resource/risk scope.
- Requires matching explicit per-action approval for R3/R4 operations according to broker policy.
- Is mirrored into the Buildroot root filesystem overlay and covered by repository source/overlay parity tests.

## Security boundary

The coordinator never dispatches a tool, calls a model, creates a grant, approves an action, or treats a model-produced plan as authority. A successful authorization decision means only that a matching grant was consumed; it is not proof that a native OS boundary enforced the operation. Model-generated plans are untrusted input and must pass validation.

The event hash chain is tamper-evident against accidental or partial record modification. It is not a digital signature and does not resist a privileged attacker who can rewrite the database and recompute hashes. External anchoring, protected key custody and OS-enforced storage permissions remain required for stronger assurance.

## Not yet implemented

- A worker scheduler and actual execution adapter; no process or tool is dispatched.
- Fresh authorization bound atomically to dispatch, plus authenticated executor identity and replay-resistant IPC.
- Linux namespaces, seccomp/LSM policy and sandbox profiles; Android SELinux/AppOps/Binder enforcement.
- Downstream propagation and enforcement of idempotency keys by external services.
- Deadline enforcement, backoff scheduling, concurrency/fairness limits and resource budgets.
- Cancellation propagation to a running process and proof that cancellation caused no side effect.
- Independent result verification and reconciliation of needs_review outcomes.
- Supervisor semantics that prove recovery runs exactly once after each confirmed service restart.
- Signed or externally anchored audit evidence, protected key custody and retention/deletion controls.

These are separate milestones. The coordinator must not be described as an autonomous execution engine until they are implemented and tested.

## Validation status

The integrated coordinator, journal, Buildroot overlay and fail-closed dependency logic passed repository validation with 111 unit tests at PR #26. The merged revision is being rebuilt and must pass the latest QEMU image and readiness gate before image-level integration is claimed.

## Next milestone

After the current QEMU image passes, define and test a non-executing executor protocol: immutable plan binding, fresh authorization, OS principal identity, idempotency propagation, deadlines, cancellation acknowledgement and independent outcome evidence. Do not enable privileged tool dispatch until native OS isolation and authenticated IPC are in place.
