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
   settled before compute is spent executing it: [`/q`](../../plugins/ida/skills/q/SKILL.md) places and values repo-scoped epic tasks on the graph ([R1](../workflows/graph-valuation.md#3-r1----placement-at-intake-q)) with `serves` links to targets or target-serving epics, and [`/dispatch`](../../plugins/ida/skills/dispatch/SKILL.md) dispatches them directly to polecat containers. Reification moves inside container supervision ([`/supervise`](../../plugins/ida/skills/supervise/SKILL.md)), where the lead executor (`james`) runs [`/reify`](../../plugins/ida/skills/reify/SKILL.md) to compose workflows solely from template descriptions and contracts onto a single combined task body by default at execution time, verifying that chosen output destinations match repository document-placement rules ([`doc-taxonomy.md`](../meta/doc-taxonomy.md)) and holding brief-locked constraints subject to Gate 0 ask authority (every imposed constraint must derive from the originating user ask or standing mandate). Dispatch surfaces trust the task contract without re-judging the premise. In interactive sessions, triage and intake place tasks without in-session workflow composition; downstream delegates execute without creating additional tasks on the graph. Pure lookups, PKB reads/writes, and questions are handled directly without creating tasks on the graph and without pull/dump ceremonies (`wf-lookup`).
2. **Execution** -- under single-session supervised execution ([`/supervise`](../../plugins/ida/skills/supervise/SKILL.md)), execution runs Stages 1-4 (design, subagent dialectical review, build, and QA/PR verification) in one combined repo-scoped task by default, keeping subagent dialectical review, incremental `git push` checkpoints, and PR verification inside the single container session rather than requiring separate Stage 1 Design / Stage 2 Build / QA child tasks. Separate tasks are split ONLY when a workflow explicitly mandates an out-of-session boundary (a different repository, a different time or external wait condition, or a separate external agent/session such as closed-loop user delivery). For already-decomposed leaf tasks, plain leaf workers execute via [`/pull`](../../plugins/ida/skills/pull/SKILL.md) and hand over via [`/dump`](../../plugins/ida/skills/dump/SKILL.md). When a task's deliverable is a pull request, the container coordinator opens the PR, records `pr_url` and branch, and releases the task as `done` without waiting for CI or merge; when the repository merges the PR, the parent epic progresses. PR descriptions communicate what was done and the approach taken, keeping PRs readable and scannable without duplicating line-by-line diffs; instructions for PR formatting remain modular to allow project-level style overrides.
3. **Rule-compliance review** -- the rule-compliance lens ([`rbg`](../../plugins/rbg/agents/rbg.md), [`wf-rbg.md`](../../plugins/ida/skills/workflow-library/workflows/wf-rbg.md), [`wf-dialectical-review.md`](../../plugins/ida/skills/workflow-library/workflows/wf-dialectical-review.md), [`/strategic-review`](../../plugins/ida/skills/strategic-review/SKILL.md)): did the artifact and handback follow the governing axioms and project rules?
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

Steps 3-4 are assembled at runtime via [`/reify`](../../plugins/ida/skills/reify/SKILL.md) from composable workflow templates ([`workflow-library`](../../plugins/ida/skills/workflow-library/SKILL.md), including [`wf-dialectical-review.md`](../../plugins/ida/skills/workflow-library/workflows/wf-dialectical-review.md), [`wf-rbg.md`](../../plugins/ida/skills/workflow-library/workflows/wf-rbg.md), [`wf-strategic-fit.md`](../../plugins/ida/skills/workflow-library/workflows/wf-strategic-fit.md), and [`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md)). Review
composition -- the lenses, the depth, whether reviewers run as independent downstream tasks -- is structural rather than an ad-hoc instruction. Under single-session supervised execution ([`/supervise`](../../plugins/ida/skills/supervise/SKILL.md)), review steps 3-4 run in-session via subagents (`wf-dialectical-review`, `strategic-review`, `verify`) with incremental `git push` checkpoints, keeping review, build, and verification inside one combined task body. Dedicated child tasks are minted only when crossing out-of-session boundaries. Proof is always written to the task record, plus a `premise-check` verdict receipt. GitHub Actions is one optional executor of code review, never the review system itself.

### Recursion

A task decomposed into subtasks nests this shape: each subtask runs its own
contract -> execution -> review cycle, and the parent
workflow's own step 4 reads the aggregate of its children's outcomes rather
than re-deriving them. An epic is a workflow whose execution step (2) is
itself one or more nested workflows -- the same four steps at a coarser grain,
with no separate contract for "epic-shaped" work.

### Risk-scaled review depth

How much of steps 3-4 run as in-session subagent verification versus a dependent downstream review task is determined during [`/reify`](../../plugins/ida/skills/reify/SKILL.md) solely from the selected workflow template descriptions and contracts in `workflow-library`, calibrated by stakes and blast radius ([`plugins/ida/skills/reify/SKILL.md`](../../plugins/ida/skills/reify/SKILL.md), [`enforcement.md#pr-risk-taxonomy-enforcement`](enforcement.md#pr-risk-taxonomy-enforcement)) -- with zero hard-coded task-class branching and zero low-risk bugfix review exemptions:

- **Description- and contract-driven review inclusion:** All code, bugfix, rule, skill, workflow, and specification deliverables undergo independent proportionate review (scaled in rounds and model tier to stakes and reversibility, never skipped). Under `/supervise`, review steps 3-4 execute inside a single combined container task body with incremental `git push` checkpoints. When a selected workflow mandates an independent downstream review task on the graph (under `/pull` leaf execution or a required separate review session), `/reify` yields **(1) the work task** (which opens the draft PR via `gh pr create --draft` or records the PKB artifact and releases with one completion status: **`done`**, never `review`) and **(2) the review task** (`needs: [<work-task-id>]`, which runs independent review, checks green `HEAD` CI, posts head-SHA-matched verdicts to the PR thread, marks the draft PR ready via `gh pr ready`, evaluates PR risk per the three-tier taxonomy, and releases `done` on pass or `failed` on fail).
- **Design research tasks:** An agent given a design research task does the groundwork and decides the route itself (selecting the recommended route); it never composes a decision task assigned to the user (`assignee: user`) unless the user explicitly directed to decide it themselves.
- **Single completion release status (`done`):** Across all tasks (both PR and non-PR tasks), the work task has one completion release status (`done`) upon fulfilling the frozen acceptance criteria with primary evidence; tasks are never released or demoted by `/reconcile` to `review` awaiting review or merge.
- **High-risk / wide blast radius:** Where sequential gating is warranted, per-chunk review tasks wired with `needs` run their own rule-compliance and substantive QA pass before the next chunk starts.

The invariant across the whole range: a complete set of steps 3-4 runs per the
assembled workflow before a workflow is marked done. A unit may also legally terminate `partial` (see
[`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md#the-partial-terminal-state)):
steps 3-4 then review the shipped chunk plus its declared-deferred
remainder, and draft -> ready-for-the-principal still requires the
specified review.
