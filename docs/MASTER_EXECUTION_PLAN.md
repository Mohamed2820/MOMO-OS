# MOMO OS — Master Execution Plan

**Purpose:** authoritative implementation sequence from the current repository state to a maintained release.  
**Planning rule:** no calendar estimate is a promise. Every phase has dependencies, deliverables, verification and an exit gate.  
**Development mode:** cloud-first GitHub workflow; no requirement to clone or build the full OS on the maintainer's phone.

## 1. Execution principles

1. Evidence before claims: specified → implemented → CI-tested → image-integrated → emulator-tested → exact-hardware-tested → release-qualified.
2. Upstream first: reuse maintained kernels, frameworks, boot chains, service managers and runtimes.
3. Two platform tracks: Android-compatible and mainline Linux share MOMO contracts, not a common kernel.
4. Device-by-device validation: each SKU requires boot, recovery, firmware and feature evidence.
5. Security before autonomy: no model or agent can grant itself permissions.
6. Small vertical slices: build and test each subsystem before adding the next dependency.
7. Reproducibility: pin source/toolchains, retain logs and hashes, generate SBOM and provenance.
8. Fail safely: optional AI failure must not block boot, recovery or essential OS functions.
9. No blind flashing: no installation before a verified stock restore/recovery path.
10. Release by evidence, not roadmap dates.

## 2. Workstreams

| Workstream | Scope | Outputs |
|---|---|---|
| WS-A Platform engineering | Linux/Android bases, kernels, boot, HAL/adapters | Bootable targets and device ports |
| WS-B Shared runtime | Contracts and core services | Versioned service APIs |
| WS-C Security | Identity, permissions, sandbox, secrets, audit | Enforcement and security evidence |
| WS-D Intelligence | Models, agents, tools, memory, planning, evaluation | Safe assistant runtime |
| WS-E Experience | Mobile shell, settings, accessibility, desktop | User-facing product |
| WS-F Build/release | Manifests, cloud workers, CI, signing, OTA | Reproducible signed releases |
| WS-G QA/device lab | Emulator, hardware, regression and recovery | Compatibility matrix |
| WS-H Governance | Licensing, documentation, contribution, security response | Maintained project |

## 3. Phases

### Phase 0 — Governance and baseline
**Goal:** make the repository a reliable engineering source of truth.
- Freeze product definition, non-goals, platform tracks and evidence terminology.
- Establish branch/PR rules, code review checklist and ownership.
- Add issue templates for features, bugs, device ports, security and documentation.
- Inventory upstream dependencies, pinned revisions, licenses and patches.
- Automate Markdown/link, YAML/JSON, secret, license and manifest checks.
- Publish threat model, contribution guide, vulnerability contact and release policy.
**Deliverables:** product overview, SRS, architecture, ADRs, dependency inventory and governance.
**Exit:** repository is reproducible and legal/security boundaries are clear.

### Phase 1 — First executable Linux target (current critical path)
**Goal:** build and boot a real MOMO-integrated Linux system in QEMU.
1. Build pinned Buildroot baseline using x86_64 QEMU configuration.
2. Build kernel and root filesystem with MOMO overlay.
3. Verify image artifacts, filesystem, startup and Python/SQLite modules.
4. Boot under QEMU with serial logging.
5. Verify readiness marker and run momoctl doctor, task self-test, device inventory and permission checks.
6. Inspect boot logs, hashes, provenance and uploaded artifacts.
7. Fix failures in isolated PRs and rerun.
8. Merge bootable target into main only after acceptance evidence.
**Deliverables:** reproducible QEMU image, boot log, hashes, provenance and test report.
**Exit:** QEMU-validated x86_64 image. This is not phone support.

### Phase 2 — Runtime foundations and service contracts
**Goal:** turn isolated modules into reliable services.
- Freeze versioned contracts for device, permissions, tasks, storage, apps, notifications, audit and updates.
- Complete Task Coordinator: idempotency, dependencies, cancellation, deadlines, retries, crash recovery and reconciliation.
- Implement narrow tool gateway and adapter registry; no arbitrary shell interface.
- Add structured errors, correlation IDs, bounded payloads and health endpoints.
- Add database migration/versioning strategy.
- Add service lifecycle/watchdog without making optional services boot-critical.
- Define authenticated IPC and per-service identities.
**Verification:** contract, restart/crash, concurrency and permission-bypass tests.
**Exit:** service layer persists, authorizes and recovers tasks without unauthorized side effects.

### Phase 3 — Security enforcement and sandboxing
**Goal:** move beyond policy-only logic to OS-enforced isolation.
- Threat-model every service, agent, tool, IPC channel, provider and update path.
- Define principals, capability scopes, expiry, revocation and replay defense.
- Android: integrate permissions, AppOps, SELinux and signature permissions.
- Linux: integrate users/groups, namespaces, seccomp, LSM, portals and service sandboxing.
- Use Android Keystore or OS/hardware-backed secret storage where available.
- Redact logs; define retention/deletion for tasks, audit and memory.
- Test prompt injection, confused deputy, path traversal, symlinks, replay, races and privilege escalation.
- Establish vulnerability response and security release process.
**Exit:** independent review finds no unresolved critical/high issue in release scope.

### Phase 4 — Platform base selection and upstream integration
**Android:** compare AOSP, LineageOS and viable maintained bases; select API baseline, kernel strategy, update branch and build manifest; build unmodified baseline; add MOMO overlays incrementally without weakening AVB, SELinux or verified boot.
**Linux:** select mainline-friendly hardware and userspace; decide init, compositor/shell, display stack, portals, package/runtime and update model; preserve kernel/firmware provenance.
**Exit:** each track has a selected maintainable base and reproducible build.

### Phase 5 — Exact-device porting and hardware enablement
- Select first device based on source availability, unlock/recovery, maintainer access and testability.
- Confirm exact SKU, board/codename, region, firmware and stock restore package.
- Map partitions, slots, AVB/vbmeta, rollback indices, boot format and recovery.
- Integrate kernel, device tree, HAL, vendor components and firmware with license records.
- Build baseline, boot reversibly and capture logs.
- Validate display, touch, GPU, storage, charging, thermal, suspend/resume, modem, emergency-call constraints, Wi-Fi, Bluetooth, audio, camera, GPS, NFC, biometrics and encryption.
- Test update, rollback, recovery and data preservation.
**Exit:** Tier 2 boot-tested minimum; Tier 3 required for daily-use candidate.

### Phase 6 — Core user experience
- Design launcher, shell, navigation, app switcher, notification shade and settings.
- Implement permissions dashboard, quick controls and capability UI.
- Add accessibility, Arabic RTL and English LTR.
- Add activity history and clear automation progress/cancel surfaces.
- Add desktop mode only where display/compositor/input support is proven.
- Define crash isolation and safe mode.
**Exit:** usable shell that works without AI and gives users control over automation.

### Phase 7 — Core services
Implement in sequence: Storage Broker; App Broker; Notification Broker; network abstraction; Power/Thermal; Audit/Diagnostics; Update/Recovery.
For each: contract → reference adapter → unit tests → integration tests → sandbox policy → UI → hardware tests.
**Exit:** P0/P1 services pass contract, integration, restart and permission tests on target platform.

### Phase 8 — AI assistant and multi-agent execution
- Add provider adapters and user-configured credentials; never hardcode keys.
- Add local model discovery and capability-based selection.
- Implement intent intake, clarification, planner, scheduler, agents and memory.
- Implement typed tool registry, risk levels and sandboxed adapters.
- Enforce permissions/approvals before tool execution.
- Add idempotency, deadlines, cancellation, retries, budgets and rate limits.
- Verify outcomes independently and report partial/failed results honestly.
- Add prompt-injection and cross-agent isolation tests.
- Build evaluation set for system tasks, device control, files, privacy, safety, cost and latency.
- Add offline fallback and transparent cloud data handling.
**Exit:** measured task performance with no critical safety bypass.

### Phase 9 — Applications and ecosystem
- Define Android compatibility policy for Android track.
- Define Linux application/package runtime for Linux track.
- Build/integrate essential apps: files, settings, terminal/developer tools, media, browser and app manager as feasible.
- Publish stable MOMO service SDK/contracts and sample apps.
- Establish app signing and permission review.
**Exit:** minimum essential app suite passes on supported devices.

### Phase 10 — Updates, distribution and operations
- Define development, nightly, beta, release-candidate and stable channels.
- Sign artifacts with protected keys; never store keys in Git or plain CI variables.
- Generate SBOM, checksums, provenance, license notices and release manifest.
- Implement staged rollout, health checks, rollback and recovery.
- Publish installation instructions only for qualified exact devices.
- Define opt-in telemetry, crash-report redaction, support lifecycle and vulnerability response.
**Exit:** signed reproducible release candidate passes full qualification.

### Phase 11 — Multi-device expansion and maintenance
- Port a second distinct device family.
- Add device-family CI and hardware lab where possible.
- Maintain kernel/security updates and upstream synchronization.
- Track regressions, battery/thermal behavior and features per SKU.
- Retire ports that cannot be safely maintained.
**Exit:** two or more distinct families meet declared support tiers and maintenance obligations.

## 4. Critical path

Governance → QEMU proof → service contracts/security enforcement → platform base selection → exact device feasibility → platform/device port → core UX/services → AI execution → applications → signed updates/recovery → release qualification → multi-device expansion.

Parallel documentation and UI prototyping are allowed. Physical flashing cannot precede recovery proof. Release signing cannot precede key custody and provenance design.

## 5. Definition of Done for every PR

- Requirement or issue linked.
- Scope and non-goals explicit.
- Source and documentation updated together.
- Unit and relevant integration tests added.
- Security impact and privilege changes reviewed.
- No secrets or unlicensed blobs introduced.
- CI green; logs/artifacts retained when relevant.
- Rollback/migration behavior considered.
- Status claims use the correct evidence level.
- Required review completed before merge.

## 6. Project release gates

| Gate | Required evidence | Block if |
|---|---|---|
| G0 Product baseline | SRS, architecture, threat model, governance | Scope ambiguous |
| G1 QEMU bring-up | Reproducible image, boot log, runtime checks | Build/boot fails |
| G2 Runtime core | Contracts, durable state, cancellation, authorization | Policy bypass/corrupt state |
| G3 Platform baseline | Pinned source and reproducible upstream build | Unknown provenance/license |
| G4 Device feasibility | Exact SKU, unlock, restore, partition and kernel facts | No safe recovery |
| G5 Device boot | Physical boot, logs, display/touch, recovery | Unstable/unverified boot |
| G6 Daily-use | Radios, media, sensors, power, encryption, OTA | Critical hardware missing |
| G7 Security | OS enforcement, adversarial tests, independent review | Critical/high issue open |
| G8 Release | Signing, SBOM, provenance, rollback, docs | Signature/recovery failure |
| G9 Multi-device | Second family passes conformance | Only one family validated |

## 7. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Vendor sources/firmware unavailable | Device port blocked | Select by source and recovery evidence |
| Bootloader locked/no restore | Data loss or device damage | Hard stop; no blind flashing |
| Build exceeds hosted runner limits | Slow/failed CI | Provision suitable cloud builder/cache |
| Upstream churn | Maintenance burden | Pin revisions and controlled patch queue |
| Android/Linux API divergence | Adapter duplication | Stable MOMO contracts and per-track adapters |
| Prompt injection/confused deputy | Data exposure/unauthorized action | Typed tools, OS sandbox, explicit approval |
| Local model too large | Poor performance/battery | Capability profiles and optional cloud routing |
| OTA/partition mismatch | Unbootable device | Per-device update/recovery qualification |
| Proprietary license unclear | Legal/release risk | Provenance/license gate |
| Single-maintainer capacity | Project stagnation | Automation, small milestones, contributor docs |

## 8. Immediate next actions

1. Complete latest Buildroot/QEMU workflow and inspect artifacts and serial log.
2. If it passes, merge bootable target PR into main; if it fails, fix the exact failing step and rerun.
3. Merge documentation baseline after repository validation.
4. Complete Task Coordinator execution lifecycle and security enforcement tests.
5. Implement service contracts and Linux adapter integration.
6. Select the first phone target only after device feasibility research.

No fixed delivery date is promised until build capacity, device access, maintainers and platform baseline are confirmed.

## Execution Progress Record — 2026-11-13

### Completed sub-milestone: durable per-step execution journal

- Added a SQLite-backed per-step ledger and append-only event history.
- Added attempt counters, stable unique idempotency keys and bounded R0/R1-only retry budgets.
- Quarantined R2-R4 failures and all restart-interrupted executions as `needs_review`; no automatic replay is permitted.
- Added cooperative cancellation semantics that distinguish a request from confirmed safe cancellation.
- Added result SHA-256 persistence and repository tests.
- Repository validation passed, including full unittest discovery (96 tests).

### Explicitly not complete

The journal is integrated into TaskCoordinator: accepted plan steps are registered in the same SQLite transaction as the parent task, immutable plan and task events. The journal and coordinator are mirrored into the Buildroot rootfs overlay, with source/overlay parity tests. The target image has not yet been rebuilt with the coordinator integration and startup recovery hook or validated in QEMU. No tool execution adapter, authenticated IPC, native OS sandbox, deadline scheduler, backoff service, concurrency/resource budget manager or outcome reconciler has been delivered.

### Next execution sequence

1. Keep the x86_64 Buildroot/QEMU acceptance gate independent and do not merge its image PR until the image, boot log and runtime evidence are verified.
2. Validate the boot-time recovery hook in the rebuilt QEMU image, including first boot and repeated recovery invocation; before concurrent workers exist, preserve the guarantee that old workers are stopped before recovery.
3. Add durable dependency-completion records and scheduler deadlines, backoff, concurrency limits and resource budgets.
4. Design the executor boundary with fresh permission authorization, OS identity, idempotency propagation, cancellation and independent result verification; do not dispatch tools yet.
5. Implement native OS isolation and IPC identity, then add adversarial tests before enabling any privileged tool.
