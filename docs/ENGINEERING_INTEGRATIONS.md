# MOMO engineering integrations: provider routing, OpenHands, and extensions

This document records the integration boundary for the optional engineering toolchain. These integrations are not part of the Android boot image and do not bypass MOMO's task planner, ExecutionGate, approval store, or typed executor.

## 1. Model access and FreeLLMAPI

MOMO's current model router is a policy selector. It checks capability, data classification, locality, provider enablement, and a configured cost ceiling; it does not send inference requests by itself.

The autonomous engineering worker now has two explicit provider modes:

- **Authenticated OpenAI-compatible gateway:** set MOMO_AGENT_API_KEY, MOMO_AGENT_MODEL, and optionally MOMO_AGENT_API_URL. This is the supported path for sustained work. A self-hosted FreeLLMAPI instance can be used by setting the URL to its /v1/chat/completions endpoint and the key to the gateway key.
- **Anonymous OVH bootstrap:** when no API key is set, the worker uses only https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions and defaults to gpt-oss-120b. The no-key path is deliberately hard-coded to this host; it does not allow arbitrary unauthenticated endpoints. An optional MOMO_AGENT_MODEL can select another OVH model only when that model is supported by the endpoint.

OVH documents a limit of **2 anonymous requests per minute per IP address and model**. This makes the path useful for a smoke test or occasional single-cycle experiment, not a reliable autonomous development service. A provider may also return rate limits, model-retirement errors, or unsupported JSON behavior; the worker fails closed on those errors or on malformed output. The anonymous path sends a small model prompt containing the public repository snapshot and plan context. Do not use it with private source, credentials, secrets, or non-public data.

FreeLLMAPI is a **gateway, not an inference engine**. It can consolidate multiple providers and fallback routes, but the operator normally adds provider credentials inside its dashboard and uses a separate FreeLLMAPI gateway key from MOMO. Its documented keyless routes do not make the platform a dependable no-credential service. In particular:

- OVH keyless access is sharply rate-limited.
- Kilo anonymous free models are limited by IP and the provider documentation warns that prompts and outputs may be logged or used to improve services. MOMO must not send private code or secrets there.
- AI Horde is queued/volunteer capacity and is not a dependable low-latency software-engineering backend.

For a private FreeLLMAPI deployment, keep it on a private network or localhost behind a trusted tunnel. The upstream project explicitly warns against exposing its single-user proxy directly to the public internet. Set and back up its separate ENCRYPTION_KEY; protect the dashboard owner account and the gateway token. Do not place upstream provider keys in source files or commit them.

## 2. OpenHands as an optional cloud engineering worker

The OpenHands Software Agent SDK is the appropriate integration surface, not the full desktop application. Its current SDK and tools packages require Python 3.12 or newer and are MIT-licensed. Install the optional packages only in a dedicated engineering runner:

    python -m pip install -r requirements-engineering.txt

The preferred topology is:

1. MOMO selects a bounded engineering task and issues a scoped workspace/task reference.
2. A separate automation service provisions a disposable OpenHands Agent Server workspace (Docker or Kubernetes sandbox), with an unprivileged user, resource limits, a repository-only working directory, no host mounts, and network egress restricted to the selected model endpoint and required package/Git hosts.
3. OpenHands works only inside that disposable workspace and returns a diff, test output, and execution metadata.
4. MOMO validates the diff with its path policy and repository test pipeline, records the result, and opens a reviewable pull request.
5. Human review is still required before merge. The agent has no GitHub merge permission.

Do **not** install OpenHands in the MOMO Android root filesystem or give its Terminal tool access to the live device. The SDK's Terminal tool executes shell commands. The security boundary therefore comes from the disposable remote workspace, not from the model prompt. Do not connect the SDK to a non-isolated host or a developer's home directory.

This repository records the optional dependency versions; it does not claim that a remote Agent Server has already been deployed. The remote-server URL, server session token, model provider configuration, and sandbox infrastructure are still deployment inputs.

## 3. Omni-inspired extension contract

Omni is a GPL-3.0 Rust/Tauri application. MOMO does not copy or vendor its implementation. The useful design ideas are permission declarations, auditable tool activity, typed extension manifests, and WebAssembly isolation.

MOMO now has a first declarative contract at security/extension-manifest.schema.json. It requires:
- a stable extension ID and semantic version;
- a runtime and SHA-256 artifact digest;
- declared capabilities and scoped permissions;
- explicit risk and approval mode (R3/R4 permissions require per-call approval);
- data classification;
- an explicit network policy and workspace mode.

The schema is only a validation contract. It does not execute code, verify an artifact signature, grant a capability, or replace ExecutionGate. Before third-party extensions can run, a future implementation must add trusted publisher signatures, artifact provenance, WASI capability mapping, a real sandbox, resource budgets, and an audit trail. High-risk and data-classification policy remains MOMO-owned.

## 4. What is and is not complete

**Implemented in this increment:** a tightly allowlisted anonymous OVH fallback in the engineering worker; tests for provider selection policy; optional OpenHands SDK/tool dependencies; a declarative extension manifest schema and its validation tests; this integration/security boundary document.

**Not yet demonstrated:** a successful live anonymous OVH completion from GitHub Actions; a running OpenHands Agent Server; a production FreeLLMAPI deployment; a WASM runtime or signed third-party extension installer. These must not be represented as completed features until their own end-to-end tests and security checks pass.
