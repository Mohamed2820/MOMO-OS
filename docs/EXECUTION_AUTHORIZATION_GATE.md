# MOMO OS — Execution Authorization Gate

**Status:** Implemented as an in-process authorization gate on the `security/execution-approval-gate` branch. Repository CI passed on commit `47170e0132ae2142d0aa24eea10f26dc35590bc2` (167 unit tests). The change has not yet been rebuilt into x86_64 or AArch64 QEMU images. No tool executor is enabled.

## 1. Purpose and security boundary

The Execution Authorization Gate is the only supported in-process path for moving a plan-bound task into `executing` and a plan-bound step into `running`. It combines immutable-plan verification, task/step state checks, capability grants or explicit approval tokens, dependency checks, and durable state transitions.

**It authorizes a state transition; it does not execute a tool.** It is not an operating-system security boundary. Code running with the same Python privileges, or a process able to modify the task database, can bypass an in-process object-level guard. Native process isolation and service identity remain mandatory before any executor is enabled.

## 2. Implemented components

| Component | Responsibility |
|---|---|
| `intelligence/runtime/approval_store.py` | Issues and consumes one-time approval tokens |
| `intelligence/runtime/execution_gate.py` | Central authorization point for task and step start |
| `intelligence/runtime/task_coordinator.py` | Validates and persists the canonical plan and step dependencies |
| `intelligence/execution/step_journal.py` | Persists step state and tamper-evident event history |
| `intelligence/runtime/task_store.py` | Persists task lifecycle and blocks direct plan-bound execution transitions |
| `board/momo/rootfs-overlay/usr/lib/momo/intelligence/` | Buildroot runtime mirror |
| `tests/test_execution_gate.py` | Authorization, bypass, replay, expiry, concurrency and rollback regression tests |

## 3. Authorization flow

1. The coordinator validates the proposed plan against registered roles, domains, capabilities, risk ceilings and dependency rules.
2. It persists a canonical plan representation and SHA-256 digest with the task and all step records.
3. A task may enter `executing` only through `ExecutionGate.start_task_execution`. R3/R4 tasks require a task-bound approval token.
4. A step may enter `running` only through `ExecutionGate.start_step`.
5. The gate revalidates the task/plan association, task state, step membership, step risk, durable readiness and every dependency's `succeeded` state.
6. R0–R2 steps require a matching scoped capability grant. R3–R4 steps require a one-time approval token bound to the task, step, action/domain, resource, risk, plan digest and arguments digest.
7. The gate consumes a high-risk token and writes the step-start transition in one SQLite `BEGIN IMMEDIATE` transaction. If the start fails, token consumption rolls back.
8. The journal records the running attempt. The system still has no executor to perform the external operation or independently verify its result.

## 4. Approval token contract

- Tokens are generated from cryptographically secure random bytes and returned once to the issuing caller.
- Only the SHA-256 token hash is stored in SQLite; the raw token is not persisted.
- The maximum token lifetime is 15 minutes; the caller cannot provide a per-call clock.
- A token is single-use. Consumption checks token existence, exact binding, expiry and prior consumption.
- Binding mismatch does not consume the token.
- SQLite write locking and conditional consumption ensure concurrent consumers cannot both win.
- A failed step-start transaction rolls back token consumption.
- A plain `Approval(approved=True)` object is not an issued token and is refused.

### Critical limitations that remain open

1. **Approver identity is not authenticated yet.** The current API requires a non-empty `approver` string, but it does not prove that the string belongs to the signed-in human or a trusted approval UI. Until an authenticated identity/session integration exists, the stored approver label is audit metadata, not proof of human consent.
2. **The step arguments digest is caller-supplied.** The future executor must canonicalize the actual typed operation and arguments itself, compute the digest, and compare it before dispatch. The current gate cannot prove that an external operation matches a caller-declared digest because no executor exists.
3. **R0–R2 grants use a separate permission database.** Grant consumption can occur before the task-database step-start transaction. This is fail-closed with respect to execution (a grant may be spent without a start, but a start is not allowed without a grant), but it is not an atomic cross-database transaction. A unified transactional store or explicit reservation/commit protocol is required.
4. **The in-process authority marker is not a process boundary.** A hostile module with the same interpreter privileges is not contained by `GATE_AUTHORITY`.
5. **The gate is not a scheduler or executor.** No process launch, network call, filesystem mutation, app action or other tool side effect is performed by this code.

## 5. Required invariants

- No plan-bound task or step may enter an executing state through the public TaskStore or journal bypass APIs.
- The accepted persisted plan is immutable for the lifetime of the task.
- Plan digest, step ID, action/domain, resource and risk must match the approved operation.
- Dependencies are complete only when their durable journal state is `succeeded`.
- Corrupt event history blocks reads, new events and dependency scheduling.
- Restart-interrupted steps are quarantined as `needs_review`; they are never replayed automatically.
- R2–R4 ambiguous outcomes require reconciliation; no automatic retry.
- Approval tokens are single-use, short-lived and fail closed.
- Tool dispatch remains disabled until native OS enforcement and executor identity are independently verified.

## 6. Verification evidence

The PR #45 CI run completed successfully. Its repository-validation job ran 167 unit tests and reported `OK`. Tests cover direct transition bypasses, CLI bypass attempts, missing grants, missing approvals, task/step/plan/argument mismatch, expiry, token reuse, concurrent consumption, rollback after injected start failure, low-risk and high-risk authorized state transitions, and rootfs overlay parity.

This CI result validates the Python authorization/state layer. It does not validate an x86_64/AArch64 image containing this exact commit, a real human approval identity, an external executor, or kernel-level isolation.

## 7. Next engineering gates

### Gate A — Image integration
- Build x86_64 and AArch64 images from the commit containing this gate.
- Boot each under its matching QEMU machine.
- Verify `MOMO OS READY`, task recovery, permission initialization and IPC status response.
- Inspect artifacts, boot logs, commit provenance and hashes.

### Gate B — Authenticated approval identity
- Define the user/session principal source for each platform.
- Make approval issuance callable only by the trusted approval service.
- Bind approval records to an authenticated principal ID and session/audit event.
- Add revocation, logout, stale-session and impersonation tests.

### Gate C — Executor protocol, still non-executing
- Define typed operation IDs and versioned argument/result schemas.
- Have the executor recompute canonical argument digests.
- Define executor principal identity, deadlines, cancellation acknowledgement, idempotency propagation and outcome evidence.
- Reject arbitrary shell, arbitrary paths and model-selected executable names.

### Gate D — Native sandbox
- Implement a separate unprivileged executor identity and per-task isolation.
- Enforce namespaces, cgroups, strict seccomp policy and an LSM policy.
- Apply read-only filesystem mounts and narrowly scoped task workspaces.
- Add adversarial tests before enabling any side effect.

### Gate E — Platform parity
- Implement the Android path separately using Binder/AIDL, SELinux, AppOps, signature permissions and Android Keystore.
- Keep Android and Linux enforcement mapped to the same MOMO capability contracts, but do not pretend their enforcement mechanisms are interchangeable.

## 8. Explicit non-goals of this milestone

This milestone does not claim autonomous task execution, secure human identity, a complete sandbox, Android integration, physical-device support, or production release readiness.
