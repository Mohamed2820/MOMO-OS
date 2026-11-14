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

The journal is integrated into TaskCoordinator: accepted plan steps are registered in the same SQLite transaction as the parent task, immutable plan and task events. The journal and coordinator are mirrored into the Buildroot rootfs overlay, with source/overlay parity tests. The target image has not yet been rebuilt with the coordinator integration and startup recovery hook or validated in QEMU. No tool execution adapter, authenticated user/session identity, native OS sandbox, deadline scheduler, backoff service, concurrency/resource budget manager or outcome reconciler has been delivered.

### Next execution sequence

1. Keep the x86_64 Buildroot/QEMU acceptance gate independent and do not merge its image PR until the image, boot log and runtime evidence are verified.
2. Validate the boot-time recovery hook in the rebuilt QEMU image, including first boot and repeated recovery invocation; before concurrent workers exist, preserve the guarantee that old workers are stopped before recovery.
3. Add durable dependency-completion records and scheduler deadlines, backoff, concurrency limits and resource budgets.
4. Design the executor boundary with fresh permission authorization, OS identity, idempotency propagation, cancellation and independent result verification; do not dispatch tools yet.
5. Implement native OS isolation and IPC identity, then add adversarial tests before enabling any privileged tool.

### Completed sub-milestone: durable dependency readiness

- Removed caller-controlled completion claims from TaskCoordinator's readiness API.
- Derived completed dependencies only from persisted `succeeded` step records.
- Restricted returned work to steps in durable `ready` state.
- Blocked downstream work after failed, cancelled, running or `needs_review` dependencies.
- Verified exact plan-to-journal step identity and risk consistency.
- Repository validation passed with 105 unit tests.

This closes the persisted dependency-readiness foundation only. It does not deliver worker scheduling, concurrency control, deadlines, backoff, fairness, quotas, executor dispatch or result verification.

### Completed sub-milestone: tamper-evident step event history

- Added a per-task-step SHA-256 event hash chain.
- Verify event integrity before returning event history.
- Block ordinary event updates and deletions through SQLite triggers.
- Backfill older pre-hash event rows during schema migration.
- Test normal verification, mutation rejection, trigger-bypass tampering and legacy migration.
- Repository validation passed with 111 unit tests, including fail-closed state-read and scheduler tests.

This is not a signed audit log and does not resist a privileged attacker who can rewrite the database and recompute hashes. External anchoring and protected storage remain open.


## Execution Progress — Versioned Linux IPC Framing (2026-11-13)

Added a version-1 bounded request frame codec: 4-byte network-order length prefix, 64 KiB maximum, strict UTF-8/JSON parsing, duplicate-key rejection, finite-number enforcement, exact top-level schema, request-ID and operation-name validation, and socket stream helpers. Added unit tests and Buildroot source/overlay parity checks.

The parser is transport hygiene only. Peer authentication, UID-to-role mapping, per-operation authorization, deadlines, replay controls, resource quotas, daemon integration and native process sandboxing remain outstanding. No privileged IPC service or tool executor is exposed. PR review and CI are required before this milestone is accepted.

## Milestone — First Unprivileged IPC Service (PR #38 candidate, 2026-11-13)

Implemented a narrow daemon/client path on top of the peer-credential primitive and bounded protocol. Buildroot provisions `momo-ipc`; init starts `momo-ipcd` under that account; the daemon checks kernel peer credentials before parsing; it dispatches only `status.read`; the socket path is protected against unsafe replacement; connection timeouts and backlog are bounded; and `momoctl ipc-status` queries the service. The service has no execution adapter.

Required acceptance: green repository CI, successful Buildroot image build, QEMU boot reaching MOMO OS READY, and an in-guest authenticated status request. Next hardening gates are replay protection, strict operation-specific schemas, service role/capability policy, seccomp/namespaces/LSM/cgroups, and adversarial denial tests. Do not enable tool execution before those gates.


## IPC Hardening Increment — Bounded Replay Detection (PR #39 candidate)

Added a lock-protected bounded 1,024-entry request-ID cache, duplicate rejection before dispatch, UUID request IDs in the CLI, and strict client response-shape validation. The cache is volatile and resets on daemon restart. Do not use it as the idempotency authority for mutating tools; durable task/step journal keys and reconciliation remain required.


## IPC Process Hardening — Resource Limits and No-New-Privileges (PR #40 candidate)

Added startup restrictions for core dumps, file size, open descriptors and address space, plus Linux `PR_SET_NO_NEW_PRIVS`. A subprocess test verifies limits and kernel state. A cumulative CPU-time hard limit is intentionally omitted to avoid killing a healthy long-lived service. This is not a complete sandbox: syscall allowlisting via seccomp, namespace isolation, cgroup limits and LSM policy remain outstanding.


## IPC Syscall Restriction — libseccomp denylist (PR #41 candidate)

Added a required libseccomp runtime dependency and a default-allow syscall denylist installed after socket setup. Dangerous process creation/exec, ptrace, mount/namespace, reboot/kexec, BPF/keyctl/perf, io_uring, userfaultfd and cross-process memory syscalls are denied. CI tests that process creation fails with EPERM. Filter installation is fail-closed. This remains defense in depth, not a strict syscall allowlist; namespace, cgroup and LSM isolation are still required.


## Platform Expansion — AArch64 QEMU target (PR #42 candidate)

Added a separate AArch64 Buildroot/QEMU workflow with pinned Buildroot verification, overlay and user-table configuration, libseccomp, cached toolchain/package outputs, image checks, QEMU serial boot and IPC status evidence. Merge/acceptance is gated on workflow success. Physical ARM devices require their own boot chain, kernel, device tree, firmware, drivers and validation.


## Historical Image Evidence and Current Gate (2026-11-13)

The initial x86_64 Buildroot baseline passed build, output verification and QEMU boot on commit `74398b8d8ab9e379e94a864d35bb9a6db3623d83`, reaching `MOMO OS READY` ([run #43437714431](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43437714431), artifact `14046724553`). The later revision integrating Step Journal/TaskCoordinator is a distinct image and remains pending in [run #43446234529](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43446234529). The earlier artifact is not acceptance evidence for the later commit.


## Current Integrated Baseline — 2026-11-13

PR #42 has been merged into the bootable development branch. It integrates the status-only authenticated AF_UNIX daemon, bounded IPC protocol, process-lifetime replay cache, process limits, `PR_SET_NO_NEW_PRIVS`, libseccomp default-allow denylist and an AArch64 QEMU build/boot workflow. The daemon runs under the dedicated `momo-ipc` account and accepts only root-owned local status requests. No tool executor is present or enabled.

Integrated commit: `a7a4caf381553d9a697b68a093eff9520d8b0bda`.

Current acceptance runs:
- x86_64 image: [run #43454224817](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224817) — build in progress at last inspection.
- AArch64 image: [run #43454224951](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224951) — build in progress at last inspection.

Do not merge further changes to the bootable branch while these image workflows are running. Once complete, inspect kernel/rootfs outputs, QEMU serial logs, IPC status response and uploaded artifacts independently for each architecture. Green repository-validation is not a substitute for either image test.

Remaining gates: resolve image/boot failures; adversarial IPC/seccomp tests; explicit operation/capability authorization; namespace and cgroup isolation plus LSM policy; durable side-effect idempotency and recovery; only then a non-privileged executor adapter. Android remains a separate AOSP/Binder-AIDL/SELinux/AppOps track, followed by per-device bootloader/kernel/DTB/firmware/driver validation.


## Execution Progress Record — 2026-11-14: plan-bound execution and Linux IPC

### Delivered in the integration candidate
- Integrated the durable per-step journal with TaskCoordinator and the Buildroot rootfs overlay.
- Added plan-bound task/step start enforcement, single-use expiring approval tokens, argument/plan binding, replay and concurrency regression tests.
- Added Linux AF_UNIX framing, kernel-derived peer credentials and a read-only IPC status daemon under a dedicated unprivileged service account.
- Added process limits, `no_new_privs` and a required libseccomp denylist for the status daemon.
- Added x86_64 and AArch64 Buildroot/QEMU workflow definitions and refreshed the SRS, roadmap, support matrix and engineering specifications.
- Added execution runtime, service API, Linux sandbox and Android integration design documents.

### Canonical validation
Integration PR #48 passed repository validation on its current initial head: 167 unit tests, documentation/JSON validation, device-profile schema validation and shell utility checks (run [#43597582878](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597582878)). The PR remains an integration candidate until its latest head is revalidated after documentation/workflow additions.

### Evidence not yet achieved
- Fresh x86_64 QEMU build and boot for the execution gate + IPC daemon revision.
- Fresh AArch64 QEMU build and boot for the same revision.
- Production Linux namespaces/cgroups/LSM policy and strict per-service seccomp allowlists.
- Authenticated human/session identity; the approval issuer still accepts a caller-asserted approver label.
- Operation-specific argument schemas, a typed executor, and outcome reconciliation; canonical argument digests are now derived internally from strict JSON, but no tools are dispatched.
- Production Linux namespaces/cgroups/LSM enforcement and strict per-service sandbox policies.
- Android AOSP baseline, Binder/AIDL services, SELinux/AppOps integration and physical device port.

### Next critical path
1. Re-run repository validation on the latest PR #48 head.
2. Build and boot the x86_64 and AArch64 QEMU images; inspect serial logs and artifacts.
3. Fix all build/boot failures before promoting the integration.
4. Close the remaining execution trust gaps: authenticated human/session identity, operation-specific schema validation, typed executor boundary, native OS isolation, and independent outcome reconciliation. Canonical argument digest computation is now performed by the public gate from exact JSON input, but remains source-level until CI/QEMU evidence is recorded.
5. Add native Linux service isolation and split authority-bearing databases behind service APIs.
6. Implement one non-destructive typed reference adapter, then test timeout, cancellation, idempotency and ambiguous outcomes.
7. Only then progress to Android platform selection and device feasibility.


## Section 1 continuation — canonical argument authorization

The public step-approval API now requires the raw bounded JSON argument payload and computes the canonical digest internally. The public gate step-start API also requires raw JSON, independently computes the digest, and exposes a deeply immutable parsed argument structure for a future executor. Caller-supplied digests are rejected at the public approval/start APIs. Source modules are mirrored byte-for-byte into the Buildroot rootfs. Focused parser, gate, approval and immutability tests are present, but a fresh CI run on the latest PR #48 head is still required.

The earlier AArch64 QEMU run [#43598435820](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435820) completed build, image verification, QEMU readiness, provenance and artifact upload on older commit `eac08aedb9a5e5fc0c4a87eaf1a973bf525242ab`. The AArch64 run [#43598435820](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435820) completed image verification, QEMU readiness, provenance and artifact upload on that older commit. The x86_64 run [#43598435846](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435846) remains in kernel/rootfs compilation on the same older commit. Neither is acceptance evidence for the latest PR head.


## Typed read-only execution increment — 2026-11-14

A narrow typed executor is now implemented in `intelligence/runtime/typed_executor.py` and mirrored byte-for-byte into the Buildroot rootfs. The registry only accepts R0/R1 operation specs. Its first operation, `system.status.read`, has an exact empty-object argument schema, requires the matching planned domain/capability/risk, enters through the argument-bound ExecutionGate, executes a fixed in-process read-only handler, hashes the returned JSON object and records the result in the durable step journal. No request can supply a shell command or handler.

Focused tests now cover success, unknown-operation denial, schema mismatch, plan mismatch, high-risk registration rejection, immutable result data and adapter failure recording. The CI workflow now includes the typed executor in source/rootfs compile checks and parity tests, and integration branches are included in the repository-validation push filter. This source increment still needs a fresh successful CI run. It is not a side-effecting executor and does not solve authenticated human identity, deadlines/cancellation, durable side-effect idempotency, OS sandboxing or outcome reconciliation.


## Kernel isolation prerequisites — 2026-11-14

Added `board/momo/kernel-security.fragment` to request namespaces, cgroups and resource controllers, seccomp filtering and Landlock. Both x86_64 and AArch64 Buildroot workflows now apply this fragment and verify the generated kernel configuration with `tools/validate_kernel_security_config.py`. Unit tests cover the validator. This is a prerequisite, not a completed sandbox: per-service namespace entry, cgroup assignment, Landlock rules, network/filesystem policy and adversarial tests remain open until the images pass.


## Landlock filesystem boundary for IPC status service — 2026-11-14

The unprivileged read-only IPC daemon now applies Landlock after binding its socket and loading seccomp. It can read/execute from `/usr`, read from `/etc`, and inspect/remove its own socket under `/run/momo`; other handled filesystem access is denied. The setup is fail-closed. A subprocess test checks allowed reads, denied reads outside the allowlist and denied writes.

This is a real filesystem restriction for the status daemon, not a complete MOMO sandbox. Per-service namespaces, cgroups, network isolation, a strict syscall allowlist, authenticated principal mapping and security enforcement for future task/executor services remain open. The Landlock code and test require fresh CI and QEMU boot evidence before promotion.


## IPC status-service namespace and cgroup profile — 2026-11-14

Added `momo-ipc-sandbox`, a root-started launcher that moves the daemon into a dedicated cgroup before dropping privileges, creates private mount/IPC/UTS/network namespaces, makes mount propagation private, clears supplementary groups, drops to the dedicated `momo-ipc` UID/GID and sets `no_new_privs`. Init script `S98momo-ipc` now requires cgroup v2 CPU/memory/PID controllers and sets a 50% CPU quota, 128 MiB memory limit and 16-process limit. The daemon then applies its existing seccomp denylist and Landlock filesystem boundary.

This is a per-service sandbox profile for the read-only status daemon only. PID/user namespaces, task/executor service isolation, authenticated human/session identity, a strict syscall allowlist, network firewall policy, and adversarial QEMU tests remain open. The wrapper/init changes have not yet passed a fresh CI/QEMU run; do not mark the sandbox gate complete until they do.


## Section 1 of the four remaining implementation sections — execution authorization foundation

### Scope and implementation result
- [x] D1: block the CLI transition command from entering `EXECUTING`; execution must use the gate.
- [x] D2: block direct low-level step starts for plan-bound tasks and reject step records not present in the accepted plan.
- [x] D3: replace caller-constructed approval objects with server-issued, random, expiring, single-use tokens stored by hash.
- [x] D4: bind approvals to task/step, operation/domain, risk, immutable plan digest and exact canonical argument digest; reject mismatch, expiry, replay and concurrent double-consumption.
- [x] Derive argument digests from bounded strict JSON inside the public approval/start APIs; return deeply immutable authorized arguments.
- [x] Add focused negative, replay, expiry, concurrency, rollback, tamper and rootfs-parity tests.
- [x] Add a typed R0/R1 read-only reference executor limited to the fixed `system.status.read` operation; keep IPC tool dispatch disabled.
- [x] Add Linux status-daemon namespace/cgroup/seccomp/Landlock setup and QEMU assertions.
- [x] Latest repository validation passed 204 tests on PR #48 code commit `39499f7e0d16d8c2dd6f2f3d2060a9d8fdc7048d` (run [#43605424201](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43605424201)); the latest documentation-updated head also passed 204 tests (run [#43605522144](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43605522144)).

### Remaining exit evidence
- [ ] Fresh x86_64 QEMU image passes namespace inode, cgroup, Landlock, seccomp, network restriction and MOMO readiness assertions.
- [ ] Fresh AArch64 QEMU image passes the same assertions.
- [ ] Inspect and retain both successful image artifacts, boot logs, build metadata and hashes.
- [ ] Review the complete PR diff and merge PR #48 only after both image acceptance runs pass.

Previous image attempts built and reached `MOMO OS READY` but failed final acceptance because namespace reporting compared against `/proc/1` and returned false. The daemon now verifies its live namespace inode identities against values captured by the root launcher immediately after `unshare()`. Corrected image workflows are running; the section remains open until both architectures pass.

**Boundary:** this section does not enable arbitrary or side-effecting tools. The IPC service remains read-only. Authenticated human/session identity, side-effecting operation adapters, full task/executor sandboxing, deadline/cancellation orchestration, outcome reconciliation, Android platform enforcement and physical-device qualification remain later sections.
