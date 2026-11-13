# MOMO Intelligence

This directory contains MOMO-owned AI orchestration components. The runtime is provider-agnostic and capability-mediated.

Planned modules:
- `orchestrator/` — canonical task state and delegation.
- `agents/` — bounded specialist roles.
- `providers/` — local and remote model adapters.
- `tools/` — typed tool declarations and adapters.
- `memory/` — scoped, user-controlled memory.
- `verification/` — independent outcome checks.
- `policy/` — capability and approval decisions.
- `tests/` — deterministic and adversarial tests.

Do not add API keys or secrets. Do not implement arbitrary shell execution as a general-purpose agent tool. Begin with mock providers and mock tools; connect real device capabilities only after the permission broker and audit model are tested.
