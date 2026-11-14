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
  - Universal framework axioms and rules: read from active PKB documents with `type: axiom` and `type: rule` via PKB MCP (or `pauli`), forming the inviolable baseline.
  - Project-local rules: `$CWD/.agents/rules/` (when present in the target workspace).
  - Enforcement architecture: `specs/enforcement/enforcement.md` (when present in the target workspace and behavior-shaping mechanisms are touched).

## Procedure

1. **Assemble active rules** -- load universal PKB axioms/rules, optional target-workspace project rules, and companion specs (e.g. `specs/enforcement/enforcement.md` when present in the target workspace) before judging; never rule from memory.
2. **Evaluate proportion, non-mechanical baseline, and scope of authority upfront (Gate 0)** -- from the originating request in the shared review briefing, state the non-mechanical baseline: can this request be fulfilled by an agent workflow template, prompt instructions (`SKILL.md`), or existing tools without new executable code? If YES, and the artifact builds a script, CLI, or test harness, immediately halt and issue `FAIL` under `no-over-engineering` and `proportionate` before reading the diff or line-by-line repo auditing. State the smallest mechanism meeting the request across its class before reading the artifact or its diff, and check whether the artifact stays within the authority granted by the request. If the artifact acts _ultra vires_ or is materially disproportionate under `proportionate` and `do-one-thing`, stop immediately and issue `FAIL` before line-by-line repo auditing. Preserve full rule coverage when the artifact is proportionate and within scope.
3. **Evaluate compliance and per-claim fail-fast** -- test the artifact against governing axioms (categorical imperative, closure, data boundaries, excellence, fail-fast, full observability, honest epistemics, human readability first, no over-engineering, non-delegable qualitative judgment, proportionate, single source of truth) and, when `specs/enforcement/enforcement.md` is present in the target workspace, verify that any behavior-shaping change respects its enforcement pyramid (defaulting to least-invasive instructions before adding mechanical gates). Verify that specifications evaluate work from the human principal's perspective (`excellence`, process-not-actor), never casting an agent, persona, or worker as the user in `## User stories` (`As an agent, I want...`), since agents do not want anything and are given capabilities only to fulfil human user requirements. Verify that workflow composition and task-assembly instructions (such as `/james:supervise` and `james:workflow-library`) do not embed hardcoded workflow branching or QA restrictions, enforcing Single Source of Truth (`single-source-of-truth`) and Runtime Workflow Composition. When `specs/ENFORCEMENT-MAP.md` is present and modified in the target workspace, verify entry validity: every row must **only** reference a specific rule derived from universal axioms (`type: axiom` in the PKB) and applicable to agents working in any third-party project (never a repository-local project rule, subsystem feature specification, or workflow; workflows are not rules and do not enforce rules, and creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that). For candidate publications and trust-boundary transitions, evaluate the full published surface against destination repository visibility under `data-boundaries`. Apply per-claim fail-fast with uncontroversial self-fix carve-out: if an identified compliance defect is uncontroversial and deterministic (such as scrubbing private identifiers, session IDs, internal hostnames, or commit trailers under `data-boundaries`, updating language/formatting, or fixing obvious pinpoint citations), apply the fix immediately to the branch, commit with an explanatory message (`fix(review): ...`), and report under `### Reviewer Self-Fixes Applied`. Do not return `REVISE` solely for self-fixed uncontroversial items. For issues lacking a reasonably deterministic solution (competing designs, architectural trade-offs, scope expansion, or missing authority), do not guess or search the repository to author complex fixes; record the violation immediately under `### Required Changes` and return `REVISE` or `FAIL`.
4. **Determine required changes vs suggested improvements**:
   - A _Required Change_ names a rule violation, its likelihood and consequence, and costs less than the failure it prevents.
   - Anything else is a _Suggested Improvement_. Where the work exceeds the request, require less, not more.
5. **Review boundaries** -- confine evaluation strictly to the artifact text/diff and governing rule/spec sources (including companion-spec checks). Does not test functional requirement satisfaction, execute runtime tests/probes, or perform whole-codebase omission scans (the quality role, `marsha`), and does not evaluate the core premise, PKB strategic direction, or congruence with existing graph material (the strategic congruence role, `pauli`).
6. **Issue verdict**: exactly one of `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

The review returns structured Markdown (standard sections and bullet lists formatted for human readability, never programmatic JSON/YAML schemas) conforming to:

```markdown
## RBG Review: **[PASS | REVISE | FAIL]**

[1-2 line summary of confidence and overall assessment]

### Reviewer Self-Fixes Applied

- **[Category / Rule]**: [Description of uncontroversial fix] ([pinpoint reference], Commit: `[commit-hash]`)

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
