# MOMO OS — Durable Step Execution Journal

**Status:** Integrated with TaskCoordinator and mirrored into the Buildroot root filesystem overlay. Repository CI passed with 111 unit tests. The latest merged revision is awaiting its QEMU image rebuild; no tool executor is connected.

## Purpose

The Step Execution Journal records the lifecycle of individual plan steps independently from the parent task lifecycle. Restart behavior is deliberately conservative: a step that was running when the system stopped is not assumed to have failed safely and is never replayed automatically.

## Persistence model

The journal shares the SQLite database initialized by TaskStore and creates two tables:

- task_step_executions: one durable record per task and step, including risk, state, attempt count, retry budget, stable idempotency key, cancellation flag, error summary and optional result SHA-256.
- task_step_events: append-only state-transition and cancellation-request events.

Foreign keys bind every execution record to an existing task. The composite primary key prevents duplicate records for the same task step, and the unique idempotency-key constraint prevents reusing a key for another step.

## State model

READY -> RUNNING -> SUCCEEDED
                    -> FAILED (R0/R1 only; explicit bounded retry may be requested)
                    -> NEEDS_REVIEW (R2-R4 failure or restart interruption)
                    -> RUNNING with cancel_requested
                         -> CANCELLED only after executor confirms no side effect

READY -> CANCELLED

NEEDS_REVIEW, SUCCEEDED and CANCELLED cannot be started again through this component. Reconciliation is a separate responsibility.

## Retry and side-effect policy

- Retry budgets are accepted only for R0/R1 read-only work.
- A retry must be explicitly requested and remain within the registered retry budget.
- R2/R3/R4 steps cannot receive an automatic retry budget.
- A failed R2/R3/R4 step becomes needs_review, because a transport or process error does not prove that the external side effect did not occur.
- A process restart converts every running step to needs_review, regardless of risk. Recovery never replays an in-flight operation.
- An idempotency key is persisted, unique and bound to the accepted plan step. A future executor must pass it to a downstream service when supported; persistence alone does not make an external operation idempotent.

## Cancellation semantics

Cancelling a step in ready state moves it directly to cancelled. Cancelling a running step records a request but does not claim that execution has stopped. The executor must acknowledge cancellation and confirm that no side effect occurred before the journal marks it cancelled. If the executor cannot establish that fact, the step remains unresolved and must be reconciled.

## Security boundary and limitations

This module is a durable state component only. It does not:

- Spawn a process, invoke a tool, call a model or execute a plan.
- Grant capabilities or approve an operation.
- Authenticate an executor or enforce Linux namespaces, seccomp, LSM/SELinux or Android permissions.
- Determine whether an external side effect actually happened.
- Schedule deadlines, backoff timers, concurrency quotas or resource budgets.
- Reconcile needs_review records or safely retry side-effecting work.

The future execution adapter must validate the immutable task plan, obtain a fresh Permission Broker decision, enforce native OS isolation, pass idempotency keys downstream, and produce independently verifiable outcome evidence. The journal's caller is not itself a security boundary.

## Test coverage

Repository validation covers registration, durable state, result digest validation, explicit and bounded R0/R1 retries, rejection of side-effect retry budgets, side-effect failure quarantine, restart recovery, recovery idempotence, queued cancellation, executor-confirmed running cancellation, duplicate step/idempotency-key rejection, unknown-step handling, dependency blocking, event migration, hash-chain tampering and fail-closed reads/scheduling.

The integrated PR #26 validation completed successfully with 111 unit tests.

## Integration status

- Source module: intelligence/execution/step_journal.py.
- Tests: tests/test_step_execution_journal.py.
- TaskCoordinator creates all plan-step records in the same SQLite transaction as the task, immutable plan digest and initial task events.
- TaskCoordinator exposes step-record/event reads and an explicit interrupted-step recovery entry point.
- The journal and coordinator are mirrored into the Buildroot root filesystem overlay, with CI source/overlay parity checks.
- momo-task recover exposes an explicit interrupted-step quarantine command.
- momoctl boot-check invokes recovery before reporting MOMO OS READY; repeated recovery calls are idempotent.
- The base x86_64 image has booted successfully in QEMU. The latest merged revision containing coordinator integration is being rebuilt; its QEMU result is still pending.

## Durable dependency readiness

TaskCoordinator obtains step states from StepExecutionJournal.list_steps(task_id). It validates that the journal contains exactly the step IDs and risk levels from the immutable accepted plan. A dependency counts as complete only when its journal state is succeeded; caller-supplied completion sets are not accepted. The coordinator returns a step only if all dependencies succeeded and that step's own durable state is ready.

A failed, running, cancelled or needs_review step cannot unblock dependent work. Retry and reconciliation remain explicit separate operations.

## Event integrity

Each step's event stream is linked with a SHA-256 hash chain. New events include the previous event hash, and verify_event_chain checks the entire sequence. list_events verifies integrity before returning history. SQLite triggers reject ordinary UPDATE and DELETE statements. On initialization, legacy event tables are migrated by backfilling hashes before append-only triggers are installed.

This is tamper-evident, not a signed audit log. A privileged attacker able to rewrite the database and recompute hashes can forge a new chain. Stronger assurance requires protected storage permissions, a signing key held outside the database, and/or an external append-only audit anchor.

Before any new lifecycle event is appended, the existing chain is verified using the same SQLite transaction connection. If prior history is corrupt, the state transition fails and rolls back; the journal will not extend or normalize a corrupted event stream.

Step-state reads and task step listings verify the corresponding event chains. TaskCoordinator therefore cannot derive dependency readiness from a step whose audit history is corrupt. Corruption blocks both reads and scheduling; tests verify that state transitions also roll back when the chain fails verification.

## Next milestone

A narrow authenticated AF_UNIX status-only service now exists in the IPC workstream: it checks SO_PEERCRED before parsing, accepts only the configured root UID, and exposes no executor. Once the latest QEMU image passes, add a non-executing executor protocol and test its authorization, identity, idempotency, deadline and cancellation contracts. Keep privileged dispatch disabled until operation-specific authorization and native OS sandboxing are implemented.
