# MOMO AI Runtime Specification

Status: architecture specification plus early deterministic runtime components; not production-ready.

## Product contract
MOMO is a personal assistant runtime that coordinates specialized agents. It is not described as AGI and must never claim certainty or task completion without evidence.

## Runtime components
- **Conversation gateway:** accepts text, voice transcripts, app/context events, and user-selected files.
- **Intent and policy classifier:** identifies task type, privacy class, risk, and required capabilities.
- **Planner:** produces a structured plan with dependencies, expected outputs, and stop conditions.
- **Orchestrator:** owns task state, budgets, delegation, cancellation, and retries.
- **Agent registry:** maps bounded specialist roles to model profiles and tool scopes.
- **Model router:** chooses local or remote provider based on policy, capability, latency, availability, and cost. An initial provider-profile selector now enforces capability, data-classification, local-only, and cost constraints; it does not yet call model APIs.
- **Tool broker:** validates schema, checks capability grants, requests approval, executes, and records evidence.
- **Memory service:** stores only authorized user/project memory with provenance and retention rules.
- **Verifier:** checks external state, test results, and artifact integrity independently.
- **Audit journal:** records decisions and actions without storing secrets or unnecessary sensitive content.

## Specialist roles
Initial roles: orchestrator, researcher, planner, developer, reviewer, device engineer, security auditor, QA verifier, personal secretary. A role is a prompt and bounded capability profile, not an independent trusted identity.

## Task state machine
`received → classified → planned → awaiting_approval → executing → verifying → completed`
Alternative terminal states: `cancelled`, `blocked`, `failed`, `partially_completed`.

A task may skip approval only when every action is explicitly pre-authorized by a narrow, revocable grant and is low-risk. Destructive, financial, externally visible, account/security, or device-integrity actions always require confirmation.

## Delegation rules
- Orchestrator remains the sole owner of canonical task state.
- Child agents receive only the minimum task context and tools.
- Agents cannot grant capabilities or approve their own actions.
- Delegation depth, parallelism, tokens, time, retries, and cost are bounded.
- Conflicting agent conclusions are surfaced to the verifier; they are not averaged blindly.

## Model routing
Use provider adapters with a common request/response contract. Keep credentials in Android Keystore or an approved external secret store, never in source control. Local models are preferred for eligible private tasks; remote models are selected only when policy allows. Provide user-selected provider configuration and no hard-coded API key.

## Reliability
Every tool call has an idempotency strategy where possible, timeout, cancellation behavior, structured error, and evidence record. A model response is not evidence of a successful side effect.

## Acceptance criteria for first runtime
- Deterministic unit tests for state transitions and policy checks.
- Mock provider and mock tools for integration tests.
- Prompt-injection and confused-deputy tests.
- Cancellation and timeout tests.
- No tool execution before policy approval.
- Independent verification of all reported side effects.
