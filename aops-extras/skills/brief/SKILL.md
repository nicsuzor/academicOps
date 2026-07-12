---
name: brief
type: skill
category: instruction
description: Just before dispatch, expand exactly the subtask(s) due next into a seven-element delegation brief (intent, scoped context, limits, autonomy, acceptance criteria, evaluation-evidence contract, effort/door-type) a contextless smart agent can execute and be judged on. Personality-agnostic; the composer must never be the executor.
triggers:
  - "brief this task"
  - "brief the subtask"
  - "write a delegation brief"
  - "prepare for dispatch"
  - "dispatch brief"
  - "expand for execution"
modifies_files: true
needs_task: true
mode: execution
domain:
  - planning
  - delegation
allowed-tools: Read,mcp__pkb__get_task,mcp__pkb__append,mcp__pkb__update_task,mcp__pkb__get_dependency_tree,Skill,Task
version: 1.0.0
permalink: skills-brief
---

# Brief Skill

You are a **delegating commander**: you trust the executor and set expectations, not methods.
[[skills-decompose]] already cut the DAG and composed the process regime — your only job is to take
the one (or few) subtask(s) that are due **right now** and turn each into a brief a contextless
agent can act on and be judged on. You carry no architectural judgment (that's decompose's) and you
never touch the work's substance yourself.

## Hard rule — the composer is not the executor

**The agent identity that writes this brief must not, in the same invocation, be the agent identity
that executes the subtask.** Same-context self-instruction has been observed not to bind: an agent
that has just reasoned its way to a plan inline will act on that reasoning trace directly and skip
the discipline the brief exists to impose (see [`references/authoring-discipline.md`](references/authoring-discipline.md) §3
for the incident record this rule comes from). Concretely:

- Compose the brief, persist it to the task body, then dispatch **by task-id reference** — hand the
  executor a task id, never the freshly-composed brief text inlined as a prompt. The executor's
  first act is to read the brief fresh from the task, not from your reasoning.
- If you find yourself about to start doing the subtask's actual work in this same call — stop.
  That is the executor's job in the next invocation, not yours.
- This rule holds regardless of personality binding: unlike `situate`/`decompose` (earmarked to
  pauli for permission-control reasons), `brief` is personality-agnostic — any capable agent may
  compose a brief, but never the one about to execute it.

## Scope — rolling-wave, brief only what's due

Decompose already produced an unexploded DAG of session-sized, titled subtasks plus the epic's
composed regime. Your job is narrow on purpose:

- Brief **exactly** the subtask(s) about to be dispatched next (their dependencies are resolved,
  they're at the front of the queue). Do **not** pre-write briefs for subtasks further out — later
  ones may be reshaped by what this wave returns, and paying the briefing cost early is exactly the
  waste rolling-wave elaboration avoids.
- Do not re-cut, re-sequence, merge, or split the subtask — that's a decompose-stage decision. If
  the subtask as titled genuinely can't be briefed (it's really two responsibilities, or a
  dependency is missing), flag it back rather than silently restructuring.
- Do not invent mid-stream approval theatre ("draft it, then surface for review before proceeding")
  — the regime decompose composed already places gates at the real junctures; don't add more.

## Step 1 — read what's already there, refresh only if stale

`get_task` the subtask and its parent epic. You're looking for: the one-line scope decompose left,
the subtask's `door-type`, and any composed gate/process templates wikilinked onto it or the epic
(e.g. `[[workflows-gates-qa]]`) — carry these forward, don't re-derive them. If the hydrate bundle on
this task predates material changes (the codebase moved, a dependency resolved differently than
assumed, real time has passed since decompose ran), invoke [[skills-hydrate]] for a refresh rather
than trusting a stale bundle — a brief built on stale context is worse than a slow one.

## Step 2 — compose the seven elements

Write the brief in prose, one pass per subtask due. The full fill-in shape, with guidance on what
belongs (and doesn't) in each element, is `references/brief-template.md`. In brief:

1. **Intent (+why)** — the end-state, and why it matters to the parent. Lets the executor adapt when
   reality diverges from your model of it.
2. **Scoped context** — pointers to _just_ the resources needed to start cold (spot-checkable node
   ids, file paths, prior decisions). Withhold the epic's broader strategic reasoning — extraneous
   strategy distorts tactical judgment, it doesn't sharpen it.
3. **Constraints** — left/right limits: what must not change, what's out of bounds.
4. **Autonomy + non-goals** — what the executor decides alone, and what's explicitly not theirs to
   do.
5. **Done + observable acceptance criteria** — set now, at design time, not left for the executor to
   infer. Frame the _outcome to verify_, not the edit you imagine produces it (never prescribe file
   paths, function names, or a step list — the one exception is a READ-DO sequence for genuinely
   order-critical or dangerous work; see [`references/authoring-discipline.md`](references/authoring-discipline.md) §1 for
   the failure mode this guards against).
6. **Emit-for-evaluation contract** — what the executor must hand back for a separate evaluator to
   reach a verdict without re-investigating: the quality rubric it's judged against, the
   claim-provenance rule (observed vs. inferred, cited not asserted), and the procedural record
   (what regime steps were followed).
7. **Effort budget + door-type** — carry forward decompose's door-type classification; only
   reclassify if new evidence changed the reversibility call, and say so explicitly if you do. Name
   a rough size (session-sized, per decompose's cut) so the executor knows the expected shape of the
   deliverable.

Never a step-script. If your draft reads like a numbered list of things to do rather than a
statement of intent and limits, you've over-specified — cut it back to outcome + criteria.

## Step 3 — persist and dispatch

`append` the brief to the subtask's task body (append-only — never overwrite prior content). Then
dispatch by task-id reference (per the hard rule above). If more than one subtask is due in this
wave, brief and dispatch each independently — don't bundle them into one combined brief.

## Must not

- Centrally plan the subtask's internals (paths, functions, exact steps) — that's the executor's
  judgment to exercise, not yours to pre-empt.
- Add approval gates beyond what the composed regime already specifies.
- Brief subtasks that aren't due next.
- Execute the subtask yourself, in this or any subsequent turn of the same invocation.

## Fitness test (self-check before you finish)

Two readers, from the emitted brief alone:

- **The executor** — a contextless agent reading only the task body — can start without asking "what
  has already been tried?" or "what am I allowed to touch?"
- **The evaluator** — a separate agent applying `/verify` or `/strategic-review` later — can reach a
  PASS/FAIL/re-dispatch verdict from the emitted evidence the brief demanded, without re-doing the
  investigation itself.

If either reader would need to ask a clarifying question your brief could have answered, it isn't
done.
