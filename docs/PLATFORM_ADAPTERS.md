# Platform Adapter Contracts

## Purpose

Platform adapters isolate MOMO-owned services from Android and Linux implementation details. They are narrow interfaces, not an unrestricted escape hatch to root or shell.

## Adapter domains

- Boot and lifecycle
- Display, input and windowing
- Audio routing and media
- Power, thermal and battery
- Connectivity, telephony and SIM
- Camera and media capture
- Sensors and location
- Biometrics and secure hardware
- Storage, encryption and backup
- Package/application lifecycle
- Notifications and accessibility

## Contract requirements

Each adapter must declare:
- Stable adapter ID and semantic version.
- Platform track: android or mainline-linux.
- Supported API/framework and kernel ranges.
- Required and optional capabilities.
- Permission/risk classification for every operation.
- Input/output schemas and error semantics.
- Cancellation and timeout behavior.
- Audit event requirements.
- Unit, integration and hardware test references.

## Security

- Adapter methods expose typed operations only.
- No generic exec, arbitrary shell, raw root command, or unrestricted file path API.
- Privileged Android integration uses narrowly scoped system services and SELinux domains.
- Mainline Linux integration uses least-privilege D-Bus/portal/service interfaces where suitable.
- User approvals are bound to the exact operation, arguments, target and expiry.
- Agents cannot grant themselves capabilities or alter adapter policy.
- Every side effect returns a verifiable result and audit identifier.

## Compatibility behavior

Adapters report supported, unsupported, temporarily_unavailable, or permission_denied distinctly. The MOMO Experience layer must not present unavailable hardware features as functional. Optional capabilities can be hidden or degraded; core boot and security requirements cannot.


## AArch64 Linux virtual target — workflow added, validation pending

The project now defines a separate Buildroot target using `qemu_aarch64_virt_defconfig` and QEMU's `virt` machine. The same portable Python runtime and rootfs overlay are intended to build for AArch64. CI must prove kernel/rootfs build and guest readiness before this target is marked supported. Hardware device trees, firmware, boot chains, vendor kernels and drivers remain device-specific adapter work.
