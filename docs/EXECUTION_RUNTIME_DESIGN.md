# MOMO OS — Execution Runtime Engineering Design

**Status:** Design baseline for the next execution-runtime increment. The plan-bound task coordinator, durable step journal, approval gate and read-only Linux IPC status daemon exist in source. A general-purpose tool executor is intentionally not enabled.

## 1. Scope and safety boundary

This document specifies how MOMO may progress from durable task planning to bounded, verifiable operations. It does not authorize arbitrary command execution, root access for agents, or autonomous execution of destructive actions.

The execution path has four distinct responsibilities:

1. **Planning:** produce a validated immutable plan.
2. **Authorization:** establish that the current task, exact step, principal, capability, arguments and approval satisfy policy.
3. **Execution:** invoke one typed adapter operation inside its platform security boundary.
4. **Verification:** independently establish the resulting state and record evidence.

A successful authorization is not proof of execution. A process exit code or model statement is not proof that the requested external state changed.

## 2. Current implementation

| Component | Current behavior | Limitation |
|---|---|---|
| TaskCoordinator | Validates agent roles, capabilities, risk ceilings and dependencies; persists canonical plan and digest | Does not dispatch operations |
| StepExecutionJournal | Persists step state, attempts, idempotency key, cancellation and append-only event hash chain | Does not execute or reconcile external effects |
| ApprovalStore | Issues random, expiring, single-use tokens; task approvals use plan binding and step approvals now require strict JSON argument payloads whose digest is computed inside the store | Approver identity is still an asserted string, not independently authenticated identity |
| ExecutionGate | Public `start_step()` accepts raw JSON and derives the digest internally; `start_step_with_arguments()` returns deeply immutable parsed values with the durable start | In-process guard only; database owner can bypass it; no typed adapter dispatch is enabled |
| Linux IPC | Bounded AF_UNIX framing, SO_PEERCRED, status-only daemon | No operation dispatcher or privileged executor |
| Rootfs integration | Mirrors runtime modules and starts the read-only IPC daemon | Fresh QEMU validation of the integrated revision remains required |

The gate and journal must not be described as an OS sandbox, trusted execution environment, or complete agent security boundary.

## 3. Canonical execution state machine

Task lifecycle:

`received → classified → planned → awaiting_approval → executing → verifying → completed`

Alternative outcomes: `blocked`, `cancelled`, `failed`, `partially_completed`.

Step lifecycle:

`ready → running → succeeded`

Other valid transitions include:
- `ready → cancelled`
- `running → failed` only for read-only work with a known safe failure
- `running → needs_review` when a side-effecting result is ambiguous
- `running → cancelled` only after the executor confirms no side effect occurred
- `running → needs_review` after restart recovery

R2–R4 operations must never be blindly replayed after timeout, crash, connection loss or unknown outcome. A retry is a new authorized attempt after reconciliation, not an automatic repetition.

## 4. Required authorization binding

Before a step can start, the trusted gate must verify all of the following against canonical persisted state:

- Task ID and task lifecycle state.
- Immutable plan digest and exact step ID.
- Registered agent role and authenticated runtime principal.
- Operation ID and adapter ID/version.
- Capability scope and target resource.
- Risk level and policy decision.
- Canonical argument digest computed from bounded strict JSON by the gate; operation-specific schema validation is still required before an adapter can be enabled.
- Approval token, if required, including expiry, one-time use and exact binding.
- Dependency completion from the durable step journal, not caller-supplied completion claims.
- Deadline, cancellation state, rate and resource budgets.

**Argument-binding increment:** `ApprovalStore.issue_for_arguments()` and `ExecutionGate.start_step()` now accept the exact bounded JSON payload rather than a caller-provided digest. Both independently parse and canonicalize the payload using `intelligence/runtime/argument_binding.py`; the gate computes the digest itself. `start_step_with_arguments()` also returns the deeply immutable parsed argument object alongside its canonical JSON and digest, so a future executor can consume exactly the authorized values without reparsing mutable caller input. The low-level digest-based transition is private to the module. This does not authenticate the approver or principal, validate operation-specific schemas, or provide OS isolation; those remain separate gates.

## 5. Transaction and persistence rules

- Task, canonical plan and initial step records are persisted atomically in the task database.
- Step transitions and their event records are committed in one SQLite write transaction.
- Event history is append-only and hash-chain verification must fail closed.
- Approval token consumption and the corresponding high-risk step start must share one transaction.
- Low-risk grants currently live in a separate permission database. Their consumption can precede a step-start transaction; this is fail-closed but may burn a grant without starting the step. Do not claim cross-database atomicity.
- Database migrations must be versioned, repeatable, backed up and tested against the previous schema.
- Missing plan or authorization schema must never silently downgrade a plan-bound task to an unprotected legacy path.

## 6. Future executor interface

The first executor must be deliberately narrow. Its interface should accept a typed operation request, not a shell string:

- `request_id`: unique request identifier.
- `task_id` and `step_id`: canonical parent and step identity.
- `principal`: identity derived from authenticated IPC credentials, never trusted from request JSON.
- `adapter_id` and `adapter_version`.
- `operation_id`: allowlisted operation.
- `arguments`: bounded object validated against the operation schema.
- `idempotency_key`: stable key propagated to the external adapter where supported.
- `deadline`: bounded absolute deadline.
- `approval_reference`: opaque reference; never the raw token in logs.

The executor must return a structured result containing request/task/step identifiers, status, audit ID, start/end timestamps, adapter version, result digest, cancellation state and a typed error when applicable.

Prohibited interfaces:
- Generic `exec`, arbitrary shell, command interpolation or unrestricted root RPC.
- Arbitrary filesystem paths without scoped handles.
- Caller-selected UID/GID, policy, risk level or capability set.
- Agent-provided claims of successful completion.

## 7. Failure, timeout and cancellation

| Condition | Required handling |
|---|---|
| Validation or authorization denied | No side effect; record denial and leave step unstarted |
| Deadline expires before dispatch | Mark safely cancelled/failed according to state; do not dispatch |
| Read-only operation fails | Bounded retry only when explicitly permitted and within budget |
| Side effect returns known failure | Record failure and adapter evidence; require policy-controlled retry |
| Side effect outcome is unknown | `needs_review`; query authoritative external state before any new attempt |
| Process restarts with running step | Quarantine as `needs_review`; never auto-replay |
| Cancellation requested while running | Send cooperative cancellation; do not mark cancelled until adapter confirms no side effect |
| IPC peer disconnects | Treat outcome as unknown for side effects; reconcile by idempotency key or authoritative query |

## 8. Linux service boundary

The Linux IPC status daemon is a read-only, unprivileged service. Future execution services must be separate processes with separate UIDs and explicit operation scopes.

Required controls before enabling side effects:
- Kernel-derived peer identity using AF_UNIX credentials.
- Fixed UID-to-principal mapping managed by root-owned configuration.
- Authorization at the receiving service; transport authentication alone is insufficient.
- Dedicated service account and least-privilege filesystem ownership.
- Read-only root filesystem where practical and narrowly writable state directories.
- Network isolation by default; explicit egress policy per adapter.
- Namespaces, cgroup resource limits and a selected LSM policy.
- Seccomp policy tailored to each service. A default-allow denylist is defense in depth, not a complete sandbox.
- Socket path ownership/mode checks and protection against symlink/path replacement.
- Bounded frame size, request deadlines, connection quotas and audit redaction.
- No shared writable task/permission database access for untrusted agents.

The exact init/supervision and LSM choice remains an ADR decision for the production Linux track. Buildroot's current BusyBox init target is an experimental integration target, not the final phone platform.

## 9. Android service boundary

Android is a separate implementation track. The Linux AF_UNIX/ SO_PEERCRED daemon is not portable to Android.

Android execution must use:
- Binder/AIDL interfaces with stable versioned contracts.
- Distinct Android service identities and signature-level permissions.
- SELinux enforcing domains and narrowly defined service-manager access.
- AppOps/runtime permission checks for user data and sensors.
- Android Keystore for supported secret operations.
- Explicit user approval for external, destructive, account/security and device-integrity operations.

No root shell or generic privileged Binder method is an acceptable substitute for typed service APIs.

## 10. Verification matrix

| Test class | Required cases |
|---|---|
| Plan integrity | Plan substitution, digest tampering, missing plan table, altered dependencies |
| Approval | Expiry, replay, wrong task/step/arguments, wrong principal, forged token, concurrent consumption |
| Journal | Hash-chain tampering, append-only enforcement, migration, crash recovery, retry budgets |
| IPC | Wrong UID/GID, malformed/oversized frames, duplicate keys, replay, slow clients, socket replacement |
| Executor | Duplicate dispatch, idempotency propagation, deadline, cancellation race, ambiguous external outcome |
| Sandbox | Filesystem escape, process creation, network egress, namespace escape, syscall denial, resource exhaustion |
| Integration | Restart service, database recovery, overlay parity, QEMU boot and status request |
| Android | Binder caller identity, SELinux denial, AppOps denial, signature permission and revocation |

## 11. Exit gates before enabling a tool executor

1. Authenticated principal identity is enforced at the receiving service.
2. The broker validates operation-specific schemas and computes the argument digest from canonical input.
3. Approval identity is bound to a real authenticated user/session, not a free-form approver label.
4. Task, step, grant and approval transitions have tested transactional semantics.
5. A native OS boundary blocks unauthorized database and adapter access.
6. A first non-destructive reference adapter passes positive and negative integration tests.
7. Crash, timeout, cancellation and ambiguous-outcome reconciliation tests pass.
8. QEMU image tests prove the service starts with the intended UID and policy.
9. Security review finds no unresolved critical/high bypass in the enabled operation scope.

Until all gates pass, `tool_execution` remains disabled.
