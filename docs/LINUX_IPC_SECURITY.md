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


## Unprivileged status daemon — implementation candidate (PR #38)

A first narrow AF_UNIX service is added as `momo-ipcd`. Buildroot provisions a dedicated `momo-ipc` account and starts the daemon through an init script. The daemon runs under that unprivileged identity, authenticates connected peers using kernel `SO_PEERCRED`, accepts only UID 0 for this single-user development image, and exposes exactly one read-only operation: `status.read`. The socket is placed under a daemon-owned runtime directory with mode 0660. The client command is `momoctl ipc-status`.

The service deliberately has no command execution, arbitrary filesystem access, task mutation, plugin dispatch, or tool adapter. It enforces connection timeouts and a small listen backlog. It rejects replacing a non-socket or socket not owned by its effective UID.

**Limitations:** root-only client identity is a development-image policy, not multi-user authorization. There is no replay defense, per-UID role database, operation-specific grant store, seccomp profile, namespace isolation, cgroup resource policy, LSM policy, or Android Binder implementation. The daemon is not considered production-secure until QEMU integration and adversarial target tests pass.
