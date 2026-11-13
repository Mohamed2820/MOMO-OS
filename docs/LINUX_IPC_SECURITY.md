# MOMO OS — Linux IPC Security Foundations

**Status:** Linux AF_UNIX peer identity and bounded versioned message framing implemented and unit tested. Neither primitive is yet connected to a privileged daemon or executor.

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

Before binding its socket, the IPC daemon applies hard process limits: zero core dumps, 32 open file descriptors, zero file-size growth and 256 MiB address space. A hard cumulative CPU-time limit was deliberately omitted because it would eventually terminate a healthy long-lived daemon. It also sets Linux `PR_SET_NO_NEW_PRIVS`. These controls reduce impact but are not a syscall allowlist: no seccomp filter, mount/user/network namespace, cgroup policy or LSM profile is installed. Do not describe this as a complete sandbox.
