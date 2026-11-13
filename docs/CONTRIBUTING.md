# Contributing to MOMO OS

## Before contributing
Read the vision, architecture, security model, upstream policy, licensing policy, and device feasibility gate.

## Workflow
1. Create a focused branch.
2. Keep changes small and explain the motivation.
3. Include tests or a validation plan.
4. Update docs when behavior, architecture, dependencies, or security assumptions change.
5. Never commit credentials, signing keys, private user data, or vendor blobs without a license review.
6. Open a pull request with risks, compatibility notes, and evidence.

## Code standards
- Prefer typed interfaces and explicit error handling.
- Validate untrusted inputs.
- Use least privilege.
- Log security-relevant events without leaking secrets.
- Avoid silent destructive behavior.
- Document assumptions and unsupported cases.

## Review requirements
Changes to privileged services, permissions, SELinux, boot, recovery, signing, or device flashing require security and device-owner review before merge.
