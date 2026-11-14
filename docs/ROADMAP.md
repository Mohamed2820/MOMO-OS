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
- No actual tool executor, authenticated IPC or OS-enforced MOMO sandbox exists.
- No final Android base, first phone SKU, cloud build host or release signing infrastructure is selected.

## Progress Evidence Update — 2026-11-13

### Initial x86_64 bootable target

The initial Buildroot 2026.08.1 x86_64 image built and booted successfully under QEMU. The serial log reached MOMO OS READY after device inventory, persistent permission broker and task-runtime self-tests. The workflow retained a 20,463,168-byte artifact with kernel, root filesystem, boot log and build metadata. The artifact digest and run/commit identifiers are recorded in Stage 1 above. PR #15 was merged into main after this evidence was inspected.

### Integrated durable step execution

PR #26 was merged into the bootable development branch after repository validation passed with 111 unit tests. TaskCoordinator now atomically stores each accepted plan step with the task and immutable plan. The journal persists attempts, cancellation requests, result digests and unique plan-bound idempotency keys. Restart recovery quarantines in-flight steps as needs_review; no ambiguous side effect is replayed. Dependency readiness comes only from durable succeeded records. A SHA-256 hash chain and SQLite mutation guards protect the event history, and corrupted history blocks reads and scheduling. The source is mirrored into the Buildroot overlay and the boot path invokes recovery before readiness.

The integrated revision is undergoing a fresh Buildroot/QEMU run. Until that run passes, the initial QEMU evidence must not be treated as validation of the newer integrated code.

### Explicitly incomplete

Stage 2 and Stage 3 remain open. There is no worker scheduler, actual tool executor, authenticated IPC, native OS sandbox, deadline/backoff service, concurrency/resource manager, independent outcome verifier or needs_review reconciler. The 111-test repository result is not a substitute for image or hardware validation.


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


## Engineering Progress Update — 2026-11-14

### Virtual platform acceptance completed
The integrated Buildroot baseline `a7a4caf381553d9a697b68a093eff9520d8b0bda` passed both virtual-target workflows:
- x86_64 QEMU: [run #43454224817](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224817), artifact 14057431431.
- AArch64 QEMU virt: [run #43454224951](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43454224951), artifact 14055169054.

Both logs show the matching architecture, `MOMO OS READY`, a successful read-only `momo-ipcd` status response and `tool_execution: disabled`. These are virtual targets, not phone support.

### Execution authorization increment
PR #45 adds the in-process `ExecutionGate` and one-time approval tokens, protects plan-bound task/step starts, and adds bypass, expiry, replay, concurrency and rollback tests. Its code commit `47170e0132ae2142d0aa24eea10f26dc35590bc2` passed repository validation with 167 tests. This newer revision has not yet passed fresh QEMU image workflows.

### Current stage and blockers
Stage 2 has a tested authorization/state-transition gate, but it is not a tool executor. Human approver identity is not authenticated, the operation arguments digest is caller-supplied, low-risk grants are in a separate database, and native OS enforcement is not integrated. The status daemon remains read-only. No executor is enabled.

Stage 3 remains open: Linux namespaces, cgroups, LSM and strict operation-specific seccomp; Android Binder/AIDL, SELinux and AppOps; authenticated identity; and adversarial isolation tests are still required.

### Next sequence
1. Rebuild and QEMU-test the current gate revision on x86_64 and AArch64.
2. Implement trusted approval identity and atomic capability reservation.
3. Implement and test the Linux worker sandbox before enabling typed tool dispatch.
4. Continue the core service contracts and implementations.
5. Build the Android baseline and choose exact phone SKUs only after bootloader and recovery evidence.
6. Implement the MOMO shell, AI runtime and essential applications.
7. Complete signing, SBOM, OTA, rollback, hardware qualification and multi-device maintenance.


## Fresh image acceptance — execution-gate revision (2026-11-14)

The cache/output recovery from PR #49 resolved the missing kernel-image failure. The integrated revision `b762dd742e8b3b3ede0e5f98578960446c9b5e25` passed both virtual targets:

- [x86_64 Buildroot/QEMU run #43597839201](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839201), artifact 14115143750.
- [AArch64 Buildroot/QEMU run #43597839262](https://github.com/Mohamed2820/MOMO-OS/actions/runs/43597839262), artifact 14114803046.

Each run passed image verification and QEMU readiness, and confirmed the read-only IPC service with `tool_execution: disabled`. The current execution-gate revision is therefore image-integrated on both virtual architectures. It remains a development system, not a phone ROM.

Stage 2 now includes tested plan-bound authorization state transitions, but the execution gate remains in-process and there is no tool executor. Stage 3 remains open for authenticated human identity, trusted argument hashing, atomic low-risk authorization, Linux namespaces/cgroups/LSM/strict seccomp, Android Binder/AIDL/SELinux/AppOps and adversarial isolation tests.

Next: implement identity and native OS isolation before typed tool dispatch; then complete storage/app/notification/network/power/update services, Android base integration, device ports, UX/AI, signing and release qualification.
