# MOMO OS

**AI-native, device-adaptive mobile computing platform — cloud-first development workspace.**

MOMO OS aims to become a Linux-like, multi-device mobile platform: one consistent MOMO experience over separately maintained Android-compatible and mainline-Linux platform tracks, with hardware-specific adapters and evidence-based device support.

> **Status:** Architecture, initial runtime core, and feasibility research. No ROM is currently declared buildable or installable. No single phone or Android release defines the product. Galaxy A17 LTE (SM-A175F) is only one possible device-port research candidate; compatibility is not confirmed.

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
| Platform tracks | Android-compatible AOSP/ACK track and mainline-Linux mobile track |
| Device support | Per-device profiles, boot chain, kernel, vendor components, HAL/adapters and hardware validation |
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

## First bootable target

- [x86_64 QEMU bring-up image](docs/BOOTABLE_IMAGE.md) — Buildroot-based experimental Linux image with MOMO startup and diagnostics. It is not a phone ROM; QEMU boot evidence is required before calling the target bootable.

## Technical specifications

- [Vision](docs/VISION.md)
- [Technical architecture](docs/ARCHITECTURE.md)\n- [Universal platform strategy](docs/UNIVERSAL_PLATFORM_STRATEGY.md)\n- [Device compatibility and porting](docs/DEVICE_COMPATIBILITY.md)\n- [Platform adapter contracts](docs/PLATFORM_ADAPTERS.md)
- [AI runtime](docs/AI_RUNTIME.md)
- [Provider routing](intelligence/providers/README.md)
- [Orchestrator implementation](intelligence/runtime/ORCHESTRATOR.md)
- [Agent methodology](docs/AGENT_METHODOLOGY.md)
- [Tool and permission model](docs/TOOL_AND_PERMISSION_MODEL.md)
- [Desktop experience](docs/DESKTOP_EXPERIENCE.md)
- [Cloud build pipeline](docs/CLOUD_BUILD.md)
- [Test strategy](docs/TEST_STRATEGY.md)
- [Device research: SM-A175F](docs/DEVICE_RESEARCH.md) (one candidate, not the product target)\n- [Device profile schema](manifests/device-profile.schema.json)\n- [Device profile template](manifests/device-profiles/template.json)
- [Roadmap](docs/ROADMAP.md)

## Device feasibility gate

Device ports are selected by evidence, maintainability and recovery safety—not by the maintainer's personal handset. Each exact model/SKU requires a profile, verified boot and restore path, kernel/vendor provenance, and hardware test matrix. A kernel or recovery repository is not proof of ROM support.

## Security principles

- AI agents use explicit, least-privilege tools.
- Sensitive or destructive operations require human approval.
- Privileged actions must be auditable.
- Never commit API keys, signing keys, passwords, or personal tokens.
- Model output is not evidence that an operation succeeded.

## Licensing

MOMO-owned code will receive an explicit license before redistribution. Third-party components retain their own licenses and notices. See [Licensing Policy](docs/LICENSING.md).
