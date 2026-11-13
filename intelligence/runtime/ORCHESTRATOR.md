# Multi-Agent Orchestrator Core

The first deterministic orchestration layer is implemented in `orchestrator.py`.

## Implemented
- Agent registry with explicit domains, capabilities, and maximum risk.
- Plan and step contracts.
- Validation of unknown roles, duplicate IDs, unknown dependencies, cycles, domain mismatch, missing capabilities, risk ceilings, and step budgets.
- Deterministic dependency-aware ready-step scheduling.

## Deliberately not implemented yet
- Model-based planning.
- Real agent execution or parallel workers.
- Persistent task database.
- Android tool adapters.
- Memory retrieval.
- Retry, timeout, cancellation, and cost accounting at execution time.

The validator is a pre-execution guardrail, not a complete security boundary. The capability broker and Android system services must enforce authority at the point of action.
