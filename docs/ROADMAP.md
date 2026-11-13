# Roadmap

Milestones are gated by evidence and acceptance criteria, not calendar promises.

## M0 — Repository and governance foundation
- [x] Establish cloud-first, upstream-aware repository strategy.
- [x] Document architecture, security, licensing, and device feasibility gates.
- [ ] Add maintainers, issue templates, and contribution guidance.
- [ ] Inventory upstream candidates and exact licenses.

**Exit:** repository policy is clear; no unverified device or build claims.

## M1 — Device feasibility and base selection
- [ ] Confirm exact Galaxy A17 product variant/codename and regional SKU.
- [ ] Verify bootloader unlock availability for the exact variant and region.
- [ ] Locate official kernel sources and matching kernel configuration.
- [ ] Identify device tree, vendor blobs, HAL and firmware dependencies.
- [ ] Confirm partition layout, AVB/vbmeta, recovery and restore procedure.
- [ ] Compare AOSP and LineageOS integration cost and maintenance health.
- [ ] Select a pinned platform baseline only after the above evidence.

**Exit:** reproducible build plan and credible recovery path. No flashing before this gate.

## M2 — Cloud source and build pipeline
- [ ] Define pinned Repo manifest.
- [ ] Provision a suitable cloud build host with adequate RAM, storage, and build time.
- [ ] Implement source sync, cache strategy, build logs, artifact retention, and provenance.
- [ ] Build an unmodified baseline before applying MOMO patches.
- [ ] Preserve checksums and source revisions.

**Exit:** repeatable baseline build with documented limitations.

## M3 — MOMO platform shell and services
- [ ] Prototype launcher and mobile shell.
- [ ] Define permission broker and narrow system APIs.
- [ ] Build task/activity history and user-visible automation controls.
- [ ] Prototype desktop/workstation mode where hardware supports it.

**Exit:** usable shell prototype and reviewed privilege model.

## M4 — MOMO Multi-Agent Intelligence
- [ ] Specify agent/tool protocol and typed schemas.
- [ ] Implement planner, orchestrator, specialist registry, and model router.
- [ ] Add memory controls, provenance, retention, and deletion behavior.
- [ ] Add evaluator, sandboxed tool execution, budget and cancellation.
- [ ] Build benchmark tasks and adversarial tests.

**Exit:** measured task performance with safe, auditable execution.

## M5 — Integration, hardening, and device validation
- [ ] Integrate services with Android permission and SELinux policy.
- [ ] Run functional, regression, privacy, and security tests.
- [ ] Validate battery, thermal, radio, camera, audio, sensors, biometrics, and OTA.
- [ ] Test restore and rollback paths.
- [ ] Conduct independent review before any public release.

**Exit:** release candidate with explicit device and feature support matrix.

## M6 — Release
- [ ] Publish reproducible build instructions and source manifests.
- [ ] Publish checksums, SBOM, licenses, notices, and security contact.
- [ ] Sign artifacts with protected keys.
- [ ] Provide installation and recovery instructions only for verified devices.
