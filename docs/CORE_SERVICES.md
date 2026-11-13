# MOMO Core Services Blueprint

Status: specification baseline; implementation is incremental.

## Service model
MOMO services are platform-neutral processes or libraries with versioned APIs. Android implementations may use Binder/AIDL and platform services; Linux implementations may use D-Bus, portals, and narrowly scoped daemons. No shared service may assume root or a writable system partition.

## Core services
- Device Inventory: reads a signed/validated device profile and discovers runtime capabilities. Unknown is not supported.
- Permission Broker: evaluates identity, capability, resource, risk, expiry, user approval, and audit requirements.
- Task Coordinator: durable task state machine, cancellation, deadlines, retries, idempotency keys, and verification.
- Storage Broker: scoped file handles, user consent, encryption-at-rest integration, quotas, and backup/restore.
- App Broker: platform-specific package discovery and launch; Android package manager on Android track, Linux package/runtime adapters on Linux track.
- Notification Broker: channels, priorities, actions, privacy visibility, and user controls.
- Power & Thermal Manager: platform telemetry and policy hints; never overrides thermal safety.
- Update Manager: signed metadata, staged rollout, A/B or platform-native update integration, rollback and recovery checks.
- Audit Service: append-only security-relevant event stream with redaction and retention policy.
- AI Orchestrator: model/provider abstraction, agent scheduling, tool mediation, evaluations and offline fallback.

## API rules
- Version all public interfaces and maintain compatibility tests.
- Typed requests and responses; no arbitrary command or ambient filesystem access.
- Explicit deadlines, cancellation, bounded payloads and structured errors.
- Every side effect emits an audit record and returns a correlation ID.
- Services fail closed for privileged operations and degrade gracefully for optional features.
- Secrets are stored in platform-backed secure storage where available; never in logs or source control.

## Implementation order
1. Device inventory and permission broker integration.
2. Task coordinator persistence and event journal.
3. Storage and notification adapters.
4. App and lifecycle adapters.
5. Update, power and thermal services.
6. AI orchestration integration.
7. Production hardening and multi-device conformance.
