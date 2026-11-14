# MOMO CELL — Autonomous Engineering Worker

## Purpose

This is the first executable engineering-agent increment for MOMO-OS. It gives MOMO CELL a bounded model-backed patch cycle: inspect an explicit repository snapshot and project plan, select one engineering task, propose a minimal unified diff, validate every touched path, apply the patch, and leave independent CI to test it.

This is not model training or AGI. The worker is a configured model using a versioned project contract, repository context, deterministic policy checks, and independent test evidence.

## Required GitHub configuration

Create a repository Actions secret named `MOMO_AGENT_API_KEY` containing an API key for an OpenAI-compatible provider (OpenRouter is the default endpoint). Create a repository Actions variable named `MOMO_AGENT_MODEL` containing the exact model identifier. Optional variable `MOMO_AGENT_API_URL` may override the default OpenRouter-compatible endpoint. Never place credentials in source files, workflow inputs, logs, or prompts.

## Local model experiment (no API key)

The worker also supports an explicitly selected local OpenAI-compatible inference server. Set:

- `MOMO_AGENT_PROVIDER=local`
- `MOMO_AGENT_API_URL=http://127.0.0.1:8080/v1/chat/completions`
- `MOMO_AGENT_MODEL=momo-local-coder`

Local mode accepts only HTTP loopback addresses (`127.0.0.1`, `localhost`, or `::1`), rejects API keys, and never silently redirects local requests to a remote provider. The experimental GitHub Actions workflow builds llama.cpp and downloads the Qwen2.5-Coder 1.5B Q4_K_M GGUF model (Apache-2.0 distribution) into the disposable runner, then runs one bounded candidate cycle with read-only GitHub permissions.

This is local inference, not model training. MOMO specializes the model at runtime using its project brief, bounded source snapshot, strict output contract, and deterministic tests. Fine-tuning model weights would require a separately prepared, licensed training dataset and suitable accelerator hardware; no weight training is claimed or performed here.

The 1.5B model is deliberately an experiment, not an assumed replacement for a stronger hosted coding model. Its candidate must pass the same patch policy and full independent test suite. A failed, malformed, empty, or low-quality proposal is a failed experiment, not a successful development cycle.

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
