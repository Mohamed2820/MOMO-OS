# MOMO OS — Versioned Core Service API Contracts

**Status:** Normative contract baseline for implementation planning. The contracts below define operation boundaries and error semantics; they do not claim that the services are implemented.

## 1. Design rules

1. MOMO services expose typed, versioned operations rather than shell commands.
2. The caller's identity is derived from the authenticated transport or platform principal. A request body cannot assert its own trusted identity.
3. Every operation declares required capabilities, data scope, risk, timeout, cancellation semantics and audit behavior.
4. Unknown capabilities are unavailable. Unsupported operations return an explicit error and never simulate success.
5. Side effects require an idempotency strategy and independently verifiable result.
6. APIs remain platform-neutral. Android Binder/AIDL and Linux IPC/D-Bus adapters implement the same semantic contract but use different native security boundaries.
7. Service startup and optional AI availability must not block core boot, recovery or emergency functions.

## 2. Common request envelope

A future request envelope contains:

| Field | Type | Rule |
|---|---|---|
| `protocol_version` | integer | Required; exact supported major version |
| `request_id` | string | Unique, bounded to 128 characters |
| `operation` | string | Stable operation identifier |
| `task_id` | string/null | Required when invoked by task runtime |
| `step_id` | string/null | Required for a plan step |
| `deadline` | timestamp | Absolute UTC deadline; server enforces maximum horizon |
| `idempotency_key` | string/null | Required for mutating operations where supported |
| `arguments` | object | Operation-specific strict schema; unknown keys rejected |

The authenticated principal, UID/GID, Android UID, signing identity and effective capabilities are transport-derived metadata. They are not accepted as caller-controlled fields.

## 3. Common response envelope

| Field | Type | Rule |
|---|---|---|
| `protocol_version` | integer | Version used to encode the response |
| `request_id` | string | Echo of validated request ID |
| `ok` | boolean | True only when the operation's defined completion condition is met |
| `result` | object/null | Typed operation result |
| `error` | object/null | Stable error code and safe diagnostic |
| `audit_id` | string | Correlates request, policy decision and service event |
| `started_at` / `finished_at` | timestamp | Service-observed times |

The response must not leak raw secrets, tokens, private payloads or internal filesystem paths.

## 4. Common error model

| Code | Meaning | Retry guidance |
|---|---|---|
| `INVALID_ARGUMENT` | Schema or value invalid | Do not retry without corrected input |
| `UNAUTHENTICATED` | Transport principal missing/invalid | Re-establish authenticated session |
| `PERMISSION_DENIED` | Principal lacks required capability | Do not retry until permission changes |
| `APPROVAL_REQUIRED` | Exact user approval missing | Request approval through UX |
| `APPROVAL_EXPIRED` | Approval token expired | Obtain a new approval |
| `APPROVAL_REPLAYED` | Single-use approval already consumed | Never replay |
| `UNSUPPORTED` | Platform or adapter does not implement operation | Do not retry on same target |
| `CAPABILITY_UNAVAILABLE` | Required hardware/service not currently available | Retry only after state change |
| `CONFLICT` | State changed since request was planned | Refresh canonical state and re-plan |
| `DEADLINE_EXCEEDED` | Deadline reached | Read-only may retry within policy; side effects require reconciliation |
| `CANCELLED` | Cancellation safely completed | Terminal for this request |
| `OUTCOME_UNKNOWN` | Side effect may have occurred but cannot be confirmed | Enter needs_review; reconcile before retry |
| `RESOURCE_EXHAUSTED` | Quota, rate, memory or concurrency budget exhausted | Backoff within caller policy |
| `INTERNAL` | Unexpected service failure | Return audit ID; do not expose stack trace |

## 5. Service catalog and operation contracts

### 5.1 Device Inventory Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `device.identity.read` | R0 | `device.identity` | Platform track, architecture, OS/kernel and exact profile identity if verified |
| `device.capabilities.read` | R0 | `device.capabilities` | Capability IDs and state: supported, unsupported, temporarily_unavailable, permission_denied, unknown |
| `device.health.read` | R1 | `device.health` | Battery/thermal/health snapshot, only when platform supports it |

Identity and capability reporting must preserve evidence provenance and timestamp. Unknown is never promoted to supported.

### 5.2 Permission and Approval Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `permission.grant.create` | R2/R3 | `permission.manage` | Scoped grant ID, subject, action, resource, expiry and use limit |
| `permission.grant.revoke` | R2 | `permission.manage` | Revocation receipt and audit ID |
| `permission.grants.list` | R1 | `permission.read` | Redacted active/revoked grant metadata |
| `approval.request` | R2 | `approval.request` | User-visible approval request bound to exact operation |
| `approval.respond` | R3/R4 | Authenticated user session | Single-use decision reference; approver identity from session |

Agents may request approval but cannot issue, approve or expand grants. A model-generated `approved=true` field has no authority.

### 5.3 Task and Execution Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `task.create` | R2 | `task.create` | Task ID and accepted plan digest |
| `task.read` | R1 | `task.read` | Task state, redacted events and progress |
| `task.cancel` | R2 | `task.cancel` | Cancellation request and current state; not false confirmation of stopped side effects |
| `task.steps.read` | R1 | `task.read` | Durable step states, attempts and event verification status |
| `task.reconcile` | R2/R3 | `task.reconcile` | Authoritative reconciliation evidence for needs_review steps |

There is no public `task.execute_arbitrary_command` operation. Step dispatch is internal to the trusted executor after plan, dependency, capability and approval checks.

### 5.4 Storage Broker

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `storage.list` | R1 | Scoped directory handle | Bounded entries and metadata |
| `storage.read` | R1 | Scoped file handle | Stream or bounded content response |
| `storage.create` | R2 | Scoped directory handle | Created object ID and metadata |
| `storage.write` | R2 | Scoped file handle | Version/digest and write receipt |
| `storage.move` / `storage.rename` | R2 | Source and destination scopes | Operation receipt |
| `storage.delete` | R4 | Explicit exact-object approval | Tombstone/recovery receipt where supported |

Paths supplied by agents must never be treated as trusted absolute paths. The broker resolves scoped handles, rejects traversal and symlink escapes, enforces quotas and records audit IDs.

### 5.5 Application Broker

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `app.list` | R1 | `apps.metadata` | Installed application metadata allowed by platform policy |
| `app.launch` | R2 | `apps.launch` | Launch request result and target identity |
| `app.install` / `app.uninstall` | R4 | Explicit exact-package approval | Package manager result and signer identity |

The broker cannot silently downgrade signature, package integrity or platform install protections.

### 5.6 Notification Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `notification.list` | R1 | Explicit notification access | Redacted notification metadata |
| `notification.dismiss` | R2 | Exact notification ID | Dismissal receipt |
| `notification.reply` | R3 | Exact conversation and message approval | Delivery result or OUTCOME_UNKNOWN |

Notification content is sensitive user data. It is not available to every agent by default.

### 5.7 Connectivity Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `network.status.read` | R0/R1 | `network.status` | Connection type and sanitized state |
| `network.wifi.set` | R2 | `network.configure` | Configuration receipt |
| `network.vpn.set` | R3 | `network.configure` plus approval | VPN state and audit evidence |

The service must not expose arbitrary packet capture, credential extraction or unrestricted network sockets.

### 5.8 Power and Thermal Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `power.status.read` | R0 | `power.status` | Battery, charging and power state |
| `power.profile.set` | R2 | `power.configure` | Applied profile and actual state |
| `device.shutdown` / `device.reboot` | R3 | Exact user approval | Request accepted and observed transition state |

Emergency and recovery controls must remain available independently of AI.

### 5.9 Update and Recovery Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `update.check` | R0 | `update.read` | Signed metadata and compatible update candidates |
| `update.download` | R1 | `update.download` | Verified artifact digest |
| `update.stage` | R3 | `update.install` and approval | Staged slot/image metadata |
| `update.apply` | R4 | Explicit approval plus device recovery gate | Update transaction ID and health status |
| `update.rollback` | R4 | Recovery authority | Verified rollback result |

No update is applied without signature verification, exact-device compatibility, power/battery constraints and a tested recovery path.

### 5.10 Audit and Diagnostics Service

| Operation | Risk | Required scope | Result |
|---|---|---|---|
| `audit.events.read` | R1 | `audit.read` | Redacted, paginated audit records |
| `diagnostics.health.read` | R0/R1 | `diagnostics.read` | Service health and sanitized component states |
| `diagnostics.bundle.create` | R2 | `diagnostics.export` | Redacted diagnostic bundle and digest |

Audit events are append-only where feasible. Secrets and private message bodies are redacted by default. Retention and deletion policy must be implemented before production memory/audit release.

## 6. Adapter conformance requirements

Each Android or Linux adapter must publish:
- Adapter ID and semantic version.
- Platform track and supported API/framework/kernel ranges.
- Supported operation IDs and JSON schemas.
- Required/optional capabilities and evidence.
- Risk and permission mapping.
- Timeout, cancellation and idempotency behavior.
- Error-code mapping.
- Unit, integration, emulator and exact-device test references.

The conformance suite must verify that unsupported/unknown capabilities fail closed, caller identity cannot be forged, argument schemas reject unknown fields, approvals are bound to exact targets, and every side effect has an audit ID.

## 7. Versioning and compatibility

- Major version changes may remove or redefine behavior and require explicit migration.
- Minor version changes may add backward-compatible operations or optional result fields.
- Patch changes may clarify errors or fix behavior without changing the contract.
- Clients must reject unsupported major versions and must not silently ignore security-relevant fields.
- Each service advertises supported protocol versions and capability set.
- Database schema version is separate from IPC/API version.

## 8. Implementation sequence

1. Freeze common envelope, error taxonomy and identity rules.
2. Implement Device Inventory read-only service as the first reference service.
3. Implement Permission Service read-only grant inspection and revoke path.
4. Integrate Task/Execution read-only status and cancellation request.
5. Add Storage Broker with scoped handles and path traversal tests.
6. Add App and Notification adapters per platform.
7. Add network, power and update services only after native platform/security integration.
8. Publish adapter conformance tests and generate API documentation from schemas.

## 9. Current implementation status

- The Python platform-neutral adapter protocol exists in `platform_adapters/contracts.py`.
- Device inventory, task storage, permission broker and execution journal exist as source components.
- The Linux IPC daemon currently supports only `status.read`; it is not a general service bus.
- Storage, app lifecycle, notifications, connectivity, power, update/recovery and production audit service APIs are not yet implemented as independently secured services.
- Android Binder/AIDL adapters are not implemented.
- This document is a design contract, not evidence that the listed services exist.
