# MOMO CELL — Autonomous Engineering Worker

## Purpose

This is the first executable engineering-agent increment for MOMO-OS. It gives MOMO CELL a bounded model-backed patch cycle: inspect an explicit repository snapshot and project plan, select one engineering task, propose a minimal unified diff, validate every touched path, apply the patch, and leave independent CI to test it.

This is not model training or AGI. The worker is a configured model using a versioned project contract, repository context, deterministic policy checks, and independent test evidence.

## Required GitHub configuration

Create a repository Actions secret named `MOMO_AGENT_API_KEY` containing an API key for an OpenAI-compatible provider (OpenRouter is the default endpoint). Create a repository Actions variable named `MOMO_AGENT_MODEL` containing the exact model identifier. Optional variable `MOMO_AGENT_API_URL` may override the default OpenRouter-compatible endpoint. Never place credentials in source files, workflow inputs, logs, or prompts.

## Authority granted

- Read a bounded, tracked repository snapshot and the engineering plan.
- Propose one small source/test/documentation patch per invocation.
- Modify only allowlisted source, tests, ordinary documentation, and selected adapter directories.
- Use a fixed patch-application operation; no model-selected shell command or arbitrary tool call exists.
- Rely on fixed CI commands for tests and verification.
- Publish a branch and pull request through the workflow's narrowly scoped GitHub token.

## Explicitly denied

The worker cannot edit its own implementation, its policy, GitHub workflows, security policy, credentials, kernel/init configuration, permissions, or protected engineering contracts. It cannot approve its own changes, merge a pull request, change repository settings, access deployment credentials, or operate physical devices. R3/R4 operations remain outside its authority.

## Stop conditions

Missing provider configuration, malformed model output, invalid patch paths, oversized patches, failed patch application, failing tests, timeouts, and policy violations stop the run. The worker does not retry a failed patch indefinitely. A human reviews each pull request. The supervising engineer must inspect repeated failures, correct the task/policy/context, and only then resume.

## Operating cycle

1. Read the current plan and bounded source snapshot.
2. Select one highest-priority task with a verifiable outcome.
3. Produce a minimal patch in a strict JSON response.
4. Validate path policy and patch integrity locally.
5. Run repository tests and deterministic checks in GitHub Actions.
6. Push only a successful candidate and open/update a pull request.
7. Independent CI and human review decide whether the candidate is promoted.
8. Re-evaluate the remaining roadmap after integration.

## Current maturity

This is a controlled first worker, not a complete autonomous project owner. It does not yet maintain a durable multi-cycle backlog, independently authenticate a human approver, repair failed CI, merge its own PRs, or prove x86_64/AArch64/Android device acceptance. Those are subsequent milestones and must be implemented as separately tested capabilities.
