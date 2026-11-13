# Universal Mobile Platform Strategy

## Product decision

MOMO OS is a device-adaptive mobile computing platform, not a ROM for one phone model. Product identity, user experience, AI runtime, system APIs, and security policy remain consistent while boot and hardware integration vary by device family.

"Universal" is a long-term compatibility objective, not a claim that one binary can boot every phone. Each device needs a verified boot path and working support for its SoC, display, storage, power, radio, audio, camera, sensors, and security hardware.

## Two platform tracks, one MOMO experience

### Track A — Android-compatible platform (initial priority)
- Use AOSP/Android Common Kernel and established Android platform interfaces where appropriate.
- Integrate device-specific vendor components and HALs through explicit, versioned adapters.
- Preserve Android application compatibility as a major practical advantage.
- Keep MOMO services, shell, AI runtime, and policy layers separate from vendor-specific code.

This is the pragmatic first track because Android has a broad commercial-device driver and HAL ecosystem. GKI separates a generic kernel core from vendor modules, but does not eliminate device-specific integration or guarantee arbitrary image compatibility.

### Track B — Mainline Linux mobile platform
- Support devices with usable mainline kernel drivers and an upstreamable device tree.
- Reuse mature Linux user-space components and mobile shells where practical.
- Provide a compatibility/runtime strategy for mobile applications; do not assume Android APK compatibility is automatic.
- Track modem, suspend/resume, GPU acceleration, camera, audio, fingerprint and power-management maturity separately.

The two tracks share MOMO-owned UX concepts, AI orchestration, task APIs, user data formats, policy contracts, and app-facing service abstractions. They do not share a kernel image or assume identical hardware APIs.

## Layer boundaries

1. MOMO Experience — launcher/shell, notifications, settings, windows, desktop mode, accessibility.
2. MOMO Intelligence — planner, agents, model router, memory, tool registry, evaluations.
3. MOMO System Services — files, search, automation, task/activity APIs, sync and backup.
4. MOMO Security — identity, capability grants, approval UI, audit, sandbox policy and secret storage.
5. Compatibility Runtime — stable MOMO APIs mapped to Android framework/HAL or Linux services.
6. Platform Adapter — boot integration, init, SELinux/policy integration, graphics, audio, power, radio and device-specific adapters.
7. Kernel and Firmware — upstream/GKI or device kernel, drivers, firmware, bootloader and secure boot chain.

No upper layer may directly assume a vendor-specific sysfs node, ioctl, HAL implementation, partition layout, or privileged shell command. Device-specific behavior belongs behind a tested adapter.

## Architecture rules

- Platform-independent code is the default; device-specific code requires a documented adapter and compatibility test.
- Version every adapter contract and declare supported platform/API/kernel ranges.
- Discover hardware capabilities at runtime; do not infer them from marketing names alone.
- Degrade gracefully: unsupported features must be visibly unavailable, not simulated as working.
- Never bypass secure boot, AVB, SELinux, verified boot, or user consent as a general compatibility strategy.
- Keep device firmware and proprietary blobs out of the common platform repository unless redistribution rights are clear.
- Maintain per-device build manifests and signed, traceable artifacts.
- Use feature flags only for optional capabilities, never to conceal a broken boot or security boundary.

## Support tiers

- Tier 0 — Research: identity and source discovery only; no boot/install claim.
- Tier 1 — Buildable: reproducible build and static checks; hardware may not boot.
- Tier 2 — Boots: verified boot and basic display/input; major functions may be missing.
- Tier 3 — Daily-use candidate: telephony/data, Wi-Fi, Bluetooth, audio, camera, sensors, suspend/resume, encryption and OTA tested.
- Tier 4 — Maintained release: repeatable releases, security updates, rollback/recovery, regression suite and an active device maintainer.

Every release must publish its tier and feature matrix. "Supported" without a tier and tested feature list is prohibited.

## Initial architecture targets

- ARM64 Android devices with documented bootloader unlock and maintainable vendor support.
- Mainline-friendly ARM64 Linux phones as a separate porting cohort.
- x86_64 virtual/emulated targets for early CI and shell/service development, not as evidence of phone hardware support.

Do not select a single phone as the product's architectural boundary. A device may be used as an early bring-up target only when it has a credible recovery path.

## Acceptance criteria

- A clean checkout can build common MOMO components without device vendor trees.
- Device adapters declare exact model/codename, SoC, boot chain, kernel, firmware and supported features.
- CI validates profile schema, adapter API compatibility and required evidence fields.
- At least two distinct device families are used before claiming the architecture is multi-device.
- Android and mainline Linux tracks are tested independently.
- The release matrix states unsupported capabilities and known limitations.


## AArch64 virtual target bring-up — 2026-11-13 (PR #42 candidate)

A separate Buildroot/QEMU workflow is added for `qemu_aarch64_virt_defconfig`. It reuses the MOMO rootfs overlay, dedicated IPC account, unprivileged status daemon and libseccomp policy, then boots the ARM64 `Image` under `qemu-system-aarch64`. The workflow requires both `MOMO OS READY` and the authenticated status response marker. This is a virtual AArch64 target, not evidence of compatibility with any specific phone, tablet, SBC or laptop.
