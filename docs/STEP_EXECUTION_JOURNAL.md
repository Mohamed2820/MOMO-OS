# MOMO OS — Durable Step Execution Journal

**Status:** Implemented, integrated with TaskCoordinator, mirrored into the Buildroot rootfs overlay, and covered by repository tests. The integrated revision is awaiting its fresh QEMU image acceptance run. It is not a tool executor or OS sandbox.

## Purpose

The Step Execution Journal records each immutable plan step independently from the parent task lifecycle. Restart behavior is conservative: an operation found in progress after a service restart is quarantined for review and is never replayed automatically.

## Persistence model

The journal shares the SQLite database initialized by `TaskStore`:

- `task_step_executions`: one durable record per `(task_id, step_id)`, including risk, state, attempt count, retry budget, stable idempotency key, cancellation flag, error summary and optional result SHA-256.
- `task_step_events`: append-only transition and cancellation-request events, protected by a SHA-256 event chain and SQLite update/delete guards.

Foreign keys bind execution records to existing tasks. Composite and unique constraints prevent duplicate task steps and idempotency-key reuse.

## Integrated lifecycle

When TaskCoordinator accepts a plan, task, canonical immutable plan and initial step execution records are persisted atomically. The coordinator validates the persisted plan digest before use. Step registration is bound to the accepted plan; the Buildroot overlay contains the same runtime module as the source tree.

The boot recovery path invokes `momo-task recover` before the readiness marker. Interrupted `running` steps become `needs_review`; recovery is idempotent and does not replay work.

## State model

```text
READY ──start──> RUNNING ──success──> SUCCEEDED
                    │
                    ├──R0/R1 failure──> FAILED ──explicit bounded retry──> RUNNING
                    ├──R2-R4 failure──> NEEDS_REVIEW
                    ├──restart recovery──> NEEDS_REVIEW
                    └──cancel request──> RUNNING(cancel_requested)
                                              └──executor confirms no side effect──> CANCELLED
READY ──cancel──> CANCELLED
```

Dependency readiness is derived from durable succeeded step records; caller-supplied completion claims are not trusted. Journal integrity is verified before relevant reads, appends and scheduling; tampering fails closed.

## Retry, side effects and cancellation

- Retry budgets are limited to R0/R1 read-only work and must be explicitly requested within the registered budget.
- R2-R4 operations do not receive automatic retry budgets.
- Ambiguous outcomes and restart-interrupted work become `needs_review`.
- A persisted idempotency key is unique and plan-bound. Persistence alone does not make an external system idempotent.
- Cancelling a running step records a request; it does not claim that execution stopped. The future executor must confirm that no side effect occurred before the state can become `cancelled`.

## Security boundary and remaining limitations

This component does not spawn processes, invoke tools, call models, grant capabilities, authenticate an executor, or enforce Linux namespaces, seccomp, LSM, Android SELinux or AppOps. It does not independently determine whether an external side effect happened, nor does it provide deadline scheduling, backoff, concurrency quotas, outcome reconciliation or a complete tool sandbox.

A future execution adapter must verify the immutable plan, obtain fresh permission authorization, enforce native OS isolation, pass idempotency keys downstream and produce independently verifiable outcome evidence. The journal and its caller are not a security boundary.

## Source, overlay and tests

- Source: `intelligence/execution/step_journal.py`.
- Target overlay: `board/momo/rootfs-overlay/usr/lib/momo/intelligence/execution/step_journal.py`.
- Tests: `tests/test_step_execution_journal.py`, `tests/test_task_coordinator.py`, and overlay parity tests.
- Integration: TaskCoordinator atomically registers accepted plan steps; `momo-task recover` is invoked by the first-boot readiness path.
- Evidence: PR #26 is merged into `bootable/x86_64-buildroot-mvp-v2` (not yet `main`); its repository validation reported 111 passing unit tests. A new QEMU image run for integrated revision `1cb65956c7e1ab0b2d0c1bb6f0f4f8850a1ede25` is [run #43446234529](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43446234529); its latest observed state is still in progress, with no artifact yet.

**Evidence boundary:** repository tests and source/overlay parity do not establish that the integrated revision has booted. QEMU acceptance for this revision remains pending; physical hardware, Android/AOSP and native OS sandboxing remain unvalidated.
