# MOMO OS — Linux IPC Security Foundations

**Status (2026-11-14):** A read-only Linux AF_UNIX status daemon is integrated into the Buildroot rootfs. It uses kernel peer credentials, bounded versioned framing, replay detection, a dedicated UID, private mount/IPC/UTS/network namespaces, cgroup v2 CPU/memory/PID limits, process resource limits, `no_new_privs`, a required libseccomp denylist and Landlock filesystem confinement. Repository CI passes 201 tests. Fresh x86_64 and AArch64 QEMU acceptance for the namespace/cgroup/Landlock startup path is still pending. No side-effecting tool executor or privileged operation dispatcher is enabled.

## Peer identity

`linux_peercred.py` reads kernel-provided PID, UID and primary GID through `SO_PEERCRED`, then enforces explicit UID and optional primary-GID allowlists. Supplementary groups are not part of this credential tuple.

## Protocol framing

`ipc_protocol.py` defines version 1 request frames using a 4-byte network-order length prefix and a 64 KiB maximum payload. It rejects malformed lengths, truncated frames, trailing bytes, invalid UTF-8, duplicate JSON keys, non-finite numbers, unsupported versions, unexpected/missing top-level fields and invalid request identifiers/operation names. It provides no operation dispatcher.

## Security boundaries

- Transport framing is not authentication; call peer-credential checks before trusting a connected local peer.
- Peer identity is not authorization; a service must map UID to a fixed service role and check each operation's capability.
- The protocol parser does not prevent replay by itself, rate-limit clients, impose socket deadlines, or provide process isolation.
- The peer-credential and protocol helpers are wired into the read-only status service. No external command/tool execution is enabled.
- Linux-specific AF_UNIX mechanisms do not apply to Android. Android requires a separate Binder/AIDL, SELinux and AppOps implementation.

## Next integration gate

Extend the existing status-service controls to task and executor services; add authenticated human/session principal mapping, per-operation schema/capability enforcement, socket deadlines and quotas, a strict seccomp allowlist, PID/user namespace policy, per-service cgroups and Android Binder/SELinux equivalents. Add adversarial tests for path replacement, replay, malformed frames, slow clients, resource exhaustion and unauthorized identities. Keep side-effecting execution disabled until those controls are independently verified.


## Replay defense increment (PR #39 candidate)

The status daemon now keeps a bounded 1,024-entry request-ID cache for the lifetime of one daemon process. Duplicate IDs are rejected after peer authentication and before operation dispatch; oldest IDs are evicted when capacity is reached. The CLI generates a fresh UUID-based request ID and validates response framing, exact response fields, duplicate JSON keys and the explicit disabled-execution marker.

This is process-lifetime replay detection, not durable anti-replay across daemon restarts. It is appropriate only for the current read-only status endpoint; future mutating operations require durable idempotency and outcome reconciliation, not merely this in-memory cache.


## Daemon process hardening increment (PR #40 candidate)

Before binding its socket, the IPC daemon applies hard process limits: zero core dumps, 32 open file descriptors, zero file-size growth and 256 MiB address space. A cumulative CPU-time hard limit is intentionally omitted because it would eventually terminate a healthy long-lived daemon. It also sets Linux `PR_SET_NO_NEW_PRIVS`. These controls reduce impact. A separate default-allow libseccomp denylist blocks selected dangerous syscalls, but this is not a strict syscall allowlist. Mount/user/network namespace, cgroup policy and LSM enforcement remain unimplemented. Do not describe this as a complete sandbox.


## Syscall hardening increment (PR #41 candidate)

The daemon now requires libseccomp and installs a syscall denylist after creating and listening on its AF_UNIX socket. The default action remains ALLOW; process creation/exec, ptrace, mount/namespace changes, reboot/kexec, BPF/keyctl/perf, io_uring, userfaultfd and cross-process memory syscalls are denied with EPERM. The image explicitly includes Buildroot libseccomp, and CI installs libseccomp development headers to test the filter in a subprocess.

This is not a strict syscall allowlist and is not equivalent to a complete sandbox. Filesystem read/write syscalls and many other kernel interfaces remain available. Namespace isolation, cgroup limits and an LSM policy are still required. If libseccomp cannot load or the filter cannot be installed, the daemon refuses to start.


## Integrated read-only daemon — 2026-11-14

The Linux status service is now implemented in `board/momo/rootfs-overlay/usr/lib/momo/momo_ipcd.py` and mirrored in the Buildroot overlay. Init script `S98momo-ipc` starts it as the dedicated unprivileged `momo-ipc` account. The service accepts root-owned clients only, authenticates the connected process using `SO_PEERCRED`, parses one bounded protocol frame, rejects duplicate request IDs within the daemon lifetime, and serves only `status.read` with an empty argument object.

The root-started `momo-ipc-sandbox` wrapper joins a dedicated cgroup (128 MiB memory, 16 processes, 50% CPU quota), enters private mount/IPC/UTS/network namespaces and drops to `momo-ipc`. The daemon applies resource limits and `PR_SET_NO_NEW_PRIVS`, requires libseccomp to install a default-allow denylist, binds its socket, then applies a fail-closed Landlock read-only filesystem policy before accepting requests. It refuses to start if libseccomp is missing or filter installation fails. The current CLI `momo-ipcctl status` is read-only. The response explicitly reports `tool_execution: disabled`.

### Verified and pending

- Repository CI for integration PR #48 passed 201 unit tests, including Landlock filesystem allow/deny, kernel config validation, typed executor and source/rootfs parity (run #43603174498).
- The earlier QEMU acceptance applies to an older image revision and does not validate this daemon.
- Fresh x86_64 and AArch64 Buildroot/QEMU boot checks are required before this increment receives image-integrated/emulator-tested status.
- The daemon is not a general-purpose executor. Future mutating operations require a separate authorization design, durable idempotency, outcome reconciliation and stronger per-operation principals.


## Landlock filesystem confinement — 2026-11-14

The read-only IPC daemon now installs a Landlock ruleset after binding its AF_UNIX socket and loading the seccomp filter. The daemon receives read/execute access to `/usr` and read access to `/etc`; `/run/momo` is limited to directory metadata and removal of its own socket during shutdown. Other filesystem paths receive no handled filesystem rights. Landlock setup is fail-closed: if the kernel syscall or ruleset operation is unavailable, the daemon does not enter its accept loop.

A subprocess test proves that an explicitly allowed directory remains readable, an unrelated directory is unreadable, and writes in the allowed read-only directory are denied. This confines the status daemon's filesystem view. Separate launcher and init controls now provide namespaces and cgroup limits for this one service. It still lacks a strict seccomp allowlist and a human/session principal boundary; the profile is not yet applied to task or executor services.
