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

MOMO CELL is a bounded, supervised repository engineering worker. A human assigns one open GitHub Issue labeled `momo-cell:ready`, with an explicit task contract and exact files in scope. A human-triggered GitHub Actions run sends that assignment and the permitted repository context to the configured model, which proposes a patch for that task only. The worker validates the patch against the assigned file scope and repository policy, runs the fixed MOMO CELL tests and patch checks, and opens a candidate pull request against `main` when validation succeeds. A human reviews and merges the candidate pull request; MOMO CELL does not merge its own changes. This remains supervised repository engineering, not unrestricted autonomy. The worker uses a configured primary model with OpenRouter fallback routing; fallback availability is provider- and quota-dependent.


## MOMO CELL engineering toolchain

The worker now uses a bounded OpenRouter tool-calling loop. The model can request only these host-executed capabilities:

- `list_repo_files` — list tracked files allowed by MOMO's immutable read policy.
- `search_repo` — literal search across policy-readable source, tests, and ordinary documentation.
- `read_repo_file` — read one tracked, regular text file within a fixed size limit.
- `run_fixed_tests` — run the repository-owned MOMO test suite and syntax checks; the model cannot supply a command.
- `validate_patch` — validate a unified diff against the exact Issue file scope and run `git apply --check` without changing files.
- `get_recent_ci_runs` / `get_ci_run_jobs` — inspect recent GitHub Actions runs and step outcomes through read-only, same-repository API calls.

The model cannot call arbitrary shell, access secrets, browse the network, write files directly, or expand its assigned file scope. The host applies only a validated patch. A separate reviewer model must approve the patch before application; if the reviewer resolves to the same model as the author, the cycle fails closed. Fixed tests run after application, with at most one feedback-based repair attempt.

After a successful verification, MOMO CELL appends a structured record to `.momo-cell/memory/engineering.jsonl`. The latest records are supplied as untrusted project memory on later tasks. The fixed evaluation contract in `intelligence/autonomy/evaluation_cases.json` tracks tool use, scope enforcement, prompt-injection resistance, independent review, test feedback, and bounded repair. Its score measures observable engineering-process evidence; it is not a measure of model intelligence and does not train model weights.

Candidate changes still go to a human-review pull request. MOMO CELL does not merge its own pull requests.
