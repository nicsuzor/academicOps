---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: Universal compliance review -- evaluate candidate artifact, change, or decision against universal axioms, user and project rules, delegated authority scope (ultra vires), data boundaries, and the least-invasive enforcement hierarchy, returning PASS, REVISE, or FAIL.
id: wf-rbg
tags:
  - wf-template
  - review
  - rules
  - compliance
title: Rule-Compliance Review
type: template
---

## What this step does

Universal compliance review: a compliance reviewer evaluates an artifact, specification, design, code change, or decision against universal axioms, project-local and user-scoped rules, scope of delegated authority (_ultra vires_), data boundaries, and the least-invasive intervention hierarchy, exercising direct qualitative judgment over intent and gravity rather than mechanical pattern-matching.

## Input contract

Draws its brief from the shared review briefing plus active rule sources assembled in priority order:

- **Universal axioms**: inviolable framework baseline.
- **Project-local rules**: project rule definitions in the active repository.
- **User-scoped rules**: active user rule records (when present).
- **Enforcement architecture**: governing enforcement policy when behavior-shaping mechanisms are modified.

## Procedure

1. **Assemble active rules** -- load governing axioms, project rules, user rules, and applicable enforcement policy before judging; never rule from memory.
2. **Stage 0: Proportion, non-mechanical baseline & authority** -- from the quoted ask alone, determine whether an agent workflow, instruction update, or existing tool meets the request without new executable code. If yes and the artifact builds a new script, CLI, or harness, halt immediately with `FAIL`. State the smallest proportionate mechanism before reading the diff, and halt with `FAIL` if the artifact acts _ultra vires_ or is materially disproportionate. When invoked in **PR description-only mode** on a pre-approval consolidated feature-branch PR (whose constituent branches already passed three-lens diff review) or during open-PR intake screening, evaluate only the PR title, description (summary, approach, trade-offs, constituent review receipts, test receipts), donor PR closure status, and external-audience `data-boundaries` without re-reading the combined code diff.
3. **Evaluate compliance** -- test the artifact against governing axioms (categorical imperative, closure, data boundaries, excellence, fail-fast, full observability, honest epistemics, honour glossaries, human readability first, no over-engineering, non-delegable qualitative judgment, proportionate, single source of truth), project/user rules, and the enforcement hierarchy (defaulting to instructions before mechanical controls):
   - Verify specifications evaluate from the human user's perspective, never casting an agent or worker as the user in user stories.
   - Verify task-composition skills and cross-project enforcement tables remain generic, single-sourced, and free of hardcoded workflow branching or repo-local rules.
   - Verify published surfaces comply with data boundaries for the target destination's visibility.
4. **Apply fix discipline** -- apply uncontroversial deterministic fixes (`fix(review): <description>`) ONLY when serialized or explicitly authorized on a writable branch; during parallel or read-only review passes, report suggested fixes for the fix pass. Non-deterministic or contested defects go under `### Required Changes` (`REVISE` or `FAIL`). A _Required Change_ names a rule breach whose prevention cost is less than its risk; anything else is a _Suggested Improvement_ (requiring less, not more, when work exceeds the ask).
5. **Respect boundaries & issue verdict** -- judge strictly on compliance within the artifact text/diff and rule sources (leaving strategic congruence and runtime verification to their respective review roles), returning one verdict (`PASS`, `REVISE`, or `FAIL`) in readable Markdown (`## Compliance Review: **[PASS | REVISE | FAIL]**` with `### Reviewer Self-Fixes Applied`, `### Required Changes`, and `### Suggested Improvements`).

## Output contract

- Structured Markdown review containing one verdict (`PASS`, `REVISE`, or `FAIL`), itemized `### Required Changes` with pinpoint citations, `### Suggested Improvements`, and `### Reviewer Self-Fixes Applied` (if any).

## When to include

Any workflow producing a specification, design proposal, instruction, code change, or decision for compliance review before delivery or escalated sign-off.
