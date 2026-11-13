# MOMO OS — Linux Local IPC Identity

**Status:** Kernel peer-credential primitive implemented and unit tested; not yet wired into a privileged service or executor.

## Design

On Linux, a connected AF_UNIX socket can expose the peer process credentials through `SO_PEERCRED`. MOMO's `intelligence.security.linux_peercred` helper reads the kernel-provided PID, UID and primary GID, then checks explicit UID and optional primary-GID allowlists.

The source module is mirrored into the Buildroot root filesystem overlay. Tests cover current-process credentials, exact allowlists, UID/GID denial, empty allowlists, invalid policy values and rejection of non-AF_UNIX sockets.

## Important boundaries

- `SO_PEERCRED` identifies the connected process credentials reported by the kernel; it is not a capability grant or authorization to perform a requested action.
- The primary GID is reported. Supplementary group membership is not part of this credential tuple and requires a separately trusted identity source if policy needs it.
- A UID/GID allowlist is only one input to a service policy. It does not provide message schema validation, replay protection, rate limiting, process isolation, namespaces, seccomp, LSM policy or resource controls.
- The helper is not yet called by a production MOMO daemon. No external command or tool execution is enabled by this change.
- Linux-specific behavior must not be reused as an Android IPC design; the Android track will use Binder/AIDL and SELinux/AppOps policy.

## Next integration gate

Before a privileged broker is exposed, add a narrow versioned Unix-socket protocol, validate peer identity before parsing or acting on requests, bind the peer UID to an explicit service role, enforce request schemas and per-operation capabilities, and run the service under a dedicated unprivileged identity. Add adversarial tests for spoofed fields, malformed frames, oversized messages, replay, path replacement and unauthorized UIDs. Native sandboxing remains a separate mandatory layer.
