---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: Supervisor (james) calibrates proportionality and altitude upfront, coordinates review across strategic direction/congruence (pauli), compliance (rbg), and quality/requirement satisfaction (marsha) into a reconciled PASS, REVISE, or FAIL verdict via james:dialectical-review."
id: wf-dialectical-review
tags:
  - wf-template
  - review
  - dialectic
  - multi-agent
  - briefing
  - default
title: Dialectical Review Workflow
type: template
---

## What this step does

Universal default review workflow template: invokes `/james:dialectical-review` (`james:dialectical-review`), where **`james` as Supervisor** calibrates **proportionality**, **altitude**, and the **governing genre standard** at intake, dispatches three non-overlapping specialist lenses in parallel -- **Strategic Direction & Congruence (`pauli`)**, **Compliance (`rbg`)**, and **Quality & Requirements Satisfaction (`marsha`)** -- and reconciles their findings into a single `PASS`, `REVISE`, or `FAIL` verdict.

## Input contract

The invoking workflow supplies the shared review briefing inputs defined in `james:dialectical-review` (presented before the artifact or diff so reviewers judge intent and proportion before implementation details):

1. **Originating request** -- the commissioning ask quoted verbatim with its source ID.
2. **Target artifact & governing genre standard** -- the file, diff, PR reference, manuscript, or specification under review and the standard governing its genre (`specs/meta/doc-taxonomy.md` and `specs/meta/writing-specs.md` when present in the target workspace, otherwise the standard matching the artifact's genre; never impose task-handback sections like `## Ask` on non-task artifacts).
3. **Available specifications, requirements & acceptance criteria** -- explicit criteria governing the artifact (or explicit notice of their absence, which forces `FAIL` from `marsha`).
4. **Strategic context** -- parent task, target objectives, and related PKB notes or specifications.

## Obligations

Execute the authoritative procedure in `james:dialectical-review`:

1. **Calibrate (`james`)**: Set review depth, deliberation rounds, subagent model tier, primary-material audit scope (`marsha` on high-risk requests), and abstraction altitude.
2. **Dispatch in parallel**: Run `pauli` (`wf-strategic-fit`), `rbg` (`wf-rbg`), and `marsha` concurrently using the shared review briefing. Reviewers apply and commit uncontroversial deterministic self-fixes (`fix(review): <description>`) under `### Reviewer Self-Fixes Applied` without returning `REVISE` solely for those items.
3. **Audit warrants & deliberate**: Verify reviewer reports via `james:premise-check` (`verdict.py --judged-file`), challenge surface readings or unverified note claims of live state, and cross-examine conflicting specialist findings across rounds when warranted by stakes.
4. **Reconcile & release**: Synthesize findings into a unified table and overall verdict (`PASS`, `REVISE`, or `FAIL`). Any expert reviewer's `FAIL` forces a combined `FAIL` and is never downgraded. In headless task execution, `PASS` releases the task as `done` and `REVISE` or `FAIL` releases as `failed` (or `partial`) with findings recorded in `reason`.

## Output contract

- Calibration summary (proportionality, model tier, rounds, primary-material scope, altitude, and governing genre standard).
- Itemized `### Reviewer Self-Fixes Applied` with commit references.
- Unified findings table mapping issues, specialist dispositions, and any unresolved open questions.
- Reconciled overall verdict (`PASS`, `REVISE`, or `FAIL`) with a parser-valid `james:premise-check` `argdown` block, persisted to the tracking task or review surface.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
