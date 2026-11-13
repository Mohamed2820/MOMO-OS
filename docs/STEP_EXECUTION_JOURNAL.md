# MOMO OS — Durable Step Execution Journal

**Status:** Integrated with TaskCoordinator and mirrored into the Buildroot rootfs overlay; repository CI-tested, but not yet validated in the target image and not connected to a tool executor.

## Purpose

The Step Execution Journal records the lifecycle of individual plan steps independently from the parent task lifecycle. It is designed to make restart behavior conservative: a step that was running when the system stopped is not assumed to have failed safely and is never replayed automatically.

## Persistence model

The journal shares the SQLite database initialized by `TaskStore` and creates two tables:

- `task_step_executions`: one durable record per `(task_id, step_id)`, including risk, state, attempt count, retry budget, stable idempotency key, cancellation flag, error summary and optional result SHA-256.
- `task_step_events`: append-only state-transition and cancellation-request events.

Foreign keys bind every execution record to an existing task. The composite primary key prevents duplicate records for the same task step, and the unique idempotency-key constraint prevents reusing a key for another step.

## State model

```text
READY ──start──> RUNNING ──success──> SUCCEEDED
                    │
                    ├──R0/R1 failure──> FAILED ──explicit bounded retry──> RUNNING
                    │
                    ├──R2-R4 failure──> NEEDS_REVIEW
                    │
                    ├──restart recovery──> NEEDS_REVIEW
                    │
                    └──cancel request──> RUNNING(cancel_requested)
                                              │
                                              └──executor confirms no side effect──> CANCELLED

READY ──cancel──> CANCELLED
```

`NEEDS_REVIEW`, `SUCCEEDED` and `CANCELLED` cannot be started again through this component. Reconciliation is a separate future responsibility.

## Retry and side-effect policy

- Automatic retry budgets are accepted only for R0/R1 read-only work.
- A retry must be explicitly requested and must remain within the registered retry budget.
- R2/R3/R4 steps cannot receive an automatic retry budget.
- A failed R2/R3/R4 step becomes `needs_review`, because a transport or process error does not prove that the external side effect did not occur.
- A process restart converts every `running` step to `needs_review`, regardless of risk. Recovery never replays an in-flight operation.
- An idempotency key is persisted and unique. A future executor must pass this key to a downstream service when that service supports idempotency; persistence alone does not make an external operation idempotent.

## Cancellation semantics

Cancelling a step in `ready` state moves it directly to `cancelled`. Cancelling a running step records a cancellation request but does not claim that execution has stopped. The executor must acknowledge cancellation and confirm that no side effect occurred before the journal marks it `cancelled`. If the executor cannot establish that fact, the step must remain unresolved and be reconciled.

## Security boundary and limitations

This module is a durable state component only. It does not:

- Spawn a process, invoke a tool, call a model or execute a plan.
- Grant capabilities or approve an operation.
- Authenticate an executor or enforce Linux namespaces, seccomp, LSM/SELinux or Android permissions.
- Determine whether an external side effect actually happened.
- Schedule deadlines, backoff timers, concurrency quotas or resource budgets.
- Reconcile `needs_review` records or safely retry side-effecting work.

The future execution adapter must validate the immutable task plan, obtain a fresh Permission Broker decision, enforce native OS isolation, pass idempotency keys downstream, and produce independently verifiable outcome evidence. The journal's caller is not itself a security boundary.

## Test coverage

The repository validation suite currently covers registration, durable state, result digest validation, explicit and bounded R0/R1 retries, rejection of side-effect retry budgets, side-effect failure quarantine, restart recovery, recovery idempotence, queued cancellation, executor-confirmed running cancellation, duplicate step/idempotency-key rejection and unknown-step handling.

## Integration status

- Source module: `intelligence/execution/step_journal.py`.
- Tests: `tests/test_step_execution_journal.py`.
- CI: repository validation workflow, full unittest discovery.
- TaskCoordinator creates all plan-step records in the same SQLite transaction as the task, immutable plan digest and initial task events.
- TaskCoordinator exposes step-record/event reads and an explicit interrupted-step recovery entry point.
- The journal and coordinator are mirrored into the Buildroot root filesystem overlay, with CI source/overlay parity checks.
- `momo-task recover` exposes an explicit interrupted-step quarantine command.
- `momoctl boot-check` invokes recovery before reporting `MOMO OS READY`; repeated recovery calls are idempotent.
- The image has not yet been rebuilt with this integration; QEMU and physical hardware validation remain pending.

The next integration milestone is to bind each accepted plan step to this journal atomically, then add an executor interface that can only start after plan-integrity and permission checks. OS-level sandboxing remains a separate mandatory gate.

## Durable dependency readiness

TaskCoordinator obtains step states from `StepExecutionJournal.list_steps(task_id)`. It validates that the journal contains exactly the step IDs and risk levels from the immutable accepted plan. A dependency counts as complete only when its journal state is `succeeded`; caller-supplied completion sets are no longer accepted. The coordinator returns a step only if all dependencies succeeded and that step's own durable state is `ready`.

A `failed`, `running`, `cancelled` or `needs_review` step cannot unblock dependent work. This avoids treating an in-memory assertion or an ambiguous external outcome as proof of completion. Retry and reconciliation remain explicit separate operations.
