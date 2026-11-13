# Roadmap

Milestones are gated by evidence and acceptance criteria, not calendar promises.

## M0 — Repository and governance foundation
- [x] Establish cloud-first, upstream-aware repository strategy.
- [x] Document architecture, security, licensing, and device feasibility gates.
- [x] Specify AI runtime, capability broker, desktop experience, cloud pipeline, and test strategy.
- [x] Add provider-neutral task state machine and permission-policy core with unit tests.
- [x] Add JSON contracts for tasks and capability grants.
- [ ] Add maintainers, issue templates, and contribution guidance.
- [ ] Inventory upstream candidates and exact licenses.

**Exit:** repository policy and initial runtime contracts are in place; no unverified device or build claims. Remaining: dependency/license inventory and maintainer governance.

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
- [x] Specify initial typed task and capability schemas.
- [x] Implement deterministic plan validation, agent capability registry, and dependency-aware scheduling.
- [x] Implement initial privacy-aware provider profile selection with local-only handling for sensitive/restricted data.
- [ ] Implement model-backed planning, real agent execution, specialist delegation, and provider SDK adapters.
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

## Current engineering blockers

- **Device:** exact firmware/CSC, bootloader unlock status, matching Samsung kernel source, device tree, vendor files, partition/AVB layout, and restore route are not yet verified.
- **Cloud:** no build worker or cloud budget has been provisioned. Standard GitHub-hosted runners are not assumed sufficient for full AOSP.
- **AI providers:** no provider credentials or local inference runtime has been configured. The core currently contains policy/state logic only, not an LLM integration.
- **Android integration:** no privileged system service, launcher, desktop shell, or device image has been built.

These are explicit blockers, not completed tasks.