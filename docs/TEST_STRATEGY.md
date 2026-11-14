# MOMO OS Test Strategy

## Test layers
1. **Repository:** markdown links, JSON/YAML parsing, manifest invariants, secret scanning.
2. **Unit:** policy engine, task state machine, schema validation, memory scope, model routing.
3. **Integration:** mock models, mock tool broker, Android service adapters, storage boundaries.
4. **Platform:** AOSP build, boot, SELinux enforcing, permission and AppOps behavior.
5. **Device:** radio, calls, SMS, Wi-Fi, Bluetooth, GPS, NFC, camera, audio, biometrics, sensors, charging, suspend, encryption, OTA, recovery.
6. **Security:** prompt injection, confused deputy, tool schema bypass, data exfiltration, privilege escalation, replay, audit tampering.
7. **Usability/accessibility:** keyboard, pointer, touch, voice, screen reader, Arabic and RTL layouts.

## Evidence levels
- **L0:** documentation only.
- **L1:** static validation.
- **L2:** unit tests pass.
- **L3:** integration tests pass.
- **L4:** emulator/platform boot and tests pass.
- **L5:** exact physical device tests pass.
- **L6:** release candidate independently reviewed and reproducible.

Never describe a feature as device-supported based only on L0-L3. A bootable image is not a stable release.

## Release gates
No public flashable build before L5 evidence for the exact supported model and a tested recovery procedure. Security-sensitive components require independent review.


## Current evidence snapshot — 2026-11-14

- Repository validation: 167 unit tests passed on the execution-gate code revision.
- Linux x86_64 QEMU: full Buildroot build, image checks, readiness and read-only IPC passed on commit `b762dd742e8b3b3ede0e5f98578960446c9b5e25` ([run #43597839201](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839201)).
- Linux AArch64 QEMU virt: full Buildroot build, image checks, readiness and read-only IPC passed on the same commit ([run #43597839262](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839262)).

These are L4 virtual-target results for the declared QEMU machines only. No L5 physical-device test, Android platform build, production executor isolation, signed release or OTA/recovery qualification has passed.
