# Upstream Integration Policy

## Principle
MOMO OS is an integration and product repository, not a mirror of the entire Android source tree.

## Choose the integration method
1. **Manifest reference:** default for large upstream projects and components that can be consumed without MOMO-specific source changes.
2. **Fork:** use when MOMO needs ongoing changes to a component. Keep the fork synchronized and submit suitable fixes upstream.
3. **Selective vendoring:** only for small, self-contained files or libraries when the license permits redistribution and provenance is preserved.
4. **Adapter/overlay:** preferred when MOMO can extend behavior without maintaining a long-lived fork.

## Required dependency record
Every imported component must record:
- Project and purpose.
- Canonical upstream URL.
- Exact commit SHA or immutable release tag.
- License identifier and required notices.
- Whether source is forked, referenced, or vendored.
- MOMO patch set and rationale.
- Known vulnerabilities and update owner.
- Build/test coverage.

## Rules
- Never use a floating branch as a reproducible release dependency.
- Never remove copyright or license notices.
- Do not assume GitHub Public means permissive licensing.
- Do not copy proprietary vendor blobs without verifying redistribution rights.
- Keep a clean upstream baseline and a reviewable MOMO patch series.
- Document merge/rebase procedure and conflict resolution.
- Prefer upstreaming generic fixes.

## Source intake checklist
- [ ] Inspect repository health and release history.
- [ ] Verify license at the exact revision.
- [ ] Inspect build system, submodules, and dependencies.
- [ ] Review security advisories and known issues.
- [ ] Confirm target architecture and device applicability.
- [ ] Pin exact revision.
- [ ] Record notices and attribution.
- [ ] Add validation and update procedure.
