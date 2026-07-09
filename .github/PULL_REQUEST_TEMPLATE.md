<!-- Reviewer-decision structure — fill each section; keep it scannable, a
     decision aid, not a form to pad. A maintainer should be able to decide to
     approve in ~60s. Reference (don't restate) pipeline semantics owned by
     specs/workflows/pr-pipeline.md. Drop a line only if it is genuinely N/A.

     Note: polecat workers are instructed to use this same structure when they
     file their own PR from within their session (see the finish instructions
     in polecat/prompt_template.py), so it applies to bot PRs and hand-opened
     ones alike — polecat itself never creates or edits a PR. -->

## Summary

One or two plain sentences: what this changes and why it exists.

## Posture (be honest)

- [ ] Proper fix / best practice
- [ ] Pragmatic workaround — works, not ideal (say why it's OK for now)
- [ ] Stopgap — deliberately temporary (link the follow-up)

## Why now / alignment

What breaks or is blocked without this; the task/ruling/spec it serves. Intended design, or expedient?

## Change

What changed, at file:line. For fixes: root cause + evidence (run IDs, commit SHAs, worked example).

## Risk & blast radius

What could break, who's affected (one project vs shared infra/CI/all PRs), reversibility, any gate/security implication.

## Sequencing

Standalone, or depends-on / blocks other PRs? Merge before/after something? Name the other PRs if order matters.

## Verification

How it was checked (tests, behaviour) and — explicitly — what is NOT verified (e.g. CI-only paths).
