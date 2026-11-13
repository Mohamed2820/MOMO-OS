# MOMO Tool and Permission Model

Status: normative design for MOMO-owned services.

## Principle
The model never receives ambient operating-system authority. It proposes typed actions; a trusted broker decides whether and how they may execute.

## Capability format
A grant is scoped to a subject, action, resource, data classification, expiry, and optional use limit. Grants are revocable and auditable. Wildcard root or unrestricted shell grants are prohibited for normal assistant operation.

## Risk classes
- **R0 — Public/read-only:** public information and non-sensitive device state.
- **R1 — Private read:** user files, notifications, contacts, calendar, location, microphone, camera. Requires explicit scoped permission.
- **R2 — Reversible write:** create or edit a draft, organize files in a designated workspace, change a reversible preference.
- **R3 — External side effect:** send, publish, share, purchase, invite, or communicate with another person. Per-action confirmation.
- **R4 — Destructive/security/device integrity:** delete data, change security controls, alter accounts, install privileged components, bootloader/partition/firmware operations. Explicit confirmation and additional safeguards; some operations may be unsupported entirely.

## Android enforcement
- Use Android runtime permissions and platform AppOps for ordinary app capabilities.
- Privileged system APIs must be signature-protected and exposed only to MOMO-signed components.
- Enforce SELinux in enforcing mode; do not make permissive mode a product feature.
- Use scoped storage and Storage Access Framework where applicable.
- Do not bypass package sandboxing or silently elevate application privileges.
- Use Android Keystore for cryptographic secrets where available.

## Approval UX
An approval screen states: requesting agent, exact action, target/resource, data involved, consequence, reversibility, and duration. Approvals are single-use by default. Users can revoke standing grants from a central permission dashboard.

## Audit events
Record task ID, agent role, tool ID/version, capability scope, approval reference, timestamp, result, and verification evidence. Redact tokens, passwords, message bodies, and sensitive payloads unless the user explicitly chooses to retain them.

## Schema
See `security/capability.schema.json`. The schema is a contract, not an implementation of Android authorization.
