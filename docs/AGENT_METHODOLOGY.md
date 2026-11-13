# MOMO Multi-Agent Methodology

## Objective
Create a coordinated team of specialist agents that can handle broad tasks through disciplined decomposition, tools, memory, and verification. This is an engineering goal, not a claim of artificial general intelligence.

## Operating loop
1. **Understand:** extract the user's goal, constraints, context, and success criteria.
2. **Classify:** determine domain, privacy, risk, and whether action is requested.
3. **Plan:** produce a dependency-aware plan with checkpoints and fallback paths.
4. **Delegate:** assign bounded tasks to agents with clear inputs and expected outputs.
5. **Research:** gather evidence and label source quality, freshness, and uncertainty.
6. **Execute:** route approved tool calls through capability checks and policy.
7. **Verify:** use independent evidence, tests, and state inspection.
8. **Reflect:** identify failures, update task state, and retry only within limits.
9. **Report:** distinguish completed, failed, blocked, and unverified work.
10. **Remember:** retain only useful, authorized, appropriately scoped information.

## Agent contract
Each agent declares:
- Role and allowed task classes.
- Input and output schema.
- Available tools and capability scopes.
- Model requirements and fallback behavior.
- Time, token, and cost budgets.
- Evidence and citation requirements.
- Escalation conditions.

## Coordination
The orchestrator owns the canonical task state. Agents cannot silently change user goals or grant each other privileges. Use structured messages, explicit task IDs, and bounded delegation depth. Detect circular delegation and conflicting recommendations.

## Quality controls
- Separate research from implementation review.
- Require tests for code changes.
- Require security review for privileged changes.
- Compare claims against primary sources where possible.
- Track confidence and unresolved assumptions.
- Never equate fluent output with correctness.

## Memory
Use separate scopes for session state, project knowledge, and user-approved durable preferences. Store provenance and timestamps. Provide inspection, correction, export, and deletion controls. Do not store secrets in agent memory.

## Failure handling
Use timeouts, retries with backoff, idempotency keys for actions, cancellation, and clear partial-completion reports. Stop when a safety boundary or missing authorization blocks progress.
