# Claude Handoff — MOMO OS

This directory is the controlled handoff area for collaboration between ChatGPT and Claude.

## Direction

- `TO_CLAUDE/`: ChatGPT places the exact files, patches, reports, or instructions that Claude should inspect.
- `FROM_CLAUDE/`: Claude places the complete files, patches, test output, and review reports that ChatGPT should inspect.

## Rules

1. Every handoff must have a short, descriptive name and a date in its filename, for example:
   - `2026-11-14_execution-gate-review.md`
   - `2026-11-14_execution-gate.patch`
2. Do not overwrite an earlier handoff. Add a new dated file so the history remains reviewable.
3. Include the source branch and commit SHA the handoff is based on.
4. For code changes, include complete changed files or a unified diff, not partial snippets.
5. Include test commands and their actual outputs. Clearly distinguish tests not run from tests that passed.
6. Never place API keys, access tokens, passwords, signing keys, private user data, or other secrets here.
7. Files placed here are not automatically approved for merging. ChatGPT must review them against the SRS, Master Execution Plan, Roadmap, security requirements, and tests.
8. Do not commit generated binaries or large build artifacts here. Link to a GitHub Actions artifact or release when appropriate.

## Current handoff status

This directory is an exchange area only. It does not change the product architecture, implementation status, or release claims.
