# Software Requirements Specification (SRS)
## MOMO OS — Device-Adaptive Mobile Computing Platform

**Document status:** Active SRS, version 1.0  
**Date:** 2026-11-13  
**Repository:** Mohamed2820/MOMO-OS  
**Normative language:** "shall" indicates a requirement; "should" indicates a recommended requirement.  
**Implementation status:** Requirements are tracked against source implementation and test evidence. This document is not evidence that every requirement has been implemented or validated.

---

## Implementation Snapshot (2026-11-13)

This snapshot distinguishes source implementation, target-image integration, automated tests and hardware validation.

| Area | Current implementation | Evidence / limitation |
|---|---|---|
| x86_64 Linux image | Buildroot configuration, kernel/rootfs pipeline and QEMU serial-boot acceptance check | Latest image run #43437714431 is in progress at kernel/rootfs build; no image artifact or successful QEMU boot yet. Earlier run #43436209791 was cancelled during build and produced metadata only. |
| Task state machine | Risk-aware lifecycle and transition validation | Repository unit tests pass |
| Persistent task journal | SQLite TaskStore and append-only transition history | Included in Buildroot overlay; image-level execution awaits QEMU boot |
| Task Coordinator | Plan validation, immutable SHA-256 binding, atomic task/plan/event persistence and permission checks | PR #23 merged; repository tests pass; no tool execution or crash-recovery scheduler yet |
| Task CLI | create/list/show/transition/doctor/self-test | Included in rootfs overlay; target CLI has not yet been exercised in QEMU |
| Device inventory | Runtime OS/kernel/architecture/device identity collection | Source and rootfs overlay included; exact hardware capabilities remain unknown absent verified profile |
| Persistent permission broker | SQLite grants, expiry, revocation, bounded use, exact R3/R4 approval matching and audit journal | Source and rootfs overlay included; policy layer does not enforce native OS permissions or execute tools |
| Device profiles | JSON schema and CI validation | Schema validation does not prove a device port boots |
| Android track | Architecture and requirements only | No AOSP build, Android boot image or phone installation validated |
| Physical devices | Device support tiers defined | No phone hardware is currently certified |

**Evidence levels used in this SRS**

1. *Specified*: requirement and design documented.
2. *Implemented*: source code exists.
3. *CI-tested*: automated repository tests pass.
4. *Image-integrated*: files and configuration are included in the target root filesystem.
5. *QEMU-validated*: target image builds and passes runtime checks in the emulator.
6. *Hardware-validated*: exact device SKU boots and its required hardware functions pass tests.

A lower level must not be presented as evidence for a higher level. The first target is an x86_64 virtual machine, not a mobile release. Each phone still requires its own boot chain, kernel/vendor support, firmware, device tree, recovery strategy and hardware validation.


## 1. Introduction

### 1.1 Purpose
This document defines functional and non-functional requirements for MOMO OS, a device-adaptive mobile computing platform with a unified MOMO experience over Android-compatible and mainline-Linux platform tracks. It is intended for architecture, implementation, testing, security review, device porting and release planning.

### 1.2 Scope
MOMO OS shall provide:
- A coherent mobile user experience and optional desktop/convergence mode.
- Platform-neutral system services and APIs.
- Device-specific adapters and evidence-based hardware compatibility.
- A permission and security model that gives users meaningful control without unrestricted ambient authority.
- A multi-agent personal assistant integrated with system services.
- Local-first operation with optional, policy-controlled cloud services.
- Device-specific build, update, recovery and support processes.

MOMO OS is not defined as a new kernel written from scratch. It reuses mature upstream projects where technically and legally appropriate. It does not promise one universal binary that boots every phone.

### 1.3 Definitions
- **Platform track:** Android-compatible or mainline-Linux implementation path.
- **Device profile:** machine-readable identity, firmware, boot, kernel, capability and evidence record for an exact device SKU.
- **Adapter:** typed implementation translating MOMO APIs to platform/device APIs.
- **Capability:** a discovered and tested device/service feature.
- **Agent:** bounded AI worker with a role, schemas and allowlisted tools.
- **Permission Broker:** independent policy component deciding whether an operation is authorized.
- **Support tier:** evidence-based maturity level for a device port.
- **R0-R4:** risk levels from public/read-only through destructive/security/device-integrity operations.

### 1.4 References
- AOSP architecture: https://source.android.com/docs/core/architecture
- Android kernel/GKI: https://source.android.com/docs/core/architecture/kernel
- Android HAL: https://source.android.com/docs/core/architecture/hal
- Android partitions and Treble: https://source.android.com/docs/core/architecture/partitions
- Stable AIDL HALs: https://source.android.com/docs/core/architecture/aidl/aidl-hals
- Linux kernel documentation: https://docs.kernel.org/
- postmarketOS: https://postmarketos.org/

### 1.5 Product constraints
- Android and Linux have distinct kernels, hardware APIs, app ecosystems and update mechanisms.
- Each hardware SKU requires its own validated boot and hardware integration.
- Vendor firmware/blobs require license and provenance review.
- Bootloader unlocking and secure boot constraints may prevent a port.
- Cloud build capacity and physical test hardware are required for release qualification.

## 2. Overall Description

### 2.1 Product perspective
MOMO OS consists of:
1. MOMO Experience (mobile shell, launcher, settings, accessibility, desktop mode).
2. MOMO Intelligence (planner, agent registry, scheduler, model router, memory, verifier).
3. MOMO Core Services (device inventory, files, apps, notifications, power, updates, audit).
4. MOMO Security (identity, permission broker, sandboxing, secure storage, audit).
5. Compatibility Runtime (stable platform-neutral service APIs).
6. Platform Adapters (Android HAL/framework or Linux services/portals).
7. Kernel, firmware and boot chain supplied by the selected platform/device port.

### 2.2 User classes
- Everyday user: messaging, media, calls, files, settings and assistant tasks.
- Power user: advanced file management, automation, terminal/developer tools and desktop mode.
- Developer/maintainer: device porting, builds, diagnostics, signing and release operations.
- Enterprise/administrator: policy management and managed deployment, if implemented in a later product phase.

### 2.3 Operating environments
- Android-compatible devices with supported bootloader, kernel/vendor stack and recovery path.
- Mainline-Linux-friendly mobile devices with sufficiently mature drivers.
- Virtual/emulated x86_64 and ARM64 targets for service and CI development only.
- Desktop-mode displays and peripherals where supported by the device.

### 2.4 Assumptions and dependencies
- AOSP or Linux upstream projects remain available under compatible licenses.
- Device-specific sources and firmware are legally usable.
- Users can obtain required unlock/recovery access for a selected device.
- Cloud CI can build large source trees; physical devices are available for hardware validation.
- Model providers and local inference runtimes expose stable, documented interfaces.

## 3. Functional Requirements

### 3.1 Boot, platform and compatibility
- **FR-PLAT-001:** The system shall identify its platform track, architecture, OS release and kernel release at runtime.
- **FR-PLAT-002:** The system shall load a device profile matching the exact device identity and firmware variant.
- **FR-PLAT-003:** The system shall not infer hardware support from marketing name alone.
- **FR-PLAT-004:** The system shall expose hardware capabilities with states supported, unsupported, temporarily unavailable or permission denied.
- **FR-PLAT-005:** Unknown capabilities shall be treated as unavailable until verified.
- **FR-PLAT-006:** Platform-specific behavior shall be isolated behind versioned adapters.
- **FR-PLAT-007:** A platform adapter shall declare supported API/kernel ranges, required capabilities, operation risks and test evidence.
- **FR-PLAT-008:** Unsupported optional hardware features shall degrade gracefully without falsely reporting success.
- **FR-PLAT-009:** A device port shall not be installable/releasable without a verified boot and recovery procedure.
- **FR-PLAT-010:** The product shall maintain independent Android-compatible and mainline-Linux integration tracks.

### 3.2 User experience and desktop convergence
- **FR-UX-001:** The system shall provide a touch-first mobile shell.
- **FR-UX-002:** The shell shall expose system navigation, notifications, quick settings and accessibility controls.
- **FR-UX-003:** The system should provide multi-window and resizable application support where the platform permits.
- **FR-UX-004:** The system should provide desktop mode with external display, keyboard and pointer support where hardware permits.
- **FR-UX-005:** The UI shall adapt to screen size, density, orientation, input method and available capabilities.
- **FR-UX-006:** Users shall be able to configure privacy, permissions, accessibility and AI behavior.
- **FR-UX-007:** The interface shall clearly indicate unavailable or restricted hardware functions.

### 3.3 Applications and files
- **FR-APP-001:** Android track shall preserve Android application compatibility subject to platform compatibility and service dependencies.
- **FR-APP-002:** Linux track shall support native Linux applications through a documented package/runtime strategy.
- **FR-APP-003:** The system shall not claim automatic APK compatibility on a native Linux track.
- **FR-FS-001:** File access shall use scoped permissions and user-visible grants.
- **FR-FS-002:** The file manager shall support search, metadata, copy, move, rename, delete and archive operations where permitted.
- **FR-FS-003:** Destructive operations shall support confirmation and recovery mechanisms where technically possible.
- **FR-FS-004:** Private app data shall not be exposed to agents without explicit scoped authorization.

### 3.4 Core services
- **FR-SVC-001:** The system shall expose versioned APIs for device inventory, permissions, tasks, storage, apps and notifications.
- **FR-SVC-002:** Each side-effecting service operation shall produce an audit/correlation identifier.
- **FR-SVC-003:** Services shall expose structured errors, cancellation and bounded execution time.
- **FR-SVC-004:** Services shall run with least privilege and shall not require unrestricted root for normal operation.
- **FR-SVC-005:** Service APIs shall be platform-neutral at the contract level.

### 3.5 AI personal assistant and multi-agent system
- **FR-AI-001:** The assistant shall accept natural-language tasks through supported text and voice interfaces.
- **FR-AI-002:** The assistant shall classify intent, identify ambiguity and request essential missing information.
- **FR-AI-003:** The planner shall decompose complex goals into tasks with dependencies, preconditions, risk levels and acceptance criteria.
- **FR-AI-004:** The scheduler shall run independent tasks concurrently when safe and respect dependencies.
- **FR-AI-005:** Agents shall have explicit roles, schemas and tool allowlists.
- **FR-AI-006:** The model router shall select local or cloud models according to capability, privacy, latency, cost and availability.
- **FR-AI-007:** Cloud use shall be disclosed and shall not silently transfer private context against user policy.
- **FR-AI-008:** The tool gateway shall validate schemas and route all privileged operations through the Permission Broker.
- **FR-AI-009:** Models and agents shall not grant themselves permissions or approve their own high-risk actions.
- **FR-AI-010:** The verifier shall check outcomes against acceptance criteria and report partial/failed results honestly.
- **FR-AI-011:** The assistant shall support cancellation and bounded retries.
- **FR-AI-012:** Memory shall be scoped, provenance-aware and subject to user controls and retention policy.
- **FR-AI-013:** The assistant shall provide useful offline behavior when local models and local tools are available.
- **FR-AI-014:** The product shall not claim AGI; capability shall be measured by reproducible task benchmarks.

### 3.6 Security and permissions
- **FR-SEC-001:** The system shall enforce least privilege for services, apps and agents.
- **FR-SEC-002:** Permissions shall identify subject, action, resource, risk, expiry and approval scope.
- **FR-SEC-003:** R3 external side effects and R4 destructive/security-sensitive actions shall require explicit, operation-specific approval.
- **FR-SEC-004:** Approval shall be bound to exact arguments/target and shall expire.
- **FR-SEC-005:** Generic unrestricted shell/root execution shall not be exposed to AI agents.
- **FR-SEC-006:** Secrets shall be stored using platform-backed secure storage where available and excluded from logs/source.
- **FR-SEC-007:** The system shall preserve verified boot, SELinux/sandbox policy and platform security boundaries.
- **FR-SEC-008:** Security-sensitive events shall be auditable with privacy-preserving redaction.
- **FR-SEC-009:** Network, microphone, camera, contacts, location, messages, payments, app installation and deletion shall have distinct permission controls.
- **FR-SEC-010:** Prompt-injection content from files, web pages and tool outputs shall be treated as untrusted data.

### 3.7 Updates and recovery
- **FR-UPD-001:** Release artifacts shall be signed and accompanied by verifiable checksums and provenance.
- **FR-UPD-002:** Update metadata and payload signatures shall be verified before installation.
- **FR-UPD-003:** Updates shall support staged rollout and health checks where platform architecture permits.
- **FR-UPD-004:** Supported devices shall have a documented rollback/recovery procedure.
- **FR-UPD-005:** Release notes shall disclose known issues, device support tier and feature matrix.
- **FR-UPD-006:** No stable release shall be published when critical recovery, signing or security gates fail.

## 4. Non-Functional Requirements

### 4.1 Security
- **NFR-SEC-001:** Security boundaries shall be enforced below the model layer.
- **NFR-SEC-002:** Privileged APIs shall be narrow, typed and auditable.
- **NFR-SEC-003:** Security tests shall include permission bypass, confused-deputy and prompt-injection cases.
- **NFR-SEC-004:** The project shall publish a vulnerability reporting and response process before stable release.

### 4.2 Privacy
- **NFR-PRIV-001:** Local processing shall be preferred where practical.
- **NFR-PRIV-002:** Data sent to cloud services shall be minimized and disclosed.
- **NFR-PRIV-003:** Logs shall redact secrets and sensitive content by default.
- **NFR-PRIV-004:** Users shall be able to inspect and control stored assistant memory according to product policy.

### 4.3 Performance and resource use
- **NFR-PERF-001:** Core UI interactions should target p95 response under 100 ms on qualified hardware, excluding application/network latency.
- **NFR-PERF-002:** Background services shall have explicit CPU, memory, storage and battery budgets per device tier.
- **NFR-PERF-003:** AI tasks shall expose progress, cancellation and resource usage where measurable.
- **NFR-PERF-004:** The system shall avoid loading optional agents/models until needed.
- **NFR-PERF-005:** Performance targets shall be measured on a published hardware matrix, not assumed across all devices.

### 4.4 Reliability and availability
- **NFR-REL-001:** Core services shall recover from process restart without corrupting durable task state.
- **NFR-REL-002:** Side-effecting operations shall use idempotency or reconciliation where possible.
- **NFR-REL-003:** A failed optional service shall not prevent basic telephony/boot functions on supported phone platforms.
- **NFR-REL-004:** Updates shall preserve a recoverable boot path on qualified devices.

### 4.5 Portability and maintainability
- **NFR-PORT-001:** Shared service logic shall not depend on a specific device codename or vendor filesystem layout.
- **NFR-PORT-002:** Platform adapters shall be independently versioned and tested.
- **NFR-PORT-003:** Device profiles shall validate against a checked-in schema.
- **NFR-PORT-004:** No multi-device support claim shall be made until at least two distinct device families have boot and feature test evidence.
- **NFR-MAINT-001:** Dependencies shall be pinned and have provenance/license records.
- **NFR-MAINT-002:** CI shall validate docs, schemas, unit tests, static checks and build manifests.
- **NFR-MAINT-003:** Each release shall publish an SBOM and source/toolchain provenance.

### 4.6 Accessibility and internationalization
- **NFR-A11Y-001:** UI components shall support screen readers, scalable text, contrast and alternative input.
- **NFR-I18N-001:** The product shall support localization, including Arabic RTL and English LTR layouts.
- **NFR-I18N-002:** Dates, numbers and input methods shall follow locale settings without breaking technical identifiers.

## 5. External Interface Requirements

### 5.1 User interfaces
Touch-first mobile UI, optional desktop shell, accessibility APIs, text and voice assistant surfaces.

### 5.2 Hardware interfaces
Display, touch, GPU, storage, battery/charging, thermal sensors, Wi-Fi, Bluetooth, modem/telephony, audio, cameras, location, sensors and secure hardware, each exposed only through platform/device-supported interfaces.

### 5.3 Software interfaces
Android framework services, stable AIDL HALs, Android Common Kernel/vendor modules, Linux kernel/userspace services, D-Bus/portals, local model runtimes, cloud model APIs and signed update infrastructure.

### 5.4 Communication interfaces
TLS-protected network APIs; local IPC authenticated by OS identity and scoped capabilities; no unauthenticated privileged local endpoint.

## 6. Data Requirements
- Device profiles shall be versioned JSON validated against the repository schema.
- Task state and audit events shall have stable IDs and timestamps.
- Memory entries shall include source/provenance, scope and retention metadata.
- Credentials shall be held in secure storage and never committed.
- Build and release metadata shall identify source revisions, toolchain, device profile and artifact hashes.

## 7. Risk Classification
- R0: public/read-only information.
- R1: scoped private read.
- R2: reversible local write.
- R3: external side effect (send, publish, purchase, network mutation).
- R4: destructive, security-sensitive or device-integrity action (wipe, flash, unlock, key changes).

R3/R4 require explicit operation-specific approval; certain actions may be disallowed by policy even with approval.

## 8. Device Support and Acceptance Tiers
- Tier 0 Research: exact identity/source discovery; no boot claim.
- Tier 1 Buildable: reproducible build/static checks; hardware boot unproven.
- Tier 2 Boots: verified boot and basic display/input.
- Tier 3 Daily-use candidate: telephony, data, Wi-Fi, Bluetooth, audio, camera, sensors, suspend/resume, encryption and OTA tested.
- Tier 4 Maintained: signed repeatable releases, security updates, rollback/recovery, regression suite and active maintainer.

## 9. Verification and Acceptance
- Unit tests for state machines, permission policy, schemas and adapter contracts.
- Integration tests for platform services and adapter compatibility.
- Hardware-in-loop tests for each claimed device.
- Security tests for privilege escalation, data isolation, prompt injection and tool misuse.
- AI evaluations for task completion, correctness, cost, latency, privacy and recovery.
- Release qualification for signature verification, update, rollback and data integrity.

A requirement is accepted only when a test or documented review provides evidence. Documentation presence alone is not implementation evidence.

## 10. Traceability and Priorities

| Requirement group | Priority | Primary verification |
|---|---|---|
| Boot/platform identity and profiles | P0 | schema + device integration tests |
| Permission/security broker | P0 | unit + adversarial security tests |
| Core task coordinator | P0 | state-machine and persistence tests |
| Basic mobile shell | P1 | UI and accessibility tests |
| Storage/app/notification services | P1 | integration tests |
| AI planner/tool gateway/verifier | P1 | agent benchmark and security tests |
| Desktop convergence | P2 | hardware/UI integration tests |
| Mainline Linux port | P2 | device-family port and hardware tests |
| Enterprise management | P3 | separate requirements and policy review |

## 11. Open Decisions
- Exact Android baseline and update strategy.
- First two Android device families and first mainline-Linux candidate.
- Linux mobile shell and application compatibility/runtime choice.
- Local inference runtimes and minimum RAM/accelerator profiles.
- Signing key custody and release infrastructure.
- Telemetry opt-in, memory retention defaults and vulnerability response SLA.
- Accessibility and Arabic localization acceptance targets.

## 12. Definition of Done
MOMO OS is production-ready only when a reproducible, signed release boots on its declared devices; the support matrix reflects hardware test evidence; core services and security boundaries pass acceptance tests; AI tools operate through explicit permissions and verified outcomes; updates and recovery are tested; and source, licenses, SBOM and release provenance are published.


---

# SRS Extension — Complete System Requirements Baseline

**Baseline version:** 1.0  
**Status:** Requirements baseline; implementation remains incremental.  
**Normative rule:** each requirement must be linked to implementation and verification evidence before being marked complete.

## 13. System context and architectural constraints

### 13.1 Product boundaries
MOMO OS is a product family consisting of shared MOMO contracts and independently implemented platform tracks. Android-compatible and mainline-Linux tracks are not interchangeable operating systems. Kernel, boot chain, drivers, HALs, application model, security enforcement and update mechanism remain platform-specific.

### 13.2 Architectural requirements
- **ARC-001:** Shared MOMO contracts shall not expose platform-private structures as public APIs.
- **ARC-002:** Each adapter shall declare platform, version range, capabilities, privilege requirements and conformance tests.
- **ARC-003:** Boot, emergency, recovery and basic device functions shall not depend on models, network access or AI.
- **ARC-004:** Optional subsystems shall fail independently and expose health state.
- **ARC-005:** Device-specific code shall be isolated from shared service logic.
- **ARC-006:** Hardware capability shall not be reported supported without successful probe or suitable profile evidence.
- **ARC-007:** Public service contracts shall be versioned and have compatibility tests.

## 14. Detailed functional requirements

### 14.1 Boot and lifecycle
- **FR-BOOT-001:** Boot shall identify platform and target profile before optional MOMO services start.
- **FR-BOOT-002:** Failure of an optional service shall not cause an unrecoverable boot loop.
- **FR-BOOT-003:** The system shall expose boot stage, service health and diagnostic logs.
- **FR-BOOT-004:** Safe/recovery mode shall disable nonessential services and AI automation.
- **FR-BOOT-005:** Every bootable release shall have a documented recovery and restore path for its exact device.

### 14.2 Device profile and hardware abstraction
- **FR-DEV-001:** Each profile shall bind to exact manufacturer, model, board/codename, SKU/region and relevant firmware.
- **FR-DEV-002:** Each capability shall include status, evidence source, last-tested timestamp and adapter version.
- **FR-DEV-003:** Profiles shall distinguish unsupported, unknown, unavailable, permission-denied and supported.
- **FR-DEV-004:** Runtime discovery shall not silently override reviewed profile data with weaker inferred data.
- **FR-DEV-005:** Capability changes shall be observable and auditable.
- **FR-DEV-006:** Device adapters shall gracefully degrade when optional hardware is absent.
- **FR-DEV-007:** Device-specific boot and recovery metadata shall be validated before a release is installable.

### 14.3 Service framework and IPC
- **FR-IPC-001:** Local endpoints shall authenticate callers using native OS identity.
- **FR-IPC-002:** Requests shall carry schema version, request ID, deadline and caller identity.
- **FR-IPC-003:** Responses shall contain structured status, error code, correlation ID and bounded diagnostic detail.
- **FR-IPC-004:** Service APIs shall support cancellation where safe.
- **FR-IPC-005:** Privileged services shall reject unknown fields and invalid enum values in security-sensitive requests.
- **FR-IPC-006:** IPC endpoints shall not be exposed to unauthenticated network clients by default.
- **FR-IPC-007:** Adapters shall pass shared contract and platform security tests.

### 14.4 Task and automation execution
- **FR-TASK-001:** Every task shall have stable ID, owner, goal, risk ceiling, state, creation time and event history.
- **FR-TASK-002:** Plans shall declare steps, dependencies, required capabilities, agent roles, risk, deadlines and acceptance criteria.
- **FR-TASK-003:** Plans shall be validated against registered agent/tool capabilities before scheduling.
- **FR-TASK-004:** Persisted tasks shall be cryptographically bound to their accepted plan version.
- **FR-TASK-005:** The scheduler shall run only steps whose dependencies are complete and preconditions remain true.
- **FR-TASK-006:** Every side-effecting step shall be authorized against exact subject, action, resource and risk.
- **FR-TASK-007:** R3/R4 steps shall require operation-specific approval bound to exact target and arguments.
- **FR-TASK-008:** Cancellation shall prevent new steps and propagate to running adapters where safe.
- **FR-TASK-009:** Retries shall be bounded and use backoff; side effects shall use idempotency or reconciliation.
- **FR-TASK-010:** After restart, interrupted steps shall be reconciled without blindly repeating side effects.
- **FR-TASK-011:** State transitions shall be atomic and validated against an explicit state machine.
- **FR-TASK-012:** A task shall not be marked successful without independent verification of acceptance criteria.
- **FR-TASK-013:** Users shall inspect, pause, cancel and review task history.
- **FR-TASK-014:** Budgets shall limit concurrency, CPU, memory, network and model/tool spend where measurable.

### 14.5 Permission and security enforcement
- **FR-PERM-001:** Permissions shall represent principal, capability, resource scope, risk, expiry, use limit and approval binding.
- **FR-PERM-002:** Grants shall be revocable before the next operation.
- **FR-PERM-003:** Single-use grants shall be consumed atomically to prevent replay and races.
- **FR-PERM-004:** High-risk approval shall not be satisfied by model-generated text or agent identity.
- **FR-PERM-005:** Native OS permissions, SELinux/LSM, sandbox and secure boot remain authoritative.
- **FR-PERM-006:** Privileged operations shall fail closed if policy state is unavailable.
- **FR-PERM-007:** Security decisions shall emit append-only audit events with secret redaction.
- **FR-PERM-008:** Users shall inspect active grants, scope, expiry and revocation state.
- **FR-PERM-009:** Permission prompts shall explain action, target, data scope and consequences.
- **FR-PERM-010:** Read, write, execute, network and device-control capabilities shall be distinct.

### 14.6 Storage and personal data
- **FR-STOR-001:** File APIs shall use scoped handles or equivalent capability access, not unrestricted paths.
- **FR-STOR-002:** File operations shall validate traversal, symlinks, mount boundaries and ownership.
- **FR-STOR-003:** Bulk/destructive operations shall provide preview, confirmation and recovery where possible.
- **FR-STOR-004:** Storage service shall report quotas, free space and progress.
- **FR-STOR-005:** Sensitive data shall use platform encryption facilities where available.
- **FR-STOR-006:** Backup/restore shall preserve integrity and disclose exclusions.
- **FR-STOR-007:** Temporary data shall have retention and cleanup policies.
- **FR-STOR-008:** Agent access shall be limited to exact files and operations authorized by the user.

### 14.7 Application lifecycle and compatibility
- **FR-APP-004:** App Broker shall delegate install/update/uninstall to native package manager or documented Linux runtime.
- **FR-APP-005:** Application identity and signing state shall be checked before privileged lifecycle operations.
- **FR-APP-006:** Application permissions shall remain controlled by the platform.
- **FR-APP-007:** Compatibility claims shall identify platform, OS release, app version and test status.
- **FR-APP-008:** Incompatible packages shall not be silently converted or installed.

### 14.8 Notifications and user interaction
- **FR-NOTIF-001:** Notifications shall support channels, priority, grouping and user-controlled interruption.
- **FR-NOTIF-002:** Lock-screen visibility shall respect private-content settings.
- **FR-NOTIF-003:** Notification actions that create side effects shall use the same permission policy as other tools.
- **FR-NOTIF-004:** Users shall configure, disable or snooze notification categories.
- **FR-NOTIF-005:** Critical system notifications shall be distinguishable from agent-generated notifications.

### 14.9 Network and connectivity
- **FR-NET-001:** Network access shall be mediated by native platform permissions and per-service policy.
- **FR-NET-002:** AI providers shall be selected by user policy, privacy class, availability, cost and capability.
- **FR-NET-003:** Cloud-bound payloads shall be minimized and private-context transfer disclosed.
- **FR-NET-004:** Offline degradation shall be supported; only safe operations may be queued.
- **FR-NET-005:** Credentials shall be scoped, revocable and excluded from logs.
- **FR-NET-006:** Privileged local services shall not bind to all network interfaces without security review.

### 14.10 Power, thermal and hardware safety
- **FR-PWR-001:** The system shall observe platform thermal and battery signals where available.
- **FR-PWR-002:** MOMO shall never override kernel, firmware or hardware thermal protections.
- **FR-PWR-003:** Background AI work shall be deferrable, cancellable and subject to power/thermal budgets.
- **FR-PWR-004:** Telemetry shall report unknown when the platform exposes no reliable data.
- **FR-PWR-005:** Performance modes shall be exposed only through verified adapters.

### 14.11 AI model, agent and memory behavior
- **FR-AI-015:** Provider adapters shall declare data handling, context limits, tool support, availability and credential source.
- **FR-AI-016:** Provider secrets shall be user-supplied or managed by an approved secret manager; never hardcoded.
- **FR-AI-017:** Model routing shall support local-only, cloud-allowed and offline policies.
- **FR-AI-018:** Agent delegation shall preserve initiating-user policy and cannot expand authority.
- **FR-AI-019:** Memory writes shall record provenance, scope, retention and consent state.
- **FR-AI-020:** Users shall inspect, correct and delete assistant memory through defined controls.
- **FR-AI-021:** Model planning output shall be separate from verified execution results.
- **FR-AI-022:** The assistant shall disclose uncertainty and clarify assumptions when errors could cause harm.
- **FR-AI-023:** Provider failure shall not corrupt task state or bypass approval.
- **FR-AI-024:** Evaluations shall report dataset, hardware, provider/model version, success criteria, cost and latency.

### 14.12 Updates, recovery and lifecycle
- **FR-UPD-007:** Update metadata shall bind target device, platform version, source revision and artifact hashes.
- **FR-UPD-008:** Update installation shall verify signatures and rollback constraints before writing.
- **FR-UPD-009:** Updates shall preserve user data according to the device's supported update model.
- **FR-UPD-010:** Interrupted updates shall recover to a bootable state where transactional updates are supported.
- **FR-UPD-011:** Channels shall distinguish development, beta, candidate and stable.
- **FR-UPD-012:** End-of-life devices shall be clearly identified without false security-update promises.

## 15. Data model and retention

Core logical entities:
- DeviceProfile: exact identity, platform, firmware, components, capability evidence, adapter versions and support tier.
- Capability: identifier, status, evidence, permission requirements and last verification.
- Principal: service, agent, application or user identity.
- Grant: principal, capability, resource scope, risk ceiling, expiry, use limit, approval binding and revocation state.
- Task: goal, owner, risk, state, accepted plan digest, deadline, budget and timestamps.
- TaskStep: agent/tool, input schema, dependencies, risk, preconditions and acceptance criteria.
- TaskEvent: append-only transition, authorization, execution and verification record.
- MemoryRecord: content reference, provenance, scope, retention and consent.
- AuditEvent: actor, action, target, outcome, correlation ID, timestamp and redacted metadata.
- BuildArtifact: source revision, toolchain, target profile, hash, signature and provenance.

Retention periods and deletion guarantees must be finalized before stable release. Audit retention must not become a backdoor for retaining raw private content.

## 16. Quality attributes and measurable targets

These are objectives, not current performance claims, and must be measured on declared hardware:
- **NFR-PERF-006:** Core shell input feedback target p95 ≤100 ms on qualified reference hardware.
- **NFR-PERF-007:** Local warm core-service health query target p95 ≤250 ms.
- **NFR-REL-005:** Task journal shall survive process restart and power-loss simulation without invalid transitions.
- **NFR-REL-006:** Optional AI/provider failure shall not prevent core boot or non-AI use.
- **NFR-SEC-005:** No unresolved critical/high privilege-bypass finding at stable release.
- **NFR-PORT-005:** Shared contract tests shall run against every maintained adapter.
- **NFR-OBS-001:** Every side effect shall be traceable from task ID through authorization, adapter and verification.
- **NFR-ACCESS-001:** First-party UI shall pass keyboard, screen-reader, scaling and RTL checks.
- **NFR-ENERGY-001:** Background AI shall obey per-device battery and thermal policy; numeric budgets follow baseline measurement.

## 17. External interface contracts

Every service API shall define version, compatibility policy, authenticated caller identity, typed request/response, maximum payload, timeout/cancellation, error taxonomy, capability requirements, audit/correlation, idempotency and negative security tests.

Android may use Binder/AIDL and native services. Linux may use D-Bus, authenticated Unix sockets, portals and isolated daemons. These are implementation choices; MOMO contracts remain platform-neutral.

## 18. Verification matrix

| Layer | Required evidence | Release relevance |
|---|---|---|
| Static/repository | Schemas, manifests, docs, secrets, license and source checks | Every PR |
| Unit | Deterministic policy, state, routing and data logic | Every PR |
| Integration | IPC, service, database, provider and adapter behavior | Each subsystem |
| Emulator | Image boot, health, UI and failure injection | Each platform build |
| Hardware | Exact SKU boot, radios, display, input, camera, audio, power and security | Each device claim |
| Security | Threat model, adversarial tests and independent review | Before candidate/stable |
| Release | Signatures, SBOM, provenance, update, rollback and restore | Every release |

A pass at one layer does not imply a higher layer passed.

## 19. Requirement traceability and change control

Each requirement shall have unique ID, priority, owner/workstream, implementation path, positive/negative tests, evidence link, tested revision and status (specified, implemented, CI-tested, image-integrated, emulator-tested, hardware-tested, release-qualified). Changes require rationale, impact analysis, tests and revision history.

## 20. Product acceptance gates

- **AC-001:** SRS, architecture, threat model, platform strategy and support tiers approved.
- **AC-002:** Pinned Buildroot build, non-empty artifacts, QEMU serial boot, readiness marker and target smoke tests pass.
- **AC-003:** Tasks, plans, grants and audit events persist/recover after restart and fault injection.
- **AC-004:** Unauthorized calls fail at OS sandbox/permission boundary; high-risk approval is exact and replay-resistant.
- **AC-005:** Selected Android and Linux baselines build from pinned manifests with license/provenance.
- **AC-006:** Exact SKU boots repeatedly with logs and verified restore procedure.
- **AC-007:** Essential hardware, encryption, thermal/power, update and recovery pass device tests.
- **AC-008:** Assistant uses bounded tools, approvals and independent verification and passes adversarial evaluation.
- **AC-009:** Signed artifacts, SBOM, provenance, security review, release notes and rollback evidence exist.
- **AC-010:** At least two distinct device families pass their declared support tier before broad multi-device maturity is claimed.

## 21. Open decisions requiring ADRs

- Android base, API baseline and kernel maintenance strategy.
- Mainline Linux mobile target, compositor/shell, init and package/runtime.
- First exact Android SKU and first Linux mobile device.
- Secure IPC and capability token format.
- Tool sandbox technology per platform.
- Local model runtimes and minimum hardware classes.
- Memory retention/deletion and cloud data policy.
- Signing infrastructure, key custody and OTA design.
- Supported languages and formal accessibility target.
- MOMO-owned code license and contribution governance.

No unresolved decision may be silently treated as selected. Each ADR records alternatives, evidence, decision, consequences and review date.

## Implementation Evidence Addendum — Durable Step Execution Journal (2026-11-13)

The following is an implementation update, not a claim that the complete task execution subsystem is finished.

| Capability | Evidence level | Current result | Remaining limitation |
|---|---|---|---|
| Per-step durable execution state | CI-tested; overlay-integrated | SQLite journal stores one record per task/step and append-only lifecycle events; TaskCoordinator registers every accepted plan step in the same transaction as task and immutable plan | QEMU image validation and real executor integration remain pending |
| Attempt accounting and retry budget | CI-tested | Explicit bounded retries are restricted to R0/R1 read-only work | No scheduler, deadline manager or backoff service |
| Side-effect failure handling | CI-tested | R2-R4 failures enter `needs_review` | No independent reconciliation adapter |
| Restart recovery | CI-tested; boot-hook-integrated | `momoctl boot-check` invokes the idempotent `momo-task recover` command before readiness; in-flight steps become `needs_review` and are never replayed | QEMU boot validation and future worker-supervisor ordering remain pending |
| Cancellation | CI-tested | Queued work can be cancelled; running work requires executor acknowledgement that no side effect occurred | No running process executor exists yet |
| Result evidence | CI-tested | Optional SHA-256 result digest is persisted | No independent result verifier or signed evidence envelope |

**Traceability:** This increment contributes partial implementation evidence toward FR-AI-011, NFR-REL-001 and NFR-REL-002. It does not close those requirements. The journal is not a tool executor, permission authority or OS sandbox. Native Linux/Android enforcement, authenticated IPC, actual executor integration and image-level validation remain mandatory.

## Implementation Evidence Addendum — Persisted Dependency Readiness (2026-11-13)

TaskCoordinator now derives dependency completion only from durable per-step records whose state is `succeeded`. The API no longer accepts caller-supplied completed-step IDs. A step is returned as ready only when its dependencies are durably successful and its own journal state is `ready`. Failed, running, cancelled and `needs_review` steps do not unblock downstream work. The coordinator verifies that the journal's step IDs and risk levels match the immutable accepted plan.

This is CI-tested and included in the Buildroot overlay source. It is not a concurrent scheduler or execution engine: dispatch, deadlines, backoff, fairness, quotas, durable output verification and OS-enforced isolation remain open requirements.

## Implementation Evidence Addendum — Tamper-Evident Step Events (2026-11-13)

The per-step event history now includes a SHA-256 hash chain, verifies the chain before returning event history, and uses SQLite triggers to reject ordinary event updates and deletions. A migration backfills deterministic hashes for databases created by the earlier event-table schema. CI covers normal verification, blocked mutation, tampering after trigger removal and legacy migration.

This is tamper-evident against accidental or partial record modification, not a cryptographic signature or protection against a privileged attacker who can rewrite the database and recompute the chain. Protected key custody, external audit anchoring, native file permissions and OS isolation remain required for stronger assurance.

The journal also verifies the existing event chain before appending. A corrupted history blocks the new transition and the transaction rolls back; new events cannot silently extend a compromised chain.

The integrity check also gates state reads and dependency scheduling: TaskCoordinator verifies all relevant step event chains before returning readiness. Corrupt history blocks the read/scheduling path instead of allowing untrusted state to authorize progress.


## Linux IPC Protocol Foundation — Implementation Note (2026-11-13)

A versioned, bounded local IPC framing layer has been added alongside the Linux peer-credential helper. Version 1 uses a four-byte network-order length prefix and a 64 KiB payload ceiling. The parser rejects duplicate JSON keys, non-finite values, invalid UTF-8, malformed/truncated/trailing frames, unsupported versions and invalid request fields. Source and Buildroot overlay parity is tested.

This is partial evidence toward the local service protocol requirements. The parser does not authenticate peers, authorize operations, prevent replay, impose deadlines or dispatch tools. It is not wired into a daemon. No tool execution is enabled.

## IPC Service Increment — 2026-11-13 (PR #38 candidate)

A first unprivileged local status service is implemented as a narrow integration milestone. Buildroot provisions a dedicated `momo-ipc` account; init starts the daemon under that account; AF_UNIX peers are authenticated through `SO_PEERCRED`; only the root UID is accepted by the current single-user image policy; and only the read-only `status.read` operation is dispatched. The `momoctl ipc-status` client exposes the status response. No command or tool execution exists in this service.

Acceptance remains conditional on CI and a fresh QEMU image run. This does not satisfy the full security or execution requirements: replay protection, multi-user roles, per-operation capability grants, sandboxing, resource quotas, and Android Binder/SELinux/AppOps remain open.


## IPC Replay Protection Increment — 2026-11-13 (PR #39 candidate)

The read-only IPC service adds a bounded process-lifetime replay cache (1,024 request IDs), rejects duplicate IDs before dispatch, and uses unique CLI request IDs. Client response validation rejects duplicate JSON keys, unexpected fields and mismatched request IDs. This is not durable replay protection across daemon restart and is not sufficient for side-effecting operations.


## IPC Process Restriction Increment — 2026-11-13 (PR #40 candidate)

The unprivileged IPC daemon now applies bounded core/file/descriptor/CPU/address-space limits and Linux `PR_SET_NO_NEW_PRIVS` before opening its listening socket. These are defense-in-depth process restrictions only; syscall filtering, namespaces, cgroups and LSM policy remain required for a real sandbox.
