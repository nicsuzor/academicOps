<!-- Reviewer-decision structure -- fill each section; keep it scannable as a
     decision aid. A maintainer should be able to evaluate and decide to
     approve in ~60s. State the outcome first. Link to specs or diff rather
     than restating them in prose. Drop or omit only sections explicitly
     marked optional when not applicable.

     Note: polecat workers use this structure when opening or updating a PR
     (see .agents/templates/wf-finish.md). Applies to automated agent PRs and
     human-authored PRs alike. -->

## Summary

One or two plain sentences: what this changes and why it exists. Lead with the concrete outcome or change.

## Posture

- [ ] Standard implementation / proper fix
- [ ] Pragmatic workaround (specify reason and temporary conditions)
- [ ] Stopgap (link tracked follow-up task or issue)

## Alignment

What task, ruling, spec, or user directive this serves, and what is unblocked.

## Approach

High-level architecture and decisions taken. Explain design choices clearly so the PR is easy to evaluate without reading every file. Fine-grained inspection belongs in the diff. For fixes: summarize root cause and evidence.

## Risk & blast radius

Scope of impact (single component vs shared infrastructure/CI/all PRs), reversibility, and any security or environment boundaries touched.

## Sequencing (Optional)

State if this PR depends on, blocks, or requires a specific merge sequence relative to other PRs. Omit if standalone.

## Verification

Concrete observational evidence (tests executed, commands run, outputs observed) and explicitly what is NOT verified (e.g. CI-only paths, live telemetry).
