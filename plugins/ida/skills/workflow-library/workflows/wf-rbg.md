---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: Universal compliance review -- evaluate candidate artifact, change, or decision against universal axioms, governing rules, scope of delegated authority (ultra vires), data boundaries, and least-invasive enforcement, returning a PASS, REVISE, or FAIL verdict with required changes.
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

Universal compliance review (`rbg`): evaluates an artifact, specification, design proposal, code change, or decision against universal axioms, project-local rules, user rules, delegated authority (_ultra vires_), data boundaries, and least-invasive enforcement using direct logical judgment rather than mechanical pattern-matching.

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Universal axioms**: Injected `always_on` axioms, or read from the `axioms` skill when not injected.
- **Repository local rules**: `.agents/rules/*.md` or equivalent when present.
- **User rules**: Active PKB `type: rule` documents (optional).
- **Repository standards**: Enforcement architecture or document-placement specs when present and touched.

## Procedure

If the target artifact, diff, or originating ask is missing on Turn 1, return `REVISE` listing missing inputs without recording a gate verdict.

1. **Resolve rules**: Treat injected `always_on` universal axioms as loaded (inspect unmodified axiom text only if edited in the diff; read from the `axioms` skill only when not injected). Read repository local rules (`.agents/rules/*.md` or equivalent when present) and active PKB `type: rule` documents directly from source, never from memory.
2. **Inspect full PR metadata, diff, and referenced tests**: Read PR title and body (`data-boundaries`), verify PR labels match any confirmed user route (e.g., hotfix label vs coordinator or user confirmation), read the full diff including deletions, check negative constraints, and inspect static text of test files modified in the PR diff or explicitly cited by the artifact for tautological, change-detector, mirror, or mock-coupled assertions without running repo-wide searches or executing test suites.
3. **Evaluate Gate 0 authority and substantive compliance**:
   - **Ask-bounded authority and non-mechanical baseline (Gate 0)**: Hold additions, deletions, and brief-locked prescriptions strictly to the verbatim user ask or standing user mandate rather than drifted intermediate acceptance criteria. Before line-by-line review, state the non-mechanical baseline from the ask: if an agent workflow, instruction, or existing tool meets the request, halt and `FAIL` unnecessary scripts, CLIs, or harnesses under `no-over-engineering` and `proportionate`; halt and `FAIL` _ultra vires_ or materially disproportionate work.
   - **Least-invasive mechanism and prose generality**: Verify loaded instructions on the same occasion and surface were tried and shown insufficient before accepting hooks, scripts, or extra mechanisms; reject multi-file prose bloat and single-incident prohibitive rules; distinguish neutral baseline runtime orientation from mutable world state, conduct rules, and force gradations.
   - **Waivers, turn errors, and anti-circularity**: Hold cited user or rule waivers strictly to literal quoted bounds (never inferred waivers); reject errors suppressed from the executing agent turn context behind stderr or telemetry logs (`fail-fast`); reject circular specification, test, or tool-injected output relaxations (`closure`); reject unnecessary restatements of existing axioms as new rules, deferred DRY/SSoT defects, or platform-native duplication (`single-source-of-truth`, `use-native-mechanism`).
   - **Required Changes vs Suggested Improvements**: A Required Change names a rule violation, its likelihood and consequence, and costs less than the failure it prevents; anything else is a Suggested Improvement (where work exceeds the request, require less, not more).
4. **Apply conditional genre, destination, and egress compliance**: When diffs touch agent definitions, skills, workflows, specifications, or plan/doc destinations, apply the repository's governing instruction/craft, specification, and document-placement rules when present (contract separation, human-principal user stories never casting agents as users, runtime workflow composition without hardcoded template routing or workflow rows in enforcement maps) alongside `data-boundaries` public egress across diffs, titles, bodies, commits, trailers, and route/auth or endpoint-visibility diffs risking unapproved public exposure of private endpoints.
5. **Certify committed fixes, respect boundaries, and post verdict**: Apply uncontroversial deterministic repairs (scrubbing private identifiers under `data-boundaries`, typos, pinpoint citations) directly, commit (`fix(review): ...`), and push so `HEAD` matches inspected diff before `PASS` (or itemize under `### Suggested Fixes` when dispatched read-only in parallel for single-writer commit before `PASS`; never `REVISE` solely for self-fixed items); leave non-deterministic issues under `### Required Changes`. `Needs judgment: no` in proportion notes cannot bypass Gate 0 or fail-fast checks. Confine evaluation strictly to static compliance, authority, and egress (never runtime QA, qualitative taste, relay truth/fidelity, or strategic congruence), and post explicit `## RBG Review: PASS | REVISE | FAIL` directly on the PR thread when permitted by `data-boundaries`.

## Verdict contract

Return structured Markdown for human readability (never JSON/YAML schemas):

```markdown
## RBG Review: [PASS | REVISE | FAIL]

[1-2 line summary of confidence and overall assessment]

### Reviewer Self-Fixes Applied

- **[Category / Rule]**: [Description of fix] ([pinpoint reference], Commit: `[commit-hash]`)

### Proportion & Mechanisms

- **Baseline vs Artifact**: [Minimal non-mechanical baseline vs mechanism proposed; consequence, `Needs judgment: yes|no`, rule]

### Required Changes

- **[Rule Name]**: [Violation reason and risk] ([pinpoint reference])

### Suggested Improvements

- **[Rule Name]**: [Improvement suggestion] ([pinpoint reference])
```

- **PASS:** Compliant with governing rules, within delegated authority, coherent, and validly supported.
- **REVISE:** Remediable rule gaps or missing justification within accepted scope.
- **FAIL:** Fundamental rule breach, ungrounded assertions, _ultra vires_ overreach, or disproportionate mechanism.

## Output contract

Structured review returning one verdict token (`PASS`, `REVISE`, or `FAIL`), proportion assessment, any committed and pushed self-fixes, itemized required changes with pinpoint citations, and suggested improvements.

## When to include

Any workflow producing an artifact, specification, design proposal, code change, or decision for compliance review prior to merge or release.
