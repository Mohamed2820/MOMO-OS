# MOMO OS

**AI-native hybrid mobile operating system — cloud-first development workspace.**

MOMO OS aims to create a capable mobile computing environment by reusing mature open-source platform components and adding a purpose-built multi-agent AI layer, system services, interface, and security architecture.

> **Status:** Architecture, initial runtime core, and feasibility research. No ROM is currently declared buildable or installable. Samsung Galaxy A17 (SM-A175F) is a research target only; compatibility is not confirmed.

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

- `docs/` — vision, architecture, runtime, security, feasibility, UX and roadmap.
- `manifests/` — upstream source manifests and pinned dependency records.
- `platform/` — MOMO-owned platform overlays and device integration.
- `intelligence/` — runtime core, orchestrator, agents, memory, model router and tools.
- `interfaces/` — mobile, desktop and voice experiences.
- `infrastructure/` — cloud build and runtime configuration.
- `security/` — threat models, capability schemas and permission policies.
- `tests/` — automated validation and compatibility checks.
- `.github/workflows/` — repository-level validation workflows.

## Technical specifications

- [Vision](docs/VISION.md)
- [Technical architecture](docs/ARCHITECTURE.md)
- [AI runtime](docs/AI_RUNTIME.md)
- [Agent methodology](docs/AGENT_METHODOLOGY.md)
- [Tool and permission model](docs/TOOL_AND_PERMISSION_MODEL.md)
- [Desktop experience](docs/DESKTOP_EXPERIENCE.md)
- [Cloud build pipeline](docs/CLOUD_BUILD.md)
- [Test strategy](docs/TEST_STRATEGY.md)
- [Device research: SM-A175F](docs/DEVICE_RESEARCH.md)
- [Roadmap](docs/ROADMAP.md)

## Device feasibility gate

Initial target: Samsung Galaxy A17 LTE, model SM-A175F. Do not confuse it with SM-A176B (Galaxy A17 5G). Before selecting a ROM base or generating flashable images, verify exact firmware/CSC, bootloader unlockability, partition layout, kernel source/configuration, vendor components, device tree completeness, AVB/vbmeta behavior, and a tested recovery/restore path. A recovery tree or kernel repository is not proof of ROM support.

## Security principles

- AI agents use explicit, least-privilege tools.
- Sensitive or destructive operations require human approval.
- Privileged actions must be auditable.
- Never commit API keys, signing keys, passwords, or personal tokens.
- Model output is not evidence that an operation succeeded.

## Licensing

MOMO-owned code will receive an explicit license before redistribution. Third-party components retain their own licenses and notices. See [Licensing Policy](docs/LICENSING.md).
