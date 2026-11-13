# Release, Update and Recovery Policy

Status: release requirements; no installable production image is currently declared.

## Release channels
- nightly: CI artifacts for developers, not daily-use devices.
- alpha: limited hardware validation with explicit risks.
- beta: feature-complete candidate with regression and recovery tests.
- stable: signed release, supported device matrix, security response process and rollback path.

## Artifact provenance
Every release records source commit, build manifest, toolchain, device profile, build logs, test results, SBOM, licenses, signing identity, checksums and support tier. Reproducible builds are preferred and deviations are documented.

## Update requirements
- Signed update metadata and artifact verification.
- Staged rollout with health checks.
- Atomic/A-B update or platform-native safe update strategy where supported.
- Battery, storage and network preconditions.
- User-visible changelog and permissions changes.
- Rollback/recovery plan validated per device.
- Security updates tracked against upstream Android/Linux advisories.

## Stop-ship conditions
No stable release if boot recovery is untested, signature verification fails, data migration is destructive without recovery, critical vulnerabilities remain, device feature claims lack evidence, or OTA rollback is broken.

## Recovery
Publish exact device/SKU recovery instructions, stock firmware source, required tools, data-loss warnings and verified restore test results. Never provide generic flashing instructions as though partition layouts are interchangeable.
