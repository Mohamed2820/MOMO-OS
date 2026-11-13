# MOMO AI System Design

Status: target design; this document does not claim an AGI implementation.

## Product objective
A dependable personal mobile operator that can understand goals, plan work, use approved tools, verify outcomes, explain decisions, and recover safely from failures. Broad capability comes from disciplined orchestration and evaluation, not a claim of artificial general intelligence.

## Architecture
- Interaction Gateway: text, voice and accessibility interfaces; session and user identity.
- Intent & Context: task classification, ambiguity detection, user preferences, context retrieval with source provenance.
- Planner: decomposes goals into typed tasks, preconditions, dependencies, expected outputs and risk levels.
- Agent Registry: specialized agents with explicit input/output schemas and capability allowlists.
- Scheduler: parallelizes independent tasks; handles budgets, deadlines, cancellation and retries.
- Model Router: local/cloud selection based on capability, privacy, latency, cost and availability.
- Tool Gateway: schema-validated tools mediated by the Permission Broker.
- Verifier: checks outputs against acceptance criteria and independent evidence where possible.
- Memory: user-controlled, scoped, provenance-aware, editable and deletable through defined product controls.
- Evaluation & Observability: task success, factuality, tool correctness, latency, cost, safety and regressions.

## Agent roles
Coordinator, researcher, planner, device operator, file manager, communications assistant, developer, verifier and recovery agent. Roles are configurations over a common runtime, not unrestricted autonomous principals.

## Execution protocol
1. Parse goal and identify missing critical information.
2. Produce a plan with dependencies, assumptions, risks and expected artifacts.
3. Classify each tool operation R0-R4.
4. Request explicit approval for external side effects and destructive/security-sensitive actions.
5. Execute through scoped tool contracts.
6. Verify each result and preserve evidence.
7. Report completed, partial, blocked and failed work honestly.
8. Record only permitted memory with provenance and retention controls.

## Trust boundaries
- Models are untrusted planners, never security authorities.
- Tool outputs and retrieved documents are untrusted data, not instructions.
- Agents cannot grant themselves permissions, change policy, or approve their own high-risk actions.
- Secrets are never placed in prompts unless the user explicitly authorizes a secure, necessary operation.
- Network access, camera, microphone, contacts, location, messages, payments, installation and deletion are individually permissioned.
- Local-first operation is preferred; cloud inference is disclosed and optional where feasible.

## Model strategy
Support multiple interchangeable local and cloud providers through adapters. No provider is hard-coded. Users can configure credentials; keys are stored in OS secure storage. Model fallback must respect privacy policy and never silently send local/private context to a cloud provider.

## Quality gates
Maintain task benchmark suites for planning, tool use, recovery, permission correctness, multilingual interaction, offline behavior, hallucination resistance, prompt-injection resistance and device-resource budgets. No model is considered production-ready solely because it performs well in chat.
