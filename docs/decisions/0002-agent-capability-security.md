# ADR 0002: Capability-mediated AI execution

- Status: Accepted
- Date: 2026-11-13

## Context
MOMO aims to provide powerful multi-agent automation. Giving model processes ambient root or unrestricted shell access would make prompt injection, model errors, and compromised providers equivalent to device compromise.

## Decision
Agents may only propose typed tool calls. A trusted permission broker validates identity, schema, capability scope, risk, and approval before execution. System-level operations use narrow privileged APIs protected by Android signatures and SELinux. No unrestricted root shell is exposed to the general agent runtime.

## Consequences
- More implementation work is required for each tool.
- User approvals and audit records become first-class product features.
- The model can plan broadly without gaining broad authority.
- Security tests can target a stable broker boundary.
- Some desired automations may be unavailable unless Android exposes a safe supported API.
