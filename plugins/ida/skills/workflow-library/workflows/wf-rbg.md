---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: Universal compliance review -- evaluate candidate artifact, change, or decision against universal axioms, governing rules, scope of delegated authority (ultra vires), and the enforcement pyramid, returning a PASS, REVISE, or FAIL verdict with required changes.
id: wf-rbg
tags:
  - wf-template
  - review
  - rbg
  - rules
  - compliance
title: Rule-Compliance Review
type: template
---

## What this step does

Universal compliance review (`rbg`): evaluates an artifact, specification, design proposal, code change, or decision for compliance with universal axioms, project-local rules, scope of delegated authority (_ultra vires_), data boundaries, and the enforcement pyramid's least-invasive intervention hierarchy. Exercises direct logical judgment against the intent behind the rule, the intended and incidental uses of the work, and the gravity of the situation rather than mechanical pattern-matching.

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Rule sources** -- assembled in priority order:
  - Framework axioms: the `rbg:axioms` skill (inviolable baseline).
  - Project-local rules: `$CWD/.agents/rules/`.
  - Account-scoped rules: read from active PKB rules.
  - Enforcement architecture: `specs/enforcement/enforcement.md` (when behavior-shaping mechanisms are touched).

## Procedure

1. **Assemble active rules** -- load governing axioms, project rules, and companion specs (e.g. `specs/enforcement/enforcement.md`) before judging; never rule from memory.
2. **Evaluate proportion and scope of authority upfront** -- from the originating request in the shared review briefing, state the smallest mechanism meeting the request across its class before reading the artifact or its diff, and check whether the artifact stays within the authority granted by the request. If the artifact acts _ultra vires_ or is materially disproportionate under `proportionate` and `do-one-thing`, stop immediately and issue `FAIL` before line-by-line repo auditing. Preserve full rule coverage when the artifact is proportionate and within scope.
3. **Evaluate compliance and per-claim fail-fast** -- test the artifact against governing axioms (categorical imperative, closure, data boundaries, fail-fast, full observability, honest epistemics, non-delegable qualitative judgment, single source of truth) and verify that any behavior-shaping change respects the enforcement pyramid (`specs/enforcement/enforcement.md`, defaulting to least-invasive instructions before adding mechanical gates). For candidate publications and trust-boundary transitions, evaluate the full published surface against destination repository visibility under `data-boundaries`. Apply per-claim fail-fast: if a cited claim, path, or authority is falsified, record `UNMET` / violation immediately without searching the repository to author a fix.
4. **Determine required changes vs suggested improvements**:
   - A _Required Change_ names a rule violation, its likelihood and consequence, and costs less than the failure it prevents.
   - Anything else is a _Suggested Improvement_. Where the work exceeds the request, require less, not more.
5. **Review boundaries** -- confine evaluation strictly to the artifact text/diff and governing rule/spec sources (including companion-spec checks). Does not test functional requirement satisfaction, execute runtime tests/probes, or perform whole-codebase omission scans (the quality role, `marsha`), and does not evaluate the core premise, PKB strategic direction, or congruence with existing graph material (the strategic congruence role, `pauli`).
6. **Issue verdict**: exactly one of `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

The review returns structured Markdown conforming to:

```markdown
## RBG Review: **[PASS | REVISE | FAIL]**

[1-2 line summary of confidence and overall assessment]

### Required Changes

- **[Rule Name]**: [Violation reason] ([pinpoint reference])

### Suggested Improvements

- **[Rule Name]**: [Improvement suggestion] ([pinpoint reference])
```

- **PASS:** Work satisfies governing rules, stays within its delegated authority, exhibits coherent reasoning, and carries valid evidentiary support (with any non-blocking suggestions noted under Suggested Improvements).
- **REVISE:** Material deficiencies or missing proof requiring remediation within the accepted scope.
- **FAIL:** Fundamental rule contradiction, ungrounded assertions, _ultra vires_ overreach, or disproportionate work.

## Output contract

The structured review artifact containing exactly one verdict token (`PASS`, `REVISE`, or `FAIL`), itemized required changes with pinpoint citations, and suggested improvements.

## When to include

Any workflow that produces an intellectual artifact, specification, design proposal, code change, or decision for review, before delivery or escalated sign-off.
