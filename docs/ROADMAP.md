# MOMO OS — End-to-End Roadmap

Roadmap stages are evidence-gated. Dates are not promised until build capacity, device access, platform baselines and maintainers are confirmed.

## Current stage — Experimental Linux bring-up
Build the x86_64 Buildroot image and prove it boots under QEMU. This is a development target, not a mobile ROM.

## Stage 0 — Governance and product baseline
- [x] Repository and cloud-first development strategy.
- [x] Initial architecture, security, device compatibility, AI runtime and licensing documents.
- [x] Initial task state machine, task journal, device inventory and persistent permission broker.
- [x] Initial Task Coordinator with immutable plan binding and scoped permission checks.
- [ ] Complete SRS, product overview, master plan and evidence-based roadmap.
- [ ] Dependency/license inventory, contribution governance and security reporting process.
**Exit:** product scope and governance approved; claims mapped to evidence.

## Stage 1 — First bootable target (critical path)
- [x] Buildroot x86_64 configuration and MOMO rootfs overlay.
- [x] CI workflow for kernel/rootfs build, QEMU serial boot, readiness check and artifact upload.
- [ ] Successful kernel/rootfs build on latest commit.
- [ ] Verify image output and artifact integrity.
- [ ] QEMU boot reaches MOMO OS READY.
- [ ] Run momoctl doctor, task self-test, device inventory and permission checks in target.
- [ ] Inspect boot log, checksums and provenance.
- [ ] Merge bootable image PR into main only after all gates pass.
**Exit:** reproducible QEMU-validated image with retained evidence.

## Stage 2 — Runtime and service contracts
- [x] Task state machine and durable event journal.
- [x] Plan validation, agent registry and dependency-aware scheduling.
- [x] Initial Task Coordinator, persistent permission integration and immutable plan digest.
- [ ] Complete cancellation, deadline, idempotency, retries and crash recovery.
- [ ] Define versioned contracts for device, permissions, tasks, storage, apps, notifications, power, update and audit.
- [ ] Add IPC identity, structured errors, health checks and migration tests.
**Exit:** durable service layer with negative authorization and restart tests.

## Stage 3 — OS-enforced security
- [ ] Linux service identities, namespaces, seccomp/LSM policy and sandbox profiles.
- [ ] Android Binder/AIDL, SELinux, AppOps and signature-level enforcement.
- [ ] Secure secret storage, audit redaction and retention/deletion policy.
- [ ] Adversarial tests: prompt injection, confused deputy, replay, path traversal and privilege escalation.
- [ ] Independent security review.
**Exit:** unauthorized actions rejected by native OS boundaries, not only app-level policy.

## Stage 4 — Platform selection and reproducible upstream builds
- [ ] Evaluate and pin Android-compatible base and API baseline.
- [ ] Evaluate mainline-Linux userspace, shell/compositor, package and update strategy.
- [ ] Build unmodified platform baselines before MOMO patches.
- [ ] Record source manifests, licenses, firmware provenance, toolchain and SBOM.
**Exit:** two documented, reproducible platform tracks with selected baselines.

## Stage 5 — First exact-device port
- [ ] Select first device by source availability, unlock/recovery and test access.
- [ ] Confirm exact SKU, codename, region, boot chain, partitions, AVB, kernel and vendor dependencies.
- [ ] Build and boot without risking the only device.
- [ ] Validate display, touch, storage, charging, thermal, radios, audio, camera, sensors, biometrics and encryption.
- [ ] Test OTA, rollback, restore and data preservation.
**Exit:** at least Tier 2 boot-tested; Tier 3 required for daily-use candidate.

## Stage 6 — MOMO mobile and desktop experience
- [ ] Launcher/shell, navigation, quick settings, notifications and settings.
- [ ] Permissions dashboard, task/activity history and approval UX.
- [ ] Arabic RTL and English LTR localization.
- [ ] Screen reader, scalable UI, contrast and alternative input.
- [ ] Desktop/convergence mode on qualified hardware.
**Exit:** coherent shell usable without AI and with understandable automation controls.

## Stage 7 — Core services
- [ ] Storage Broker and scoped file access.
- [ ] App Broker and lifecycle integration.
- [ ] Notification Broker.
- [ ] Network/connectivity abstraction.
- [ ] Power and Thermal service.
- [ ] Audit/diagnostics service.
- [ ] Update and Recovery Manager.
**Exit:** P0/P1 services pass contract, integration, restart and permission tests on target platform.

## Stage 8 — AI assistant and multi-agent execution
- [ ] Model provider adapters and user-configured credentials.
- [ ] Local model runtime discovery and cloud routing policy.
- [ ] Planner, agent execution, tool gateway and sandbox adapters.
- [ ] User-controlled memory, provenance, retention and deletion.
- [ ] Approval UX, cancellation, budgets, rate limits and outcome verification.
- [ ] Benchmark and adversarial safety suite.
**Exit:** measured task completion with no critical safety bypass.

## Stage 9 — Applications and ecosystem
- [ ] Essential first-party apps and settings.
- [ ] Android compatibility validation on Android track.
- [ ] Native Linux app/package strategy on Linux track.
- [ ] Stable service SDK/contracts and sample integrations.
**Exit:** minimum app set works on qualified targets with permission conformance.

## Stage 10 — Release engineering
- [ ] Protected artifact signing and key custody.
- [ ] SBOM, checksums, source provenance and license notices.
- [ ] Staged updates, health checks, rollback and recovery.
- [ ] Release channels, support lifecycle, security response and installation guides.
**Exit:** signed reproducible release candidate passes full qualification.

## Stage 11 — Multi-device expansion and maintenance
- [ ] Port a second distinct device family.
- [ ] Cross-device conformance and regression automation.
- [ ] Kernel/security update process and upstream synchronization.
- [ ] Public support matrix and end-of-life policy.
**Exit:** at least two device families have evidence-backed support tiers and active maintenance.

## Current blockers
- Latest QEMU image build is pending; no successful image boot is claimed.
- No Android/AOSP build or Android phone image is validated.
- No physical device is certified.
- No OS-enforced MOMO tool sandbox or full tool execution adapter exists yet.
- No final Android base, first phone SKU, cloud build host or release signing infrastructure is selected.

## Progress Evidence Update — 2026-11-13

The Runtime and Service Contracts stage has a new tested sub-milestone: a durable per-step execution journal. It records step attempts and events, bounds retries to R0/R1 read-only work, and quarantines side-effecting failures and restart-interrupted work as `needs_review`. Cooperative cancellation requires executor confirmation that no side effect occurred. The repository validation workflow passed with 96 unit tests.

This does **not** complete Stage 2 or Stage 3. The journal is integrated with TaskCoordinator and mirrored into the Buildroot rootfs overlay; accepted plan steps are persisted atomically with their task and immutable plan. The target image has not yet been rebuilt with the coordinator and startup-recovery changes or validated in QEMU. There is no actual tool executor, authenticated IPC, native OS sandbox, deadline/backoff scheduler, concurrency manager or outcome reconciler. The Stage 2/3 exit criteria remain open.

### Runtime scheduling progress — 2026-11-13

A tested dependency-readiness foundation is now integrated: TaskCoordinator trusts only persisted `succeeded` step records, returns only journal entries in `ready` state, and blocks descendants of failed or ambiguous steps. Callers cannot forge completion by supplying an in-memory set. The change is mirrored into the Buildroot overlay and covered by the repository validation suite (105 tests).

The Runtime and Service Contracts stage remains open: there is no worker scheduler, actual executor, deadline/backoff service, concurrency/fairness/resource quotas, independent outcome verifier or OS-enforced sandbox.

### Audit integrity progress — 2026-11-13

The per-step event ledger now has a verified SHA-256 hash chain, update/delete protection through SQLite triggers and a migration path for legacy event rows. The repository suite covers mutation attempts and tamper detection. This is an integrity foundation only; it is not a signed or externally anchored audit log and does not replace native storage protection.
