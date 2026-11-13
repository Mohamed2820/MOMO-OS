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
