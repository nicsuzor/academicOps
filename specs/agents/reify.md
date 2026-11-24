---
title: Reify
status: ready
---

# Reify

Turn a terse user prompt into a durable, enriched task node carrying intent,
workflow, execution steps and guardrails -- so any worker can pull it and execute
without gathering context again.

Reification works on one node at the moment it is next to run (the micro
altitude of the planning pipeline). `/reify` runs inside container supervision
(`/supervise`) or on explicit planning request. In supervised epic execution,
the lead executor (`james`) runs `/reify` to bind the claimed task to an executor
and composed workflow from the template library at execution time, avoiding premature
reification and stale tasks on the graph. A node whose prerequisites are outside
the graph's control stays unreified until they clear. Expanding an objective into
the nodes themselves is the preceding stage (decomposition), which binds nothing
to an executor. On explicit planning requests, the PKB custodian (`pauli`) can also
run reification.

This skill does _enrichment_: selecting a workflow, interpreting it
into concrete steps, attaching guardrails, and **writing the result onto a task
node**. That durability is the whole point: an enriched task survives session loss,
is visible to other sessions, and carries its own audit trail.

## Outputs

The hydrator emits four components, and the main agent executes them without
making further routing decisions:

| Component | Content |
| - | - |
| Intent | What the user actually wants, stated plainly |
| Workflow | The selected template from the workflow catalog, plus its quality gate |
| Execution steps | The workflow interpreted for _this_ request as concrete numbered steps, `CHECKPOINT:`-prefixed where the workflow mandates verification |
| Guardrails | The constraints the selected workflow imposes |

## Workflow Resolution: Three-Tier Template Library

`/reify` absorbs 3-tier template resolution (`Project > PKB > Universal`) from `/workflow-library`:

- **Fast-Path**: If the task already carries a composed workflow (`## Instructions` and `## Appendix: Sources`) or requires invoking a single skill (`invoke /<skill>`), skip redundant re-composition and proceed directly to planning.
- **3-Tier Resolution**:
  1. `Project`: PKB documents carrying `type: template` whose frontmatter `project` matches the task's `project` (determine the shadowed slug by stripping an optional `<project>-` or `<project>_` prefix from `id` when present; otherwise use `id` directly).
  2. `PKB`: PKB documents carrying `type: template` with no `project` (absent or `null`).
  3. `Universal`: Built-in templates in `plugins/ida/skills/workflow-library/workflows/*.md`.

Selection is interpretive, not mechanical: `/reify` reads the template and generates steps for the specific request. A plan that instructs the main agent to go read a workflow file has failed -- the whole cost saving is that the reading already happened.

**`CHECKPOINT:` is behavioural guidance, not enforcement.** No code blocks
progress when verification is skipped. This is deliberate: enforcement here would
need a gate that can read evidence, which is a larger design than this one, and
the failure mode of a missed checkpoint is recoverable.

## Task body length and step inlining

Task bodies are strictly concise: 50-150 words for atomic tasks, and up to 300 words for multi-stage composite workflows.

Step inlining is interpretive, not mechanical transcription:

- Workflow templates (`wf-*`) cannot be invoked by workers. Each composed template stage, obligation, and quality gate is interpreted into a concise numbered imperative step in Instructions.
- Inlining distills the required outcome or verification checkpoint for each stage; it omits narrative prose, rationale, background explanations, and implementation methods the worker can determine for itself.
- Every composed template stage and finish obligation is represented as a concrete step so no required process or gate is lost, while staying strictly within the 300-word ceiling for composite workflows (or 150 words for atomic tasks).
- Outcome-oriented criteria: Reified tasks define observable end-state conditions and verification criteria rather than implementation mechanisms. Line numbers, line ranges, and narrow code slice prescriptions are strictly forbidden in `Goal`, `Acceptance criteria`, and `Execution steps` / `Instructions`.
- Combined single-session task body by default: `/reify` writes a single combined repo-scoped task body by default, keeping design, subagent dialectical review, build, incremental `git push` checkpoints, and PR verification inside the single supervised container session rather than mandating separate Stage 1 Design / Stage 2 Build / QA child tasks.

## Task Splitting, Two-Task Reviewed Classes, and Out-of-Session Boundaries

`/reify` writes a single combined repo-scoped task body by default under container supervision (`/supervise`), where subagent dialectical review, testing, incremental `git push` checkpoints, and PR verification execute in-session.

When a class of task has an independent review process reified onto the task graph (rather than folded into a single-session `/supervise` run), reifying it yields **two separate tasks** under the parent container:

1. **The work task**: Completes the deliverable, opens the draft PR (`gh pr create --draft`) or records the PKB artifact, ticks met acceptance criteria with primary evidence, and releases with one completion status: **`done`** (never `review`).
2. **The review task** (`needs: [<work_task_id>]`): Unblocks when the work task is `done`, runs the independent proportionate review, posts verdicts to the PR thread, marks the draft PR ready (`gh pr ready`), and releases `done` on pass or `failed` on fail.

Unreviewed task classes (routine documentation, notes, trivial chores, and low-risk internal bugfixes) yield only the work task, which releases as `done`. Outside the work-task + review-task pair for reviewed classes, separate tasks are split ONLY when a workflow explicitly mandates:

1. A different repository (strictly one task per repository);
2. A different time or external wait condition;
3. A separate external agent or session (such as independent downstream review or closed-loop `assignee: ida` user-channel delivery).

For research tasks investigating open design questions or architectural choices, the agent does the groundwork and makes the decision itself (selecting the recommended route); it never composes a decision task assigned to the user (`assignee: user`) unless the user explicitly directed to decide it themselves.

Worker self-release to `done` is preserved across all tasks: every work task has one completion release status (`done`) upon satisfying the frozen acceptance checklist with concrete evidence, and is never released or moved to `review`.

## Context gathering

| Tier | Source | Role |
| - | - | - |
| 1 | PKB, via `aops:hydrate` | Primary -- semantic search for related knowledge and open tasks |
| 2 | Framework specs and axioms | Secondary -- the principles that bind this work |
| 3 | GitHub / web search | Tertiary -- only when internal sources are insufficient |
| 4 | Session transcripts | Last resort -- very recent context not yet written anywhere |

Tiers 1-2 run inside the hydrator against a budget of roughly 450 tokens of
retained context. Tiers 3-4 are never run by the hydrator; they are emitted as
execution steps for the main agent, because they are slow and usually
unnecessary.
