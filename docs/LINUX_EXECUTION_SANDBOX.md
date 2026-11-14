# MOMO OS — Linux Executor Isolation Engineering Specification

**Status:** Design specification. The current `momo-ipcd` is a read-only status daemon, not an executor. The current libseccomp policy is a default-allow denylist and is not a complete sandbox. No tool execution may be enabled on the basis of this document alone.

## 1. Objective

Define the Linux enforcement architecture required before MOMO can run any model-proposed operation. The security objective is to ensure that a compromised model, agent, parser or worker cannot obtain ambient host authority, escape its task scope, or silently perform an unapproved side effect.

## 2. Process separation

Use separate service identities and responsibilities:

| Identity/service | Responsibility | Authority |
|---|---|---|
| `momo-core` | Own task lifecycle and canonical plans | Task DB access only |
| `momo-permissions` | Capability grants and approval policy | Permission DB access only |
| `momo-ipc` | Current read-only status endpoint | Status socket and status data only |
| `momo-exec` | Future per-task worker supervisor | Create constrained workers; no unrestricted host access |
| Per-task worker | Execute one typed operation | Only the task's declared resources and capabilities |

Do not run the future executor as root. If a privileged setup step is unavoidable, isolate it in a tiny, fixed-function broker with a narrow request schema; never pass model-generated shell strings to it.

## 3. Request path

1. Authenticate the local peer using kernel-provided credentials.
2. Map the peer UID/GID to a fixed service principal; do not trust a role supplied in JSON.
3. Validate protocol version, request size, request ID and operation schema.
4. Load the immutable task plan and verify its digest and current state.
5. Obtain a fresh capability decision or authenticated human approval for the exact operation.
6. Canonicalize the operation and arguments inside the trusted broker; compute the arguments digest there.
7. Reserve the durable idempotency key and record a dispatch-intent event.
8. Create a worker with the minimum namespace, cgroup, filesystem, network and syscall permissions.
9. Dispatch only a registered typed operation; no arbitrary command or executable path.
10. Collect a structured result, terminate the worker, verify the outcome independently and persist evidence.
11. On timeout, crash or uncertain side effect, mark the step `needs_review`; never replay blindly.

## 4. Isolation profile

### Namespaces
- User namespace: map the worker to an unprivileged identity; do not expose host capabilities.
- Mount namespace: read-only base filesystem; task-specific writable workspace only; private temporary filesystem.
- PID namespace: worker sees only its own process tree.
- IPC namespace: isolate System V/POSIX IPC resources.
- Network namespace: no network by default. Enable narrowly scoped connectivity only for a typed operation that requires it.
- UTS namespace: isolate hostname where supported.

Namespace availability is kernel/configuration dependent. If a required namespace cannot be created, the operation must be refused rather than silently run without isolation.

### Cgroups
Use cgroup v2 where available. Define per-worker CPU, memory, process-count and I/O limits, plus a supervisor-enforced wall-clock deadline. Failure to attach a worker to its required cgroup is a hard failure.

### Syscall policy
Replace the daemon's default-allow denylist with a separately designed worker policy:
- Default action: deny.
- Allow only the syscall set required by the selected operation/runtime.
- Architecture-aware syscall-number validation.
- Deny privilege transitions, mount manipulation, kernel interfaces, tracing, cross-process memory access and process creation not required by the worker model.
- Install the filter before untrusted operation code runs.
- Test both allowed behavior and explicit EPERM/kill behavior for forbidden calls.

A single broad allowlist for every tool is not acceptable. Profiles should be operation-family specific and versioned.

### LSM and filesystem
- Enforce an LSM policy (AppArmor, SELinux or another supported LSM) with a dedicated worker domain/profile.
- Deny host home directories, signing material, credentials, device nodes and unrelated service databases.
- Expose only a task workspace and explicitly granted read-only inputs.
- Use `no_new_privs`, drop capabilities, set restrictive umask and resource limits.
- Do not assume `no_new_privs` or seccomp alone provides filesystem isolation.

## 5. Typed operation model

Every operation must have:
- Stable operation ID and semantic version.
- Strict input and output schema.
- Declared read/write resources and data classification.
- Risk class and required capabilities.
- Network requirement and allowed destinations, if any.
- Timeout, cancellation and resource budget.
- Idempotency behavior and reconciliation method.
- Result-verification procedure.
- Dedicated sandbox profile and test suite.

Reject unknown fields, path traversal, symlink escapes, device paths, executable selection and arbitrary shell fragments. Resolve file access against an opened directory descriptor and enforce containment at the OS boundary, not only with string-prefix checks.

## 6. Reliability and recovery

- Persist dispatch intent before launching a worker.
- Pass a stable idempotency key to downstream systems where supported.
- Treat timeout/connection loss as an unknown outcome unless independent evidence proves no side effect occurred.
- Cancellation is a request until the supervisor confirms worker termination and the operation's side-effect state.
- On supervisor restart, reconcile in-flight workers and task records; do not automatically replay.
- Keep a tamper-evident audit chain and protect its storage with OS permissions and, later, external signing/anchoring.

## 7. Adversarial verification matrix

| Test | Expected result |
|---|---|
| Unapproved UID connects | Rejected before request parsing |
| Client spoofs UID in payload | Ignored; kernel credentials are authoritative |
| Oversized/truncated/malformed frame | Rejected without dispatch |
| Duplicate request ID | Rejected; durable idempotency governs mutations |
| Unknown operation or extra argument | Rejected |
| Path traversal or symlink swap | Cannot escape task workspace |
| Attempt to read host secrets | Denied by filesystem/LSM boundary |
| Attempt to exec shell or spawn forbidden process | Denied by operation policy/seccomp |
| Attempt to mount, ptrace, BPF or alter namespaces | Denied |
| Exceed memory/CPU/PID/deadline budget | Worker stopped and task outcome reconciled |
| Kill worker during external side effect | Step becomes `needs_review`; no blind retry |
| Missing namespace/cgroup/LSM support | Operation refused; no weaker fallback |
| Corrupt plan or event chain | Authorization/dispatch refused |
| Reuse or mismatch approval token | Refused without dispatch |

## 8. Kernel and Buildroot prerequisites

Before implementing the executor, verify the selected Buildroot kernel configuration enables the required namespace, cgroup v2, seccomp and LSM features. Record each exact config symbol and runtime probe. QEMU tests must demonstrate the feature is actually available; a config file alone is not evidence.

Keep x86_64 and AArch64 profiles separate where syscall ABI or kernel behavior differs. Physical devices require their own kernel configuration, vendor constraints and test evidence.

## 9. Android counterpart

The Android track must not reuse Linux AF_UNIX assumptions. Its enforcement path is Binder/AIDL with authenticated calling UID, signature-level permissions, SELinux domains, AppOps/runtime permissions, scoped storage and Android Keystore. The same typed MOMO operation/capability contract should map to native Android controls. Do not weaken verified boot or SELinux to make an adapter work.

## 10. Enablement gate

The executor remains disabled until all of the following are true:
- Authenticated approval identity and broker-only issuance are implemented.
- Actual arguments are canonicalized and hashed by the trusted executor.
- Capability reservation/consumption is atomic with durable dispatch intent.
- Per-task namespace, cgroup, LSM and strict seccomp profiles are enforced.
- Worker identity and operation schemas are validated.
- Adversarial tests pass on both x86_64 and AArch64 QEMU targets.
- Crash, cancellation, duplicate dispatch and unknown-outcome reconciliation tests pass.
- Independent security review has no unresolved critical/high finding.
