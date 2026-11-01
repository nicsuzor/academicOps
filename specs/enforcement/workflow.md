---
id: enforcement-workflow
title: Enforcement -- The Workflow
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, workflow]
---

# Enforcement -- The Workflow

## aops -- Workflow

A set of tasks and subtasks that make up a more user-reviewable,
user-directed unit of work.

At the workflow scope, the framework cares about _how_ the work is
done, not only the outcome -- in contrast to the execution span inside a single
task, where the posture is trust-the-method.

### Mechanisms

- **Runtime workflow composition via [`/reify`](../../plugins/ida/skills/reify/SKILL.md) and [`workflow-library`](../../plugins/ida/skills/workflow-library/SKILL.md)** --
  task-template conventions, composable workflow templates across universal, PKB, and project tiers, and proof-of-compliance tool fields assemble a compliant workflow before the unit is dispatched.
- **The supervisor loop** ([`sara.md`](../agents/sara.md)) -- the
  delegate-and-verify loop that coordinates execution and verifies returned reports across a set of tasks.

## The four-step shape

A workflow is assembled at runtime from composable templates in the [`workflow-library`](../../plugins/ida/skills/workflow-library/SKILL.md) rather than prescribed as a fixed pipeline. Only the mechanical lifecycle steps every task shares -- claiming (`claim_task`) and releasing (`release_task`) the task -- are fixed; the composing pass selects templates for the work between them based on the task's domain, risk, and deliverables. A literature review, a paper critique, and a code change share the same task contract ([`task-contract.md`](task-contract.md)) with different assembled workflows (citation verification, methodological soundness, container validation).

1. **Contract and composition** -- the unit's premise, worth, and acceptance criteria are
   settled before compute is spent executing it: [`/q`](../../plugins/ida/skills/q/SKILL.md) places and values the work on the graph ([R1](../workflows/graph-valuation.md#3-r1----placement-at-intake-q)), and [`/reify`](../../plugins/ida/skills/reify/SKILL.md) composes the workflow from templates, writes the dispatchable task (`queued`), and mints any downstream QA task (`needs: [<primary_task_id>]`). The previously separate standalone premise-gate ceremony at the spend surfaces ([`/pull`](../../plugins/ida/skills/pull/SKILL.md), [`/dispatch`](../../plugins/ida/skills/dispatch/SKILL.md)) is retired; dispatch surfaces trust the reified contract without re-judging the premise themselves. `/reify` plans only: it writes tasks to the graph and never dispatches or runs them itself.
2. **Execution** -- the claimed worker executes the task ([`/pull`](../../plugins/ida/skills/pull/SKILL.md)) and hands over via [`/dump`](../../plugins/ida/skills/dump/SKILL.md). This span is
   trust-the-method: no process-level micromanagement during execution, with evidence-driven intervention
   only if something goes wrong. When a task's deliverable is a pull request, the worker opens the PR, records `pr_url` and branch, and releases the task as `done` without waiting for CI or merge; releasing `done` immediately unblocks dependent follow-ups (such as independent QA tasks); when the repository merges the PR, the parent epic progresses. In a spec-then-build workflow (one branch, one PR), the spec goes out as a draft PR into the base branch carrying the spec, and its review verdict is recorded on that PR; the spec task never merges on its own. After approval, the feature is built on the same branch and PR, with the spec still editable as more is learned; the PR flips to ready once the feature is written and ready for full review, without waiting for approval; spec and feature merge together after full review. PR descriptions communicate what was done and the approach taken, keeping PRs readable and scannable without duplicating line-by-line diffs; instructions for PR formatting remain modular to allow project-level style overrides.
3. **Rule-compliance review** -- the rule-compliance lens ([`rbg`](../../plugins/rbg/agents/rbg.md), [`wf-rbg.md`](../../plugins/ida/skills/workflow-library/workflows/wf-rbg.md), [`wf-review.md`](../../plugins/ida/skills/workflow-library/workflows/wf-review.md), [`/strategic-review`](../../plugins/ida/skills/strategic-review/SKILL.md)): did the artifact and handback follow the governing axioms and project rules?
   Evaluates the target artifact, contract, and handback against [`task-contract.md`](task-contract.md)'s
   `release_task` evidence gate (Work-Unit Contract) and the acceptance criteria
   set in step 1.
4. **Substantive QA verification** -- the QA lens ([`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md), [`/verify`](../../plugins/ida/skills/verify/SKILL.md)): does the delivered artifact actually do what
   step 1's contract asked, and does it do it excellently at runtime? Distinct from step 3: rule-compliance review asks whether the rules were
   followed; substantive QA asks whether the work works and meets the excellence bar.

Steps 3 and 4 read and produce claims in the same shape: see
[evidence-contract.md](evidence-contract.md): every load-bearing claim at each
step carries checkable evidence or a stated failure reason. At steps 3 and 4
the reviewer opens each pointer, confirms it supports its claim, and checks
that the acceptance criterion itself was met.

### Review composition

Steps 3-4 are assembled at runtime via [`/reify`](../../plugins/ida/skills/reify/SKILL.md) from composable workflow templates ([`workflow-library`](../../plugins/ida/skills/workflow-library/SKILL.md), including [`wf-review.md`](../../plugins/ida/skills/workflow-library/workflows/wf-review.md), [`wf-rbg.md`](../../plugins/ida/skills/workflow-library/workflows/wf-rbg.md), [`wf-strategic-fit.md`](../../plugins/ida/skills/workflow-library/workflows/wf-strategic-fit.md), and [`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md)). Review
composition -- the lenses, the depth, whether reviewers run as independent downstream tasks -- is structural rather than an ad-hoc instruction. Workflow templates set the reusable patterns for these choices
and evolve over time. Any surface satisfying the assembled workflow's
requirements qualifies as an executor: an independent polecat session ([`/dispatch`](../../plugins/ida/skills/dispatch/SKILL.md)) that
validates runtime behavior with [`/verify`](../../plugins/ida/skills/verify/SKILL.md) for code changes, or
review subagents running [`/strategic-review`](../../plugins/ida/skills/strategic-review/SKILL.md) for rule compliance, strategic fit, and substantive quality.
Proof is always written to the task record, structured either within a single task with internal subtasks or as child tasks under a dedicated epic (e.g. `Child 2: QA: <primary task title>`, `needs: [<child_1_id>]`), never as loose siblings under an external parent, plus a `premise-check` verdict receipt.
GitHub Actions is one optional executor of code review, never the review system
itself.

### Recursion

A task decomposed into subtasks nests this shape: each subtask runs its own
contract -> execution -> review cycle, and the parent
workflow's own step 4 reads the aggregate of its children's outcomes rather
than re-deriving them. An epic is a workflow whose execution step (2) is
itself one or more nested workflows -- the same four steps at a coarser grain,
with no separate contract for "epic-shaped" work.

### Risk-scaled review depth

How much of steps 3-4 run as standalone downstream review tasks versus how much is folded into the next run or a consolidated review pass is determined during [`/reify`](../../plugins/ida/skills/reify/SKILL.md) based on
the task's risk and blast radius ([`plugins/ida/skills/reify/SKILL.md:85-98`](../../plugins/ida/skills/reify/SKILL.md), [`enforcement.md#pr-risk-taxonomy-enforcement`](enforcement.md#pr-risk-taxonomy-enforcement)):

- **Substantive deliverables (features, refactors, multi-file changes)** -- structured per the follow-up placement invariant as a dedicated epic with child tasks (`Child 1: Primary Task`, `Child 2: QA: <primary task title>`, with `Child 2` `needs: [Child 1]`), never as loose siblings under an external parent, verifying the delivered artifact at runtime and evaluating PR risk against the three-tier taxonomy (`Tier 1` autonomous QA-merge vs `Tier 2` / `Tier 3` reviewer or principal sign-off).
- **Design research tasks** -- `/reify` composes a dependent decision task assigned to the user (`assignee: user`) by default (`Title: Decide implementation route for <topic>`, `depends_on: [<research_task_id>]`) before downstream implementation tasks can unblock.
- **Non-PR tasks (analyses, docs, research, operational tasks)** -- `/reify` mints a separate `QA: <task>` child task only where the composed workflow warrants an independent check (such as empirical analyses with replication requirements, high-impact policy or specification changes, or multi-step qualitative audits). Workflows that do not warrant a separate verification pass (routine documentation updates, straightforward queries, direct single-source summaries) mint no QA child. Across all tasks (both PR and non-PR tasks), worker self-release to `done` is standard upon fulfilling the frozen acceptance criteria; workers are never held in `review` awaiting a downstream gate.
- **High-risk / wide blast radius** -- per-chunk review tasks wired with
  `depends_on`, each running its own rule-compliance and substantive QA pass before the
  next chunk starts.
- **Low-risk bugfixes (`severity: low` / narrow blast radius)** -- rather than spawning a separate container session solely to verify a minor fix, `/reify` folds a 1-2 line verification check into the next scheduled task or run that touches the affected component, and workers hand back commits under one shared PR over the coupled set ([`task-contract.md`](task-contract.md)).

The invariant across the whole range: a complete set of steps 3-4 runs per the
assembled workflow before a workflow is marked done. A unit may also legally terminate `partial` (see
[`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md#the-partial-terminal-state)):
steps 3-4 then review the shipped chunk plus its declared-deferred
remainder, and draft -> ready-for-the-principal still requires the
specified review.
