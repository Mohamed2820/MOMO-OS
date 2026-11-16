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

## MOMO CELL supervised engineering worker

MOMO CELL is a bounded, supervised repository engineering worker. A human assigns one open GitHub Issue labeled `momo-cell:ready`, with an explicit task contract and exact files in scope. A human-triggered GitHub Actions run sends that assignment and the permitted repository context to the configured model, which proposes a patch for that task only. The worker validates the patch against the assigned file scope and repository policy, runs the fixed MOMO CELL tests and patch checks, and opens a candidate pull request against `main` when validation succeeds. A human reviews and merges the candidate pull request; MOMO CELL does not merge its own changes. This is not unrestricted repository autonomy, it is not automatically scheduled, and it does not currently provide multi-model fallback.
