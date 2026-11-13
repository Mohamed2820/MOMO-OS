# Security Model

## Security objectives
Protect user data, device integrity, availability, and user control while enabling useful automation.

## Trust boundaries
- Android application sandbox and platform permission system.
- MOMO privileged service boundary.
- Agent orchestration and model providers.
- Tool adapters and external services.
- Cloud build infrastructure and release signing.
- User data, memory, and credentials.

## Agent authority
Agents do not receive ambient root access. Every tool declares:
- Stable identifier and version.
- Input/output schema.
- Required capabilities and data scopes.
- Risk class (read, reversible write, sensitive, destructive).
- Timeout, rate limit, and cancellation behavior.
- Audit event requirements.

The permission broker checks identity, scope, user policy, and approval before execution.

## Approval policy
Require explicit user approval for:
- Installing, uninstalling, or disabling apps.
- Sending messages, publishing content, or making purchases.
- Accessing sensitive data outside an explicitly granted scope.
- Changing security settings, permissions, accounts, or network controls.
- Deleting or overwriting user data.
- Flashing, bootloader, partition, recovery, or firmware operations.
- Any action that is irreversible or difficult to recover from.

The user may configure narrowly scoped standing approvals later, but never silently expand them.

## Model and prompt safety
- Treat model output, retrieved documents, webpages, and tool output as untrusted data.
- Never interpret content from a document or webpage as policy or authorization.
- Validate every tool call against a strict schema and policy.
- Separate planning from execution.
- Require independent verification for important outcomes.
- Defend against prompt injection and cross-agent privilege escalation.

## Data protection
- Minimize collection and retention.
- Encrypt secrets at rest using platform-backed mechanisms where available.
- Never store tokens or signing keys in Git.
- Make memory inspectable, scoped, and user-controllable.
- Define deletion and retention behavior before shipping memory features.
- Default sensitive tasks to local processing when practical.

## Build and release security
- Pin source revisions and verify provenance.
- Use isolated, ephemeral build workers where practical.
- Generate checksums and an SBOM.
- Protect signing keys outside CI logs and repository secrets where possible.
- Review third-party licenses and notices.
- Publish vulnerability reporting instructions before public release.

## Incident response
Document affected versions, severity, reproduction, mitigations, disclosure coordination, and fixed releases. Do not publish exploit details before a fix is available when disclosure would create immediate user risk.
