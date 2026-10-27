---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: Universal rule-compliance review gate -- evaluate candidate artifact, change, or decision against axioms and governing rules, returning an APPROVE, SUGGEST, REVISE, or REJECT verdict with required changes.
id: wf-rbg
tags:
  - wf-template
  - review
  - rbg
  - rules
  - compliance
  - gate
title: Rule-Compliance Review
type: template
---

## What this step does

Universal rule-compliance review gate: evaluates an artifact, specification, design proposal, code change, or decision against governing rules with rigorous logical judgment. Exercises direct judgment rather than mechanical pattern-matching.

## Input contract

Draws its brief from the shared review briefing in `wf-review`. Additional role-specific inputs:

- **Rule sources** -- assembled in priority order:
  - Framework axioms: the `rbg:axioms` skill (inviolable baseline).
  - Project-local rules: `$CWD/.agents/rules/`.
  - Account-scoped rules: read from active PKB rules.

## Procedure

1. **Assemble active rules** -- load governing axioms, project rules, and companion specs (e.g. `specs/enforcement/enforcement.md`) before judging; never rule from memory.
2. **Gate 0 early stopping** -- from the originating request in the shared review briefing (`wf-review`), state the smallest mechanism meeting the request across its class before reading the artifact or its diff. If the core premise fails or the artifact is materially disproportionate under `proportionate`, halt immediately and issue `REJECT` before line-by-line repo auditing. Preserve full rule and acceptance-criteria coverage when Gate 0 passes.
3. **Evaluate against rules and per-claim fail-fast** -- test the artifact against governing axioms (categorical imperative, closure, data boundaries, fail-fast, full observability, honest epistemics, non-delegable qualitative judgment, single source of truth). For candidate publications and trust-boundary transitions, evaluate the full published surface against destination repository visibility under `data-boundaries`. Apply per-claim fail-fast: if a cited claim, path, or authority is falsified, record `UNMET` / violation immediately without searching the repository to author a fix.
4. **Determine required changes vs suggested improvements**:
   - A _Required Change_ names a rule violation, its likelihood and consequence, and costs less than the failure it prevents.
   - Anything else is a _Suggested Improvement_. Where the work exceeds the request, require less, not more.
5. **Review boundaries** -- confine evaluation strictly to the artifact text/diff and governing rule/spec sources (including companion-spec checks). Does not execute runtime tests or scratch probes (the QA role), does not perform whole-codebase omission scans (the QA role), and does not evaluate high-level PKB objective alignment or competing backlog options (the strategic fit role).
6. **Issue verdict**: exactly one of `APPROVE`, `SUGGEST`, `REVISE`, or `REJECT`.
7. **Schedule the next step on a failing verdict** -- a review that returns `REJECT` or `REVISE` schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task.

## Verdict contract

The review returns structured Markdown conforming to:

```markdown
## RBG Review: **[APPROVE | SUGGEST | REVISE | REJECT]**

[1-2 line summary of confidence and overall assessment]

### Required Changes

- **[Rule Name]**: [Violation reason] ([pinpoint reference])

### Suggested Improvements

- **[Rule Name]**: [Improvement suggestion] ([pinpoint reference])
```

- **APPROVE:** Work satisfies rules, exhibits coherent reasoning, and carries valid evidentiary support. Advance to the next workflow stage or deliver.
- **SUGGEST:** Trivial or mechanical improvements identified. The author applies straightforward fixes in place and advances.
- **REVISE:** Material deficiencies or missing proof requiring remediation. The author addresses the required changes and re-submits for review before advancing.
- **REJECT:** Fundamental rule contradiction, ungrounded assertions, or disproportionate work. The workflow halts; excess machinery is cut or the proposal is cancelled/redesigned.

### Handback on a failing verdict

A review that returns `REJECT` or `REVISE` schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task.

## Output contract

The structured review artifact containing exactly one verdict token, itemized required changes with pinpoint citations, suggested improvements, and, on a `REJECT` or `REVISE` verdict, the queued subtask scheduled under the primary task recorded on the review task.

## When to include

Any workflow that produces an intellectual artifact, specification, design proposal, code change, or decision for review, before delivery or escalated sign-off.
