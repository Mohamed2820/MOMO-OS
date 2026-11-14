# Cloud Build and Source Pipeline

Status: GitHub Actions currently builds and QEMU-tests the Buildroot x86_64 and AArch64 virtual targets. No dedicated AOSP cloud build machine has been provisioned and no Android image has been built.

## Why cloud
AOSP's published build requirements call for a 64-bit x86 workstation, approximately 400 GB free disk, and at least 64 GB RAM. A phone is not an appropriate full Android build host.

## Pipeline
1. Resolve a manifest with immutable source revisions.
2. Verify remotes, licenses, source hashes, and manifest provenance.
3. Create an isolated ephemeral x86_64 Linux build worker with sufficient memory and disk.
4. Sync source with Repo and persistent cache volumes where cost-effective.
5. Build an unmodified baseline before applying MOMO patches.
6. Run static checks, unit tests, and build target validation.
7. Generate checksums, build metadata, SBOM, and source revision inventory.
8. Store artifacts in private, access-controlled storage.
9. Publish only after device validation, signing review, and release approval.

## GitHub Actions role
GitHub Actions is appropriate for repository linting, unit tests, manifest validation, metadata generation, and orchestration. It should not be assumed to have enough resources for a full AOSP build on standard hosted runners.

## Secret handling
Never place signing keys, provider API keys, or cloud credentials in source files or logs. Use short-lived workload identity or protected secret storage. Separate test signing from release signing.

## Cost controls
Set maximum worker size, wall-clock timeout, cache quota, artifact retention, and approval gates. Stop workers after jobs complete. Do not start a costly full source sync without a pinned manifest and explicit budget.

## Release evidence
Every artifact must link to commit SHA, manifest SHA, toolchain, build environment, build logs, SBOM, checksum, signing identity, and device compatibility status.

## Reference links
- [AOSP build environment requirements](https://source.android.com/docs/setup/start/requirements)
- [AOSP build and source workflow](https://source.android.com/docs/setup/start)

These requirements are periodically updated; re-check them before provisioning a build worker.


## Current Buildroot automation evidence — 2026-11-14

The repository has two Buildroot/QEMU workflows:
- x86_64: [run #43597839201](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839201).
- AArch64: [run #43597839262](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839262).

Both passed on commit `b762dd742e8b3b3ede0e5f98578960446c9b5e25`, including image verification, guest boot, readiness, read-only IPC status and artifact publication. The workflows recover from a missing exported kernel image after cache restore by forcing a Linux package rebuild.

This does not provide the disk/RAM capacity or source-manifest workflow needed for a full AOSP build. Android build infrastructure remains unprovisioned.
