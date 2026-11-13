# MOMO OS

**AI-native hybrid mobile operating system — cloud-first development workspace.**

MOMO OS aims to create a capable mobile computing environment by reusing mature open-source platform components and adding a purpose-built multi-agent AI layer, system services, interface, and security architecture.

> **Status:** Architecture and feasibility foundation. No ROM is currently declared buildable or installable. Samsung Galaxy A17 (SM-A175F) is an initial research target only; compatibility is not confirmed.

## Engineering strategy

**Reuse → Integrate → Modify → Extend → Verify**

- Track upstream projects through manifests and pinned revisions.
- Fork only components that need sustained MOMO-specific development.
- Keep MOMO-owned code and patches separate from upstream sources where practical.
- Record provenance, revision, license, patches, and synchronization procedure for every dependency.
- Use cloud environments for source checkout and Android builds; do not require large local source checkouts on the maintainer's phone.
- Public visibility is not permission to ignore license obligations.

## Architecture

| Layer | Responsibility |
|---|---|
| Platform base | AOSP/LineageOS-derived Android platform |
| Device support | Device tree, kernel, vendor components, HAL and hardware validation |
| MOMO system services | Permission broker, automation, app/task integration and system APIs |
| MOMO interface | Mobile shell, desktop mode, windows, voice and accessibility |
| MOMO intelligence | Multi-agent orchestration, planning, memory, model routing, tools and evaluation |
| Security | Least privilege, sandboxing, approvals, audit logs and secret handling |
| Cloud engineering | Source manifests, reproducible builds, CI, tests and release provenance |

## Repository map

- `docs/` — vision, architecture, decisions, security, feasibility and roadmap.
- `manifests/` — upstream source manifests and pinned dependency records.
- `platform/` — MOMO-owned platform overlays and device integration.
- `intelligence/` — orchestrator, agents, memory, model router and tools.
- `interfaces/` — mobile, desktop and voice experiences.
- `infrastructure/` — cloud build and runtime configuration.
- `security/` — threat models and permission policies.
- `tests/` — automated validation and compatibility checks.
- `.github/workflows/` — repository-level validation workflows.

## Device feasibility gate

Initial target reported by the maintainer: Samsung Galaxy A17, model SM-A175F, ARM64, Android 16. Before selecting a ROM base or generating flashable images, verify exact product codename, bootloader unlockability, partition layout, kernel source/configuration, vendor components, device tree completeness, AVB/vbmeta behavior, and a tested recovery/restore path. A recovery device tree is not proof of ROM support.

## Security principles

- AI agents use explicit, least-privilege tools.
- Sensitive or destructive operations require human approval.
- Privileged actions must be auditable.
- Never commit API keys, signing keys, passwords, or personal tokens.
- Model output is not evidence that an operation succeeded.

## Licensing

MOMO-owned code will receive an explicit license before redistribution. Third-party components retain their own licenses and notices. See [Licensing Policy](docs/LICENSING.md).
