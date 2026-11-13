# Task Coordinator

Status: first policy integration layer; not a tool executor.

## Responsibilities
- Validate a plan against the registered agent roles, domains, capabilities, risk ceilings, dependency graph and delegation budget.
- Persist task creation and lifecycle events through the SQLite task journal.
- Return deterministic dependency-ready steps.
- Ask the persistent permission broker to authorize each step against an exact subject/action/task-resource/risk grant.
- Require a matching explicit per-action approval for R3/R4 steps.

## Security boundary
The coordinator never dispatches a tool, calls a model, creates a grant, approves an action, or treats a model-produced plan as authority. A successful authorization decision means only that a matching grant was consumed; the platform adapter must still enforce native OS permissions and sandboxing.

## Current limitations
Plans are caller-supplied and revalidated but are not yet persisted. There is no execution adapter, crash-recovery scheduler, cancellation propagation, or end-to-end tool execution. These are separate milestones and must not be implied by this module.
