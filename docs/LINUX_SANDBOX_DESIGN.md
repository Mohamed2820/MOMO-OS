# MOMO OS — Linux Service Isolation and Sandbox Design

**Status:** Security design baseline. The current Buildroot IPC daemon uses a dedicated UID, resource limits, `no_new_privs`, a required libseccomp default-allow denylist and Landlock filesystem confinement. A shared kernel config fragment now requests namespaces, cgroups v2 controllers, seccomp filtering and Landlock for both QEMU architectures; the image workflows verify the resulting kernel `.config`. Service-level namespace/cgroup/Landlock enforcement is not yet implemented. No side-effecting tool executor is enabled.

## 1. Objectives

- Separate the model/orchestrator, policy broker, status services and future side-effecting adapters into distinct trust domains.
- Prevent an untrusted agent or compromised service from reading private databases, changing policy, replacing socket paths or obtaining ambient root authority.
- Bound CPU, memory, process count, file descriptors, writable storage, network access and request duration.
- Fail closed when a required isolation primitive is unavailable.
- Keep the boot, recovery and essential device functions independent of optional AI services.

## 2. Process roles

| Role | Identity | Allowed responsibility | Must not have |
|---|---|---|---|
| Boot supervisor | root | Start/stop services, create runtime directories, verify ownership/modes | Model/tool request handling |
| MOMO IPC status | dedicated `momo-ipc` UID | Read-only status response | Task DB write, permission DB access, shell, tool dispatch |
| Task runtime | dedicated UID, TBD | Task/plan/step persistence through its own API | Root, direct device control |
| Permission broker | dedicated UID, TBD | Grant and approval decisions, audit | Model inference, arbitrary adapter execution |
| Tool adapter | one identity per operation family | Narrow typed operation | General database access, arbitrary shell |
| Model worker | unprivileged identity | Inference and planning | Permission DB, signing keys, device nodes, privileged sockets |

A single service account shared by all services is not sufficient isolation for production.

## 3. Filesystem layout and ownership

Proposed layout (exact paths are subject to Buildroot/AOSP integration):

- `/usr`: immutable binaries and policy configuration, root-owned and read-only at runtime.
- `/etc/momo`: root-owned service allowlists and static policy; no secrets.
- `/run/momo`: ephemeral sockets and PID state; created at boot with explicit owner/group/mode.
- `/var/lib/momo/tasks`: task runtime state, writable only by task service.
- `/var/lib/momo/permissions`: grant and approval state, writable only by permission service.
- `/var/lib/momo/audit`: append-only audit state, writable through a narrow audit API.
- `/var/cache/momo`: bounded disposable cache; never authority-bearing state.

The current prototype stores task and permission databases under `/var/lib/momo`. Before splitting them into independent service identities, migrate them behind service APIs; do not solve access by making the directory world-writable.

## 4. IPC boundary

- AF_UNIX socket paths are created by the supervisor in a root-controlled directory.
- The service verifies socket type, owner and permissions before removing/replacing an existing path.
- The kernel-provided peer credentials are read from the connected socket.
- UID maps to a fixed principal configured by root; request JSON cannot set principal, UID, GID, role or capability.
- Each operation has its own strict schema and capability requirement.
- The service applies receive/send deadlines, bounded frames, connection limits, request quotas and replay/idempotency policy.
- A transport-authenticated peer is not automatically authorized for an operation.
- Status and diagnostics endpoints return redacted information only.

The existing daemon accepts root UID only and exposes `status.read`. That policy is acceptable for its current read-only boot diagnostic use, but it is not a design for future general user-facing or agent operations.

## 5. Linux kernel controls

### 5.1 Kernel prerequisites added to QEMU builds

`board/momo/kernel-security.fragment` requests UTS/IPC/user/PID/network namespaces, cgroups and the PID/CPU/memory/freezer/device controllers, seccomp filtering, and Landlock. Both x86_64 and AArch64 Buildroot workflows pass this fragment to the Linux kernel configuration and run `tools/validate_kernel_security_config.py` against the generated kernel `.config` before accepting the image. Repository CI also validates the fragment itself.

This proves only that the kernel exposes the required primitives. It does not prove that MOMO services enter namespaces, receive cgroup limits, or apply Landlock rules. Those enforcement and adversarial tests remain mandatory.

### 5.2 Identity and privilege

- Dedicated static service UID/GID per trust domain.
- Drop supplementary groups and all unnecessary effective/permitted capabilities.
- No setuid helper or ambient capability inheritance for model/agent processes.
- `PR_SET_NO_NEW_PRIVS` before seccomp or untrusted input processing.
- Explicit file/device access; no broad `/dev` or `/sys` access.

### 5.3 Namespaces

Evaluate and enable per service as supported by the target kernel:
- Mount namespace with a minimal read-only root view.
- PID namespace for process visibility/isolation.
- Network namespace with no interfaces for offline services.
- IPC namespace where System V/POSIX IPC is unnecessary.
- User namespace only after UID/GID mapping and kernel support are verified.

Namespace availability and configuration must be tested on the exact target kernel; a configuration file alone is not proof.

### 5.4 Seccomp

- Prefer a default-deny allowlist for production service profiles.
- Generate profiles from the actual syscall needs of each service and architecture.
- Keep architecture-specific syscall tables explicit.
- Deny process creation/exec, ptrace, mount/namespace changes, reboot/kexec, BPF, key management, cross-process memory and other unnecessary interfaces.
- Test both allowed and denied syscalls in a subprocess.
- A default-allow denylist, including the current IPC daemon policy, is defense in depth and must never be described as complete isolation.

### 5.5 LSM

Select and document an LSM strategy for the production Linux platform:
- AppArmor profiles may be practical for a distribution-style Linux userspace.
- SELinux may be preferable where the chosen platform already has a maintained policy ecosystem.
- Landlock may add per-process filesystem restrictions where supported, but does not replace a full service policy.
- The final choice must be made by ADR after evaluating kernel configuration, policy tooling, maintainability and integration with the chosen init system.

### 5.6 Resource controls

Use cgroups v2 or the platform's supported equivalent to bound:
- CPU quota and weight.
- Memory and swap.
- Process count.
- I/O bandwidth where relevant.
- Network egress through namespace/firewall policy.

RLIMIT values remain defense in depth, not a substitute for service-level resource control.

## 6. Service manager integration

The current experimental Buildroot target uses BusyBox init scripts. Production service supervision is not selected.

Any selected supervisor must provide:
- Explicit service ordering and dependency handling.
- Restart policy with rate limits.
- Per-service UID/GID and capability drop.
- Namespace and filesystem sandbox options.
- Resource control integration.
- Structured logs and readiness/health reporting.
- Clean shutdown and recovery semantics.

Do not migrate to systemd, OpenRC or another init system without an ADR and an upstream compatibility assessment.

## 7. Android distinction

Linux namespaces, AF_UNIX peer credentials, seccomp and Linux service accounts do not define Android's security model. Android needs separate Binder caller identity, SELinux domains, AppOps, signature permissions, scoped storage and Keystore integration. See `docs/ANDROID_PLATFORM_INTEGRATION.md`.

## 8. Required adversarial verification

- UID/GID spoofing attempts and unexpected supplementary groups.
- Socket path symlink, stale socket and ownership replacement.
- Filesystem traversal, symlink escape and writable-path abuse.
- Unexpected process creation, exec, ptrace, mount and namespace syscalls.
- Network access from offline services.
- Memory/CPU/fd/process exhaustion and slow-client attacks.
- Service restart while a request or side effect is in flight.
- Database read/write attempts from an unauthorized UID.
- Policy file replacement and permission database tampering.
- Seccomp/LSM absence or misconfiguration must prevent the protected service from starting.

## 9. Promotion gates

1. Service identity and UID mapping reviewed.
2. Task and permission databases are owned by separate services or accessed only through authenticated APIs.
3. Namespace, cgroup and LSM policies are enforced on the target kernel.
4. Production seccomp allowlist passes positive and negative tests on x86_64 and AArch64.
5. Filesystem and network boundaries pass adversarial integration tests.
6. Reboot and recovery behavior is proven with services isolated.
7. Independent security review approves the enabled operation scope.

Until then, MOMO may expose read-only status and local development diagnostics, but must not enable general agent-driven side effects.
