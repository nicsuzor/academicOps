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

The invoking workflow provides:

1. **Target artifact** -- the document, specification, design proposal, code diff, or decision under review.
2. **Context and intent** -- original user prompt, commission objective, or task acceptance criteria.
3. **Rule sources** -- assembled in priority order:
   - Framework axioms: `plugins/rbg/axioms/` (inviolable baseline).
   - Project-local rules: `$CWD/.agents/rules/`.
   - User-scoped rules: read from active PKB rules.

## Procedure

1. **Assemble active rules** -- load governing axioms and project rules before judging; never rule from memory.
2. **Judge proportion first** -- state the smallest mechanism meeting the request across its class before reading the artifact; reject excess machinery under `proportionate`.
3. **Evaluate against rules** -- test the artifact against governing axioms (categorical imperative, closure, data boundaries, fail-fast, full observability, honest epistemics, non-delegable qualitative judgment, single source of truth).
4. **Determine required changes vs suggested improvements**:
   - A _Required Change_ names a rule violation, its likelihood and consequence, and costs less than the failure it prevents.
   - Anything else is a _Suggested Improvement_. Where the work exceeds the request, require less, not more.
5. **Issue verdict**: exactly one of `APPROVE`, `SUGGEST`, `REVISE`, or `REJECT`.

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

## Output contract

The structured review artifact containing exactly one verdict token, itemized required changes with pinpoint citations, and suggested improvements.

## When to include

Any workflow that produces an intellectual artifact, specification, design proposal, code change, or decision for review, before human presentation or acceptance.
