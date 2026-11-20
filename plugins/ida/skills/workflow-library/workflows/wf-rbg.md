---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: Universal judicial compliance review -- adjudicate candidate artifact, change, or decision independently against universal axioms, user and project rules, delegated jurisdiction (ultra vires), abdication, non-delegable discretion, data boundaries, and the least-invasive enforcement hierarchy, returning PASS, REVISE, or FAIL.
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

Universal judicial compliance review: an independent adjudicator tests an artifact, design, code change, or decision against constitutional axioms, project and user rules, delegated jurisdiction (_ultra vires_), _abdication_, non-delegable discretion, data boundaries, and the enforcement hierarchy without reading prior reviews or deferring to peers.

## Input contract

Draws its brief from the shared review briefing plus active law assembled in priority order:

- **Universal axioms**: inviolable constitutional baseline.
- **Project-local rules**: project rule definitions in the active repository.
- **User-scoped rules**: active user rule records (when present).
- **Enforcement architecture**: governing enforcement policy when behavior-shaping mechanisms are modified.

## Procedure

1. **Assemble active law & verify Turn-1 inputs**:
   - Load governing axioms, project rules, user rules, active glossaries, and applicable enforcement policy before judging; never rule from memory or waive axioms.
   - If the target artifact, diff, or originating mandate is missing on Turn 1, ask the supervisor to supply it without declining (no report verdict on unarmed briefs; disarm armed direction briefs via `--no-claim` per `premise-check`).
2. **Stage 0: Proportion, non-mechanical baseline & _ultra vires_ screen** (judging independently before reading prior reviews):
   - From the verbatim ask or standing mandate alone -- before reading the diff -- state the smallest proportionate non-mechanical remedy across its class; issue `FAIL` at once if an agent workflow, instruction update, or existing tool suffices while the artifact builds scripts, CLIs, or test harnesses.
   - Audit unrequested deletions equally alongside additions against the verbatim mandate (`do-one-thing`), halting with `FAIL` on _ultra vires_ overreach or materially disproportionate work.
   - Verify loaded instructions on the same surface were tried and proved insufficient before escalating mechanisms; reject multi-file prose bloat, single-incident prohibitive rules, and single-use structural/migration scripts.
   - _PR description-only mode_: On a pre-approval consolidated feature-branch PR (whose constituent branches already passed three-lens diff review) or open-PR intake screening, evaluate only the PR title, description (summary, approach, trade-offs, constituent review receipts, test receipts), donor PR closure status, and external-audience `data-boundaries` without re-reading the combined diff.
3. **Evaluate compliance & runtime consequences**:
   - Inspect full PR metadata, the complete diff (including deletions), and static text of modified or cited test files (rejecting tautological, mirror, or mock-coupled assertions without repo sweeps or running tests).
   - Name each added mechanism by the decision it takes once running and whether it requires qualitative judgment; enforce literal waiver bounds (`closure`), fail-closed errors (`fail-fast`), and single source of truth without deferred DRY/compliance debt.
   - When diffs touch agent definitions, skills, workflows, or specs, check instruction craft standards (including preservation of authorial public-law voice), human-principal user stories, and generic workflow composition / enforcement tables.
   - Audit full published surfaces (diffs, titles, bodies, commits, trailers) under `data-boundaries`, and issue `FAIL` for unauthenticated public-endpoint exposure or auth changes risking private exposure.
4. **Apply fix discipline & duty to give reasons**:
   - _Serialized writable branch_: Apply uncontroversial deterministic fixes (`fix(review): <description>`) only when serialized or explicitly authorized, committed, pushed, and verified against `HEAD` before issuing `PASS` (itemizing them as Argdown observations internally, or under `### Reviewer Self-Fixes Applied` in published/user-facing outputs).
   - _Parallel or read-only passes_: Report suggested fixes as Argdown findings internally (or under `### Suggested Fixes` in published/user-facing outputs) for single-writer commit and `HEAD` verification before `PASS` (never issuing `REVISE` solely for cleanly self-fixed items).
   - _Contested defects_: Report non-deterministic defects as Argdown findings internally (or under `### Required Changes` in published/user-facing outputs) with `REVISE` or `FAIL`, stating the broken rule and a remedy costing less than the failure prevented; anything else is a _Suggested Improvement_ (requiring less, not more, when work exceeds the ask).
5. **Respect jurisdiction & issue verdict** -- confine adjudication to static compliance, delegated jurisdiction, and egress (leaving strategic coherence and runtime verification to their branches), returning one verdict (`PASS`, `REVISE`, or `FAIL`).

## Output contract

- Internal agent-to-agent compliance handbacks report **only** in clean Argdown prose per `premise-check` (leading with original ask and verdict, quoting deciding rule and artifact evidence inline). Use structured Markdown (`## RBG Review: **[PASS | REVISE | FAIL]**` with `### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Proportion & Mechanisms`, `### Required Changes`, and `### Suggested Improvements`) strictly for published PR/issue comments or user-facing review artifacts. Every compliance review covers one verdict (`PASS`, `REVISE`, or `FAIL`), proportion assessment, any committed and pushed self-fixes verified at `HEAD`, required changes with pinpoint citations, and suggested improvements.

## When to include

Any workflow producing a specification, design proposal, instruction, code change, or decision for compliance review before delivery or escalated sign-off.
