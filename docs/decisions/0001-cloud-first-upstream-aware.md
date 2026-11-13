# ADR 0001: Cloud-first, upstream-aware development

- Status: Accepted
- Date: 2026-11-13

## Context
The maintainer works primarily from an Android phone and does not want large source trees or build environments downloaded locally at the start of the project. Android platform source is distributed across many Git repositories and requires substantial build resources.

## Decision
Use GitHub as the project control plane. Keep this repository focused on MOMO-owned code, documentation, manifests, integration metadata, and automation. Track large upstream projects through manifests and pinned revisions. Use forks only where ongoing MOMO-specific changes justify them. Perform source checkout and platform builds in cloud infrastructure.

## Consequences
- The main repository stays relatively small and reviewable.
- Upstream provenance and update paths remain visible.
- Large source downloads happen only on cloud build workers.
- Some workflows require a separately provisioned cloud build host; GitHub Actions alone may be insufficient for full Android builds.
- Cloud cost, build duration, credentials, and artifact retention must be managed explicitly.
- Device-specific feasibility remains a hard gate before flashable artifacts.
