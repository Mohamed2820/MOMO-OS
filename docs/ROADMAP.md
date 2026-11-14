# MOMO OS — End-to-End Roadmap

Roadmap stages are evidence-gated. Dates are not promised until build capacity, device access, platform baselines and maintainers are confirmed.

## Current stage — Experimental Linux bring-up and runtime integration

The first x86_64 Buildroot image has booted successfully in QEMU. The merged TaskCoordinator execution-journal integration is now being rebuilt and must pass the same image, QEMU and readiness checks. This remains a development target, not a mobile ROM.

## Stage 0 — Governance and product baseline

- [x] Repository and cloud-first development strategy.
- [x] Initial architecture, security, device compatibility, AI runtime and licensing documents.
- [x] Initial task state machine, task journal, device inventory and persistent permission broker.
- [x] Initial Task Coordinator with immutable plan binding and scoped permission checks.
- [x] SRS, project overview, master execution plan and evidence-based roadmap.
- [ ] Dependency/license inventory, contribution governance and security reporting process.

**Exit:** product scope and governance approved; claims mapped to evidence.

## Stage 1 — First bootable target (critical path)

- [x] Buildroot x86_64 configuration and MOMO rootfs overlay.
- [x] CI workflow for kernel/rootfs build, QEMU serial boot, readiness check and artifact upload.
- [x] Kernel/rootfs build and image-output verification for the initial bootable revision.
- [x] QEMU serial boot reached MOMO OS READY on the initial bootable revision.
- [x] Target boot checks confirmed device inventory, persistent permission broker and task-runtime self-test.
- [x] Build metadata and QEMU boot log retained in the workflow artifact.
- [x] Initial bootable image PR merged into main after successful QEMU evidence.
- [ ] Rebuild and validate the latest merged coordinator/journal integration in QEMU.

**Initial image evidence:** workflow run 43437714431, commit 74398b8d8ab9e379e94a864d35bb9a6db3623d83, artifact 14046724553. The ZIP is 20,463,168 bytes and its SHA-256 is fbff57ca80e88c0189a70a46d696905dede4986e7498f82eab4afb27466dc2ba. It contains bzImage, rootfs.ext2, qemu-boot.log and build-metadata.txt. This evidence applies to the initial bootable revision, not automatically to later runtime changes.

**Exit:** reproducible QEMU-validated image for the declared x86_64 virtual target, with retained evidence.

## Stage 2 — Runtime and service contracts

- [x] Task state machine and durable event journal.
- [x] Plan validation, agent registry and dependency-aware readiness.
- [x] TaskCoordinator, persistent permission integration and immutable plan digest.
- [x] Atomic creation of task, immutable plan and all step journal records.
- [x] Durable step lifecycle, bounded read-only retry metadata, conservative restart recovery and cancellation requests.
- [x] Dependency readiness derived only from verified durable succeeded records.
- [x] Per-step hash-chained event history with fail-closed reads and scheduling.
- [x] Buildroot overlay integration and boot-time recovery hook in source.
- [ ] Latest coordinator-integrated image passes QEMU recovery and readiness checks.
- [ ] Complete executor protocol, deadlines, backoff, concurrency/fairness limits and resource budgets.
- [ ] Independent outcome verification and needs_review reconciliation.
- [ ] Define remaining versioned contracts for storage, apps, notifications, power, update and audit.
- [ ] Add authenticated IPC identity, structured errors and service health checks.

**Exit:** durable service layer persists, authorizes and recovers tasks without unauthorized side effects; execution dispatch remains blocked until native enforcement is available.

## Stage 3 — OS-enforced security

- [ ] Linux service identities, namespaces, seccomp/LSM policy and sandbox profiles.
- [ ] Android Binder/AIDL, SELinux, AppOps and signature-level enforcement.
- [ ] Secure secret storage, audit redaction and retention/deletion policy.
- [ ] Adversarial tests: prompt injection, confused deputy, replay, path traversal and privilege escalation.
- [ ] Independent security review.

**Exit:** unauthorized actions rejected at native OS boundaries, not only app-level policy.

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

- Latest coordinator-integrated image build and QEMU recovery check are pending.
- No Android/AOSP build or Android phone image is validated.
- No physical device is certified.
- No side-effecting tool executor, authenticated human/session principal or OS-enforced MOMO sandbox exists. A narrow R0/R1 read-only typed executor now exists in source.
- No final Android base, first phone SKU, cloud build host or release signing infrastructure is selected.

## Progress Evidence Update — 2026-11-13

### Initial x86_64 bootable target

The initial Buildroot 2026.08.1 x86_64 image built and booted successfully under QEMU. The serial log reached MOMO OS READY after device inventory, persistent permission broker and task-runtime self-tests. The workflow retained a 20,463,168-byte artifact with kernel, root filesystem, boot log and build metadata. The artifact digest and run/commit identifiers are recorded in Stage 1 above. PR #15 was merged into main after this evidence was inspected.

### Integrated durable step execution

PR #26 was merged into the bootable development branch after repository validation passed with 111 unit tests. TaskCoordinator now atomically stores each accepted plan step with the task and immutable plan. The journal persists attempts, cancellation requests, result digests and unique plan-bound idempotency keys. Restart recovery quarantines in-flight steps as needs_review; no ambiguous side effect is replayed. Dependency readiness comes only from durable succeeded records. A SHA-256 hash chain and SQLite mutation guards protect the event history, and corrupted history blocks reads and scheduling. The source is mirrored into the Buildroot overlay and the boot path invokes recovery before readiness.

The integrated revision is undergoing a fresh Buildroot/QEMU run. Until that run passes, the initial QEMU evidence must not be treated as validation of the newer integrated code.

### Explicitly incomplete

Stage 2 and Stage 3 remain open. There is no worker scheduler, side-effecting tool executor, authenticated human/session identity, native OS sandbox, deadline/backoff service, concurrency/resource manager, independent outcome verifier or needs_review reconciler. A narrow read-only typed executor is source-implemented but awaits fresh CI evidence. The 111-test repository result is not a substitute for image or hardware validation.


## Stage 3 Progress — IPC protocol framing (2026-11-13)

A bounded version-1 Linux local IPC framing codec is under review: strict length-prefixed frames, maximum payload, strict JSON validation and socket stream helpers, with unit and overlay parity tests. This does not complete service IPC or Stage 3. The codec is not wired to a daemon; peer identity must be checked before request processing, and operation authorization, service-role mapping, deadlines, replay defense, quotas and OS-native isolation remain mandatory.

## IPC Service Progress — 2026-11-13

PR #38 adds a first unprivileged AF_UNIX status daemon with a dedicated Buildroot account, kernel peer authentication, one read-only status operation and a CLI client. It is not a tool executor and is not production-security complete. CI and QEMU acceptance are required before merging into the boot branch. Next: replay protection, explicit role/capability authorization, Linux-native sandboxing and adversarial isolation tests. Android remains a separate Binder/AIDL + SELinux/AppOps track.


## IPC Hardening — Replay Detection (2026-11-13)

The local status service now rejects duplicate request IDs using a bounded 1,024-entry process-lifetime cache, and the CLI uses unique IDs and validates server responses strictly. Durable anti-replay for side effects, capability authorization and native sandboxing remain open.


## IPC Process Hardening — Initial Restrictions (2026-11-13)

The IPC daemon now runs unprivileged with explicit core/file/descriptor/address-space limits and `PR_SET_NO_NEW_PRIVS`. This is defense in depth, not a complete sandbox. Seccomp, namespaces, cgroups and LSM enforcement remain future gates before any executor can be enabled.


## IPC Syscall Filtering — 2026-11-13

A libseccomp denylist now blocks selected execution, process creation, namespace, kernel-control and cross-process-memory syscalls in the daemon. It is fail-closed and tested in a subprocess. The policy defaults to allow and is not a complete sandbox; strict syscall allowlisting, namespaces, cgroups and LSM enforcement remain future gates.


## Platform Roadmap — AArch64 virtual bring-up (2026-11-13)

A separate AArch64 QEMU build-and-boot workflow is now under review. It shares the portable runtime and security overlay with x86_64. AArch64 support will not be claimed until the ARM64 workflow passes. Physical device enablement remains per-device engineering, not automatic universal compatibility.


## Image Evidence Update — 2026-11-13

The first x86_64 Buildroot image is confirmed to have built and booted under QEMU, reaching `MOMO OS READY` on commit `74398b8d8ab9e379e94a864d35bb9a6db3623d83` ([run #43437714431](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43437714431)). The later Step Journal/TaskCoordinator integrated revision still requires its own fresh QEMU acceptance ([run #43446234529](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43446234529)).


## Integrated Baseline Update — 2026-11-13

PR #42 is merged into `bootable/x86_64-buildroot-mvp-v2`, integrating the read-only authenticated IPC status daemon, bounded replay detection, process limits, `PR_SET_NO_NEW_PRIVS`, libseccomp denylist and AArch64 QEMU target workflow. The service is intentionally non-executing. The syscall policy is a default-allow denylist, not a complete sandbox.

Fresh x86_64 and AArch64 image workflows are running against integrated commit `a7a4caf381553d9a697b68a093eff9520d8b0bda`: [x86_64](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224817) and [AArch64](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224951). At last inspection, both were in the kernel/rootfs build stage; QEMU acceptance and artifacts remain pending. Historical x86_64 baseline evidence must not be used to claim this integrated revision passed.

Next gates: fresh image/QEMU evidence on both architectures; adversarial security tests; explicit capability authorization; namespace/cgroup/LSM isolation; durable execution/idempotency design; then separate AOSP/Binder-AIDL/SELinux/AppOps implementation and per-device hardware enablement. No universal physical-device compatibility is claimed.


## Progress Evidence Update — 2026-11-14: execution runtime and IPC integration

The latest integration candidate adds the plan-bound execution gate and durable step journal to the coordinator and Buildroot overlay. It adds single-use, expiring approval tokens bound to task/step/plan/arguments, plus regression tests for forgery, replay, expiry, concurrency, plan substitution and interrupted-step recovery.

The Linux x86_64 target now has a dedicated unprivileged status daemon using AF_UNIX, SO_PEERCRED, bounded versioned framing, process limits, `no_new_privs` and a required libseccomp denylist. The endpoint is deliberately read-only and returns `tool_execution: disabled`. An AArch64 QEMU workflow is also defined.

**Repository CI evidence:** integration PR #48 run [#43597582878](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597582878) passed documentation/JSON, device-profile schema, shell and 167 runtime unit tests on the initial PR head. Subsequent engineering-document and workflow changes require a fresh CI run.

**Still not accepted:** the integrated x86_64 and AArch64 images have not yet passed fresh QEMU boot acceptance for this revision. The earlier x86_64 boot evidence applies only to its recorded older commit.

### Stage 2 — updated status
- [x] TaskCoordinator integration with durable per-step journal.
- [x] Plan-bound execution gate and single-use approval token primitive.
- [x] Restart recovery quarantine and event-chain tamper tests.
- [x] Linux read-only IPC status service and peer credential checks.
- [ ] Authenticated human/session identity and approval-principal binding.
- [x] Strict argument canonicalization at public approval/start APIs (source-level; fresh CI pending).
- [ ] Side-effecting typed adapters, idempotency propagation, deadlines, cancellation and outcome reconciliation.
- [ ] Native Linux namespaces/cgroups/LSM enforcement and strict seccomp profiles.
- [ ] Fresh x86_64 and AArch64 QEMU integration acceptance.
- [ ] Android Binder/AIDL and SELinux/AppOps implementation.

The current work advances the runtime and Linux security foundations but does not close Stage 2, Stage 3, or any phone support gate.


## Progress Evidence Update — 2026-11-14: PR #48 current head

The current PR #48 head is `eac08aedb9a5e5fc0c4a87eaf1a973bf525242ab`.

- Repository validation run [#43598435793](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435793) completed successfully, including 167 runtime unit tests and the repository documentation, JSON, workflow, device-profile and shell checks.
- x86_64 image run [#43598435846](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435846) is still building the Linux kernel and MOMO root filesystem. Image verification, QEMU boot/readiness, provenance and artifact upload have not yet completed.
- AArch64 image run [#43598435820](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435820) is still building the Linux kernel and MOMO root filesystem. Image verification, QEMU boot/readiness, provenance and artifact upload have not yet completed.

This supersedes the earlier PR #48 CI run references above for the current candidate. It does not supersede or reuse historical QEMU evidence from older commits. PR #48 remains open and unmerged.

**Engineering boundary remains unchanged:** the Linux IPC endpoint is read-only; there is no authenticated human principal, trusted executor-side argument canonicalization, typed side-effecting executor, full native Linux sandbox, Android Binder/AIDL adapter or physical-device qualification. Do not enable tool execution or claim Stage 2/3 completion until their explicit exit gates are evidenced.


## Follow-up engineering increment — canonical argument binding

After the image workflows recorded above started, PR #48 received an additional runtime increment on later commits. A bounded strict-JSON argument binding primitive now rejects duplicate object keys, invalid UTF-8/Unicode, non-standard numeric constants, excessive payload size/depth/node count and out-of-range integers; it emits deterministic canonical JSON and SHA-256. The module is mirrored into the Buildroot rootfs overlay, with focused unit tests and an overlay-parity assertion.

This is a serialization primitive, not an authorization boundary. It is not yet connected to an authenticated executor or the ExecutionGate, and the current gate still accepts a caller-supplied digest. The x86_64/AArch64 runs listed above started before this addition and do not contain it. The new tests have not yet been executed by a fresh CI run; do not promote this increment to CI-tested until that evidence exists.


## Argument-bound authorization increment — 2026-11-14

The public step authorization path no longer accepts a caller-supplied digest. `ApprovalStore.issue_for_arguments()` and `ExecutionGate.start_step()` accept the exact bounded JSON payload and derive canonical SHA-256 internally. The low-level digest transition is private to the gate module. `start_step_with_arguments()` returns the exact parsed values as a recursively immutable structure, alongside canonical JSON and digest, for a future typed executor to consume without reparsing mutable input. Rootfs copies are kept byte-for-byte in parity.

Focused tests cover approval/start digest agreement, changed-payload rejection, duplicate-key rejection, malformed-input rejection, canonical key ordering and deep immutability; the TaskCoordinator tests were migrated from precomputed digests to raw JSON payloads. These tests are source-added but have not yet run in CI. The approver label is still caller-asserted; there is no authenticated user/session identity, no broad operation-specific schema registry beyond the first status adapter, no side-effecting executor, and no OS-enforced isolation. Tool execution beyond the read-only status adapter stays disabled.


## Current candidate verification status — PR #48

Latest inspected PR #48 head: `68f4a4748a48e35d2bb9fd7fa71bce8daeb211cb`. The previous repository validation [#43598435793](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435793) passed on older head `eac08aedb9a5e5fc0c4a87eaf1a973bf525242ab`; it predates the strict argument-binding integration and its new tests. It cannot be used to claim the current candidate is CI-tested.

The x86_64 run [#43598435846](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435846) and AArch64 run [#43598435820](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43598435820) are also tied to the older `eac08aed...` head. At last inspection x86_64 remained in kernel/rootfs compilation and AArch64 completed image verification, QEMU readiness, provenance and artifact upload successfully; neither is evidence for the current PR head. Do not merge PR #48 or close Section 1 on these stale runs.

The latest source increment makes the public step approval/start APIs accept raw bounded JSON instead of caller-supplied digests, and returns deeply immutable authorized arguments through `start_step_with_arguments()`. The focused parser/gate tests and source/rootfs parity are added. They remain unverified by a fresh repository CI run. The remaining hard blockers are authenticated human/session identity, broader operation-specific schemas, deadlines/cancellation and resource budgets, side-effecting adapter design, OS-enforced sandboxing, outcome reconciliation, fresh CI, and current-head x86_64/AArch64 QEMU acceptance.


## First typed execution adapter — 2026-11-14

A narrow in-process typed executor now exists at `intelligence/runtime/typed_executor.py`, mirrored byte-for-byte into the Buildroot rootfs. Its registry permits only R0/R1 operations. The first built-in adapter is `system.status.read`: exact empty-object schema, planned domain/capability/risk matching, authorization through the public ExecutionGate, a registered handler only (no request-selected callable or shell), canonical result digest, and durable step completion. Tests cover successful journaling, unknown-operation denial, schema rejection, plan mismatch, high-risk registration refusal and immutable results.

This is a source-level read-only reference adapter, not a general or side-effecting executor. It has no hard deadlines, cancellation controller, side-effect idempotency/reconciliation, authenticated human/session identity or OS sandbox. The new tests and overlay parity have not yet been run in a fresh CI workflow for the current PR #48 head. Keep side-effecting tool execution disabled.


## Repository validation evidence — 2026-11-14

The integrated source/test candidate on PR #48 commit `fbd9d96caba43346af63adf2c829f32efce7557c` passed the full repository-validation workflow [#43602320431](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602320431): **196 runtime unit tests passed**, including the new argument-binding, approval/start integration, typed read-only executor and rootfs parity tests, plus documentation/JSON, YAML workflow, device-profile schema, shell utility and compile checks. A follow-up validation run [#43602466765](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602466765) is running on the latest documentation-updated PR head.

Current-head x86_64 and AArch64 Buildroot/QEMU acceptance is being run on the dedicated validation branch derived from the same PR source tree: [x86_64 run #43602390663](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602390663) and [AArch64 run #43602394024](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602394024). Both must reach QEMU readiness and artifact upload before image acceptance is recorded.


## Linux kernel isolation prerequisites — 2026-11-14

Added a shared Buildroot kernel fragment requesting UTS/IPC/user/PID/network namespaces, cgroups with PID/CPU/memory/freezer/device controllers, seccomp filtering and Landlock. Both x86_64 and AArch64 image workflows now apply the fragment and validate the generated kernel `.config` before image acceptance. A validator and four unit tests cover missing options and inactive Landlock.

This is groundwork only. A configured kernel does not isolate a service by itself. Service launch still needs explicit namespace setup, cgroup assignment, Landlock rules, filesystem/network policy, authenticated principal mapping and adversarial integration tests. Fresh image builds must prove the options survive Buildroot configuration on both architectures.


## Latest kernel-prerequisite validation — 2026-11-14

Repository validation [#43602800965](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602800965) passed **200 tests** and validated the kernel fragment, workflow YAML, shell utilities, device profiles, Python compilation and rootfs parity. Fresh image workflows now run on the integration candidate with the kernel fragment enabled: x86_64 [#43602898660](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602898660) and AArch64 [#43602902414](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43602902414). Both must finish the kernel build, verify the generated security config, pass QEMU readiness and upload artifacts. They have not yet reached those acceptance gates.


## Landlock filesystem boundary for IPC status service — 2026-11-14

The unprivileged read-only IPC daemon now applies Landlock after binding its socket and loading seccomp. It can read/execute from `/usr`, read from `/etc`, and inspect/remove its own socket under `/run/momo`; other handled filesystem access is denied. The setup is fail-closed. A subprocess test checks allowed reads, denied reads outside the allowlist and denied writes.

This is a real filesystem restriction for the status daemon, not a complete MOMO sandbox. Per-service namespaces, cgroups, network isolation, a strict syscall allowlist, authenticated principal mapping and security enforcement for future task/executor services remain open. The Landlock code and test require fresh CI and QEMU boot evidence before promotion.


## Landlock CI verification — 2026-11-14

The Landlock status-daemon implementation, source and test changes passed repository validation [#43603174498](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43603174498): **201 tests passed**, including the subprocess check that allows reads only from an explicit directory and denies unrelated reads and writes. The x86_64 and AArch64 Buildroot/QEMU workflows are currently running on commit `3bc18a52976909d72f3e82da4fccdbc54a7edad9`: [x86_64 #43603174532](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43603174532) and [AArch64 #43603174676](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43603174676). QEMU readiness and artifact upload remain pending.


## IPC status-service namespace and cgroup profile — 2026-11-14

Added `momo-ipc-sandbox`, a root-started launcher that moves the daemon into a dedicated cgroup before dropping privileges, creates private mount/IPC/UTS/network namespaces, makes mount propagation private, clears supplementary groups, drops to the dedicated `momo-ipc` UID/GID and sets `no_new_privs`. Init script `S98momo-ipc` now requires cgroup v2 CPU/memory/PID controllers and sets a 50% CPU quota, 128 MiB memory limit and 16-process limit. The daemon then applies its existing seccomp denylist and Landlock filesystem boundary.

This is a per-service sandbox profile for the read-only status daemon only. PID/user namespaces, task/executor service isolation, authenticated human/session identity, a strict syscall allowlist, network firewall policy, and adversarial QEMU tests remain open. The wrapper/init changes have not yet passed a fresh CI/QEMU run; do not mark the sandbox gate complete until they do.


## QEMU namespace-verification correction — 2026-11-14

The latest completed x86_64 run [#43604027590](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43604027590) and AArch64 run [#43604027591](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43604027591) both built the kernel/rootfs and reached `MOMO OS READY`. Both failed the final acceptance step because the daemon reported all four namespace checks as false; cgroup membership, Landlock and seccomp were reported active. The images and boot logs were uploaded, but these are failed acceptance runs, not accepted images.

The status check compared the daemon namespace inode against `/proc/1/ns`, which can produce a false negative when procfs visibility/permissions differ under the service filesystem policy. The launcher now records the four kernel namespace inode values immediately after successful `unshare()`; the daemon compares its current namespace identities against that launch-time record. This is a verification-method correction, not a relaxation of the namespace requirement. The new repository and dual-architecture QEMU workflows are running against the corrected candidate. Do not mark namespace isolation or the integrated images accepted until both current-head runs pass all namespace, cgroup, Landlock, seccomp and readiness checks.
