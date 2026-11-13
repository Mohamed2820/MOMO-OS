# Source manifests

This directory will contain Repo manifests and machine-readable upstream inventory.

Do not add speculative device projects or floating source revisions. A manifest is considered build-ready only when every project has a verified remote, branch/tag or immutable commit, license record, and compatibility rationale.

The first Android platform baseline is intentionally not pinned yet. Selection is blocked on the device feasibility gate and upstream comparison.

Suggested future files:
- `default.xml` — pinned Android/ROM source manifest after base selection.
- `upstreams.yml` — provenance, license, revision, and update metadata.
- `patches/README.md` — MOMO-owned patch series and synchronization notes.
