# MOMO OS — Linux IPC Security Foundations

**Status:** Linux AF_UNIX peer identity and bounded versioned framing are integrated into an unprivileged, read-only status daemon. The daemon has process-lifetime replay detection, resource limits, no_new_privs and a libseccomp default-allow denylist. It is not a tool executor or complete sandbox.

## Peer identity

`linux_peercred.py` reads kernel-provided PID, UID and primary GID through `SO_PEERCRED`, then enforces explicit UID and optional primary-GID allowlists. Supplementary groups are not part of this credential tuple.

## Protocol framing

`ipc_protocol.py` defines version 1 request frames using a 4-byte network-order length prefix and a 64 KiB maximum payload. It rejects malformed lengths, truncated frames, trailing bytes, invalid UTF-8, duplicate JSON keys, non-finite numbers, unsupported versions, unexpected/missing top-level fields and invalid request identifiers/operation names. It provides no operation dispatcher.

## Security boundaries

- Transport framing is not authentication; call peer-credential checks before trusting a connected local peer.
- Peer identity is not authorization; a service must map UID to a fixed service role and check each operation's capability.
- The protocol parser does not prevent replay by itself, rate-limit clients, impose socket deadlines, or provide process isolation.
- Neither helper is wired into a privileged service. No external command/tool execution is enabled.
- Linux-specific AF_UNIX mechanisms do not apply to Android. Android requires a separate Binder/AIDL, SELinux and AppOps implementation.

## Next integration gate

Implement a narrowly scoped unprivileged service using a dedicated UID, authenticate the peer before parsing, apply socket deadlines and message quotas, validate operation-specific argument schemas, bind each operation to a capability check, and run it under native Linux sandbox controls (namespaces, seccomp and LSM). Add adversarial tests for path replacement, replay, malformed frames, slow clients, resource exhaustion and unauthorized peer identities. Keep the tool executor disabled until these controls are verified.


## Replay defense increment (PR #39 candidate)

The status daemon now keeps a bounded 1,024-entry request-ID cache for the lifetime of one daemon process. Duplicate IDs are rejected after peer authentication and before operation dispatch; oldest IDs are evicted when capacity is reached. The CLI generates a fresh UUID-based request ID and validates response framing, exact response fields, duplicate JSON keys and the explicit disabled-execution marker.

This is process-lifetime replay detection, not durable anti-replay across daemon restarts. It is appropriate only for the current read-only status endpoint; future mutating operations require durable idempotency and outcome reconciliation, not merely this in-memory cache.


## Daemon process hardening increment (PR #40 candidate)

Before binding its socket, the IPC daemon applies hard process limits: zero core dumps, 32 open file descriptors, zero file-size growth and 256 MiB address space. A cumulative CPU-time hard limit is intentionally omitted because it would eventually terminate a healthy long-lived daemon. It also sets Linux `PR_SET_NO_NEW_PRIVS`. These controls reduce impact. A separate default-allow libseccomp denylist blocks selected dangerous syscalls, but this is not a strict syscall allowlist. Mount/user/network namespace, cgroup policy and LSM enforcement remain unimplemented. Do not describe this as a complete sandbox.


## Syscall hardening increment (PR #41 candidate)

The daemon now requires libseccomp and installs a syscall denylist after creating and listening on its AF_UNIX socket. The default action remains ALLOW; process creation/exec, ptrace, mount/namespace changes, reboot/kexec, BPF/keyctl/perf, io_uring, userfaultfd and cross-process memory syscalls are denied with EPERM. The image explicitly includes Buildroot libseccomp, and CI installs libseccomp development headers to test the filter in a subprocess.

This is not a strict syscall allowlist and is not equivalent to a complete sandbox. Filesystem read/write syscalls and many other kernel interfaces remain available. Namespace isolation, cgroup limits and an LSM policy are still required. If libseccomp cannot load or the filter cannot be installed, the daemon refuses to start.


## Integrated daemon status — 2026-11-14

The active bootable development branch includes `momo-ipcd`, started as the dedicated `momo-ipc` user. It authenticates the peer with `SO_PEERCRED` before parsing, accepts only the configured root UID, validates bounded versioned frames, rejects duplicate request IDs within the daemon process, applies file-descriptor/address-space/core/file-size limits, sets `PR_SET_NO_NEW_PRIVS`, and installs a required libseccomp default-allow denylist. The only exposed operation is read-only `status.read`; responses explicitly report `tool_execution: disabled`.

Both x86_64 and AArch64 QEMU workflows passed on integrated baseline commit `a7a4caf381553d9a697b68a093eff9520d8b0bda`:
- [x86_64 run #43454224817](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224817), artifact 14057431431.
- [AArch64 run #43454224951](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224951), artifact 14055169054.

### Remaining IPC/security gaps
- The replay cache is in memory and resets on restart; it is not durable mutation idempotency.
- The syscall filter is a default-allow denylist, not a strict allowlist.
- No namespace isolation, cgroup v2 resource policy, LSM worker profile or per-task filesystem isolation is integrated.
- The root-only peer policy is a single-user development policy, not a multi-user authorization model.
- No operation-specific capability dispatcher or tool executor exists.
- Android requires an independent Binder/AIDL + SELinux + AppOps implementation.

See [Linux Executor Isolation Specification](LINUX_EXECUTION_SANDBOX.md). Do not enable tool dispatch until its enablement gate is met.
