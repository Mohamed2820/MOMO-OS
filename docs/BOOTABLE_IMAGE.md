# MOMO OS Bootable Image — x86_64 Bring-up

Status: first bootable Linux integration target; experimental and not a phone ROM.

## What this target is

This target uses the upstream Buildroot distribution builder and its maintained
`qemu_x86_64_defconfig` to produce a minimal Linux kernel and root filesystem.
MOMO-owned startup and diagnostic utilities are added through a root filesystem
overlay. The image is intended to prove the repository can produce and boot a
real Linux system before the Android-compatible and mobile Linux device ports
are attempted.

It is not an AOSP build, Android replacement, production distribution, or
hardware-independent phone image. The x86_64 QEMU target is a controlled
bring-up platform. Each phone still needs its own boot chain, kernel/vendor
support, firmware, device tree and hardware validation.

## Included MOMO components

- `/etc/momo-release`: build identity and track metadata.
- `/etc/init.d/S99momo`: first-boot banner and readiness check.
- `/usr/bin/momoctl`: status, doctor, task-management, version and help commands.
- `/usr/bin/momo-task`: persistent task CLI (create/list/show/transition/self-test).
- `/usr/bin/momo-device`: reports OS/kernel/device identity and conservative hardware capability states.
- `/usr/bin/momo-permissions`: initializes the durable permission journal, displays audit events, and revokes grants.
- `/usr/lib/momo/intelligence/runtime`: bundled task state machine, SQLite task journal, device inventory, and persistent permission broker.
- Python 3 with the SQLite module, enabled in the Buildroot target configuration.
- Build workflow: builds Buildroot, boots the image under QEMU, and requires
  the MOMO readiness marker before uploading artifacts.

## Build and test

Run the GitHub Actions workflow **MOMO OS — x86_64 bootable image** manually
from the Actions tab, or push a change to the bootable image branch.

The workflow downloads the pinned Buildroot release, applies
`qemu_x86_64_defconfig`, injects the MOMO rootfs overlay, builds the kernel
and root filesystem, then boots them with QEMU. A successful job must observe
`MOMO OS READY` in the serial console log.

Artifacts include the kernel, root filesystem, boot log and build metadata.
The image must be treated as experimental and run in a virtual machine only.

## Local QEMU invocation

After a successful workflow artifact download and extraction:

```sh
qemu-system-x86_64 -M pc -m 1024 \
  -kernel bzImage \
  -drive file=rootfs.ext2,if=virtio,format=raw \
  -append "rootwait root=/dev/vda console=ttyS0" \
  -serial stdio -display none
```

## Acceptance criteria

1. Buildroot completes without errors.
2. The kernel and root filesystem artifacts exist and are non-empty.
3. QEMU reaches the MOMO init script.
4. The serial log contains `MOMO OS READY`.
5. The `momoctl` health checks pass during boot, including device inventory, permission database initialization, and an authenticated read-only IPC status request through the unprivileged daemon.
6. Python 3 can import SQLite, create a temporary MOMO task, persist five valid transitions, and restore the completed task.
7. The device inventory command reports the running architecture and leaves unverified hardware capabilities as `unknown`.
8. The persistent permission broker initializes its database and exposes its audit/revocation commands.

A successful QEMU boot validates only this x86_64 virtual target. It does not
establish support for ARM phones or the Samsung Galaxy A17.


## Runtime security integration validation — 2026-11-14

The current development branch adds the durable plan-bound step journal, the execution approval gate, and a local read-only IPC status daemon. The daemon runs under the dedicated `momo-ipc` account, authenticates local peers using Linux `SO_PEERCRED`, enforces bounded protocol frames, applies process limits and `no_new_privs`, and requires a libseccomp syscall denylist before serving the status-only operation.

The x86_64 and AArch64 workflows now include the daemon and require the boot log to show both `MOMO OS READY` and the IPC service marker with tool execution explicitly disabled.

**Evidence boundary:** these additions are not covered by the earlier QEMU acceptance run. A fresh successful run of each workflow is required before claiming that the updated image boots on either virtual target. Neither virtual target proves physical phone compatibility.

## Latest integrated image evidence — 2026-11-14

The execution-gate integration is included in commit `b762dd742e8b3b3ede0e5f98578960446c9b5e25`. Fresh builds passed:
- x86_64: [workflow #43597839201](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839201), artifact 14115143750.
- AArch64: [workflow #43597839262](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839262), artifact 14114803046.

Both guests reached `MOMO OS READY` and returned the `momo-ipcd` read-only status response with `tool_execution: disabled`. Buildroot cache recovery now forces a Linux package rebuild if the expected kernel image is absent from `output/images`.

These are QEMU virtual targets. They do not establish Android ROM support or compatibility with any physical phone.
