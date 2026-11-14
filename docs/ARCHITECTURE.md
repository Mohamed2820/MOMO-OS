# Technical Architecture

## System model
MOMO OS is a layered Android-derived platform plus MOMO-owned services and experiences. Upstream platform source remains upstream; this repository coordinates integrations and owns overlays, specifications, and MOMO-specific code.

## Layers

### 1. Platform base
Candidate: AOSP-derived distribution, with LineageOS evaluated as a practical integration base. Final selection is blocked on device feasibility, licensing review, build reproducibility, and maintainability. No base is selected as final yet.

### 2. Device adaptation
Contains product/device configuration, kernel integration, vendor interfaces, HAL dependencies, boot/recovery integration, SELinux policy, AVB and partition configuration. Device support is a separate gate, not inferred from a generic Android build.

### 3. System services
MOMO-owned privileged services should expose narrow, typed APIs:
- Permission and capability broker.
- Automation/task execution broker.
- File and content access broker.
- App launch and lifecycle integration.
- Notification and context broker.
- Audit and policy service.

Privileged operations must be mediated by Android platform permissions, signature-level controls, SELinux, and explicit user approvals as appropriate. Do not expose arbitrary shell execution as the default agent interface.

### 4. User experience
Mobile shell, launcher integration, desktop mode, window/task management, voice interface, accessibility, settings, and activity history. Prefer modular apps and overlays before invasive framework changes.

### 5. Intelligence plane
A provider-agnostic orchestration service:
- Intent intake and clarification.
- Planner and task decomposition.
- Specialist agent registry.
- Model/provider router.
- Tool registry with typed schemas.
- Short-term task state and user-approved long-term memory.
- Independent verification and evidence collection.
- Budget, timeout, retry, and cancellation controls.

### 6. Cloud engineering
Manifest-driven source acquisition, pinned revisions, isolated build workers, CI validation, artifact provenance, SBOM generation, signing, and release channels.

## Multi-agent execution lifecycle
1. Parse request and identify constraints.
2. Decide whether the task is informational or requires action.
3. Build a plan with dependencies and risk labels.
4. Delegate bounded subtasks to specialist agents.
5. Validate proposed tool calls against policy and schemas.
6. Request human approval for sensitive, irreversible, or externally visible actions.
7. Execute through a broker with timeouts and idempotency where possible.
8. Independently verify outcomes using authoritative state, not agent claims.
9. Summarize results, evidence, and any incomplete work.
10. Store only user-authorized memories and task artifacts.

## Suggested specialist roles
- Orchestrator: owns task state and coordination.
- Research: gathers evidence and citations.
- Planner: decomposes work and tracks dependencies.
- Developer: proposes code changes.
- Reviewer: reviews diffs, tests, and security.
- Device engineer: handles kernel, HAL, and hardware compatibility.
- Security auditor: threat models and permission review.
- QA verifier: executes acceptance tests and confirms results.

Agents are roles, not independent authorities. All privileged actions flow through the same policy broker.

## Hybrid AI routing
Route tasks across on-device and remote models using privacy classification, capability, latency, cost, network availability, and user policy. Sensitive data defaults to local processing when feasible. Provider credentials are user-supplied and stored outside source control.

## Key architecture decisions
- ADRs live in `docs/decisions/`.
- Prefer stable interfaces and modular components.
- Keep upstream patches small and documented.
- Do not couple system boot or emergency functions to an AI service.


## MOMO CELL — autonomous maintenance subsystem

MOMO CELL is a first-class, separately bounded maintenance subsystem. Its v1 registry contains Guardian, Builder, and Contract specialist cells. It performs deterministic repository health checks, emits structured findings and repair proposals, and runs from repository validation plus a scheduled GitHub Actions health cycle. It is not on the boot-critical path and cannot prevent core OS startup when unavailable.

The initial implementation is read-only: it cannot edit files, execute shell commands, mint credentials, grant itself permissions, or merge changes. Any future repair worker must submit typed work through the task planner and ExecutionGate, use an isolated branch/worker, pass tests and platform acceptance, and open a reviewed pull request. Protected security and execution-gate code require independent approval. See [MOMO CELL design](MOMO_CELL.md).
