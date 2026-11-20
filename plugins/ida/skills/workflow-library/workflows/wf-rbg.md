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

1. **Assemble active rules & verify Turn-1 inputs** -- load governing axioms, project rules, user rules, and applicable enforcement policy before judging; never rule from memory. If the target artifact, diff, or originating ask is missing on Turn 1, return `REVISE` listing missing inputs without recording a verdict.
2. **Stage 0: Proportion, non-mechanical baseline & authority** -- from the verbatim ask or standing mandate alone, state the smallest proportionate non-mechanical mechanism before reading the diff; if an agent workflow, instruction update, or existing tool meets the request and the artifact builds a new script, CLI, or harness, halt immediately with `FAIL`. Audit unrequested deletions equally alongside additions against verbatim ask authority (`do-one-thing`), halting with `FAIL` on _ultra vires_ or materially disproportionate work. Verify loaded instructions on the same surface were tried and proved insufficient before escalating mechanisms; reject multi-file prose bloat, single-incident prohibitive rules, and single-use migration/structural scripts. In **PR description-only mode** on a pre-approval consolidated feature-branch PR (whose constituent branches already passed three-lens diff review) or open-PR intake screening, evaluate only the PR title, description (summary, approach, trade-offs, constituent review receipts, test receipts), donor PR closure status, and external-audience `data-boundaries` without re-reading the combined code diff.
3. **Evaluate compliance** -- inspect full PR metadata, the complete diff (including deletions), and static text of modified or explicitly cited test files (rejecting tautological, mirror, or mock-coupled assertions without repo-wide searches or test execution). Test against governing axioms, project/user rules, and least-invasive enforcement:
   - Hold cited waivers strictly to literal quoted bounds (`closure`); reject turn errors suppressed behind stderr or telemetry (`fail-fast`), circular test/spec relaxations, and redundant axiom restatements or deferred DRY/SSoT defects (`single-source-of-truth`).
   - When diffs touch agent definitions, skills, workflows, or specifications, verify compliance with instruction craft standards (contract separation, progressive disclosure, model/harness agnosticism, zero historical provenance), human-principal user stories (never casting agents as users), and generic single-sourced task composition / enforcement tables (no hardcoded workflow branching or workflow rows).
   - Evaluate full published surfaces (diffs, titles, bodies, commits, trailers) under `data-boundaries` for destination visibility, and hard-reject (`FAIL`) unauthenticated public-endpoint exposure or route/auth changes risking unapproved public exposure of private endpoints.
4. **Apply fix discipline** -- apply uncontroversial deterministic fixes (`fix(review): <description>`) ONLY when serialized or explicitly authorized on a writable branch, pushed and verified against committed `HEAD` state before `PASS`; during parallel or read-only review passes, report suggested fixes under `### Suggested Fixes` for single-writer commit and `HEAD` verification before `PASS` (never `REVISE` solely for self-fixed items). Non-deterministic or contested defects go under `### Required Changes` (`REVISE` or `FAIL`). A _Required Change_ names a rule breach whose prevention cost is less than its risk; anything else is a _Suggested Improvement_ (requiring less, not more, when work exceeds the ask).
5. **Respect boundaries & issue verdict** -- judge strictly on static compliance, authority, and egress within the artifact text/diff and rule sources (leaving strategic congruence and runtime verification to their respective review roles), returning one verdict (`PASS`, `REVISE`, or `FAIL`) in readable Markdown (`## Compliance Review: **[PASS | REVISE | FAIL]**` with `### Reviewer Self-Fixes Applied`, `### Proportion & Mechanisms`, `### Required Changes`, and `### Suggested Improvements`).

## Output contract

- Structured Markdown review containing one verdict (`PASS`, `REVISE`, or `FAIL`), proportion assessment, any committed and pushed self-fixes verified at `HEAD`, itemized `### Required Changes` with pinpoint citations, and `### Suggested Improvements`.

## When to include

Any workflow producing a specification, design proposal, instruction, code change, or decision for compliance review before delivery or escalated sign-off.
