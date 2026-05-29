---
name: pull
type: command
category: instruction
description: Advance the queue one step — pick the next queued task and DISPATCH it to the right surface. Never executes inline. Thin one-shot alias over the program loop's dispatch trigger.
triggers:
  - "pull task"
  - "get work"
  - "what should I work on"
  - "next task"
  - "advance the queue"
modifies_files: false
needs_task: false
mode: dispatch
domain:
  - operations
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion, mcp__pkb__get_task, mcp__pkb__get_task_children, mcp__pkb__list_tasks, mcp__pkb__update_task
permalink: commands/pull
---

# /pull — Advance the Queue One Step (Dispatch, Not Execute)

**Purpose**: Pick the next queued task and **dispatch it to the right surface** (a polecat, or an in-process subagent), then stop. `/pull` does **one** dispatch step and exits. It never executes the task in this session.

> **What changed (WS4).** `/pull` used to mean "claim the next task and grind it inline here." That self-execution semantics is **retired** — it was the exact context-burn the north star forbids: the session that wanted to _advance_ the queue ended up _consuming_ its context on one task, shrinking its supervision breadth. The work a task needs now happens on the surface it is dispatched to (a polecat that ships a PR, or a subagent that reports back), never in the session that ran `/pull`.

## Where this lives

`/pull` is the **thin manual, one-shot face** of the **dispatch trigger** owned by the program/portfolio loop — `skills/program/SKILL.md`, [Tick Decision Order](../skills/program/SKILL.md#tick-decision-order) step 2 ("Dispatch trigger — the WS4 seam"). The program loop runs that trigger _continuously_ across the whole portfolio; `/pull` performs **exactly one** step of the same "choose + route the next ready task" logic by hand, for a solo session where Nic wants to nudge one dispatch without standing up the loop.

There is **no daemon and nothing auto-claims** queued work (the v0.4 "polecats auto-claim queued work" claim was overstated — James #2). A polecat only ever runs a task that was _explicitly dispatched_ to it, and it ships a PR. `/pull` is one such explicit dispatch.

## Workflow (one dispatch, then stop)

### Step 1: Select the next queued task

Per [[../skills/remember/references/TAXONOMY.md]] §Status Values: dispatch only from `queued` (the human-gated dispatch queue). Tasks in `ready` are decomposed-but-unapproved and MUST NOT be dispatched here — the user promotes `ready` → `queued` manually.

- **No argument**: call `mcp__pkb__list_tasks(status="queued", limit=10, format="json")` and pick the highest-`focus_score` task. `focus_score` is the composite ranking (severity, priority, downstream weight, deadline urgency, stakeholder waiting, decay) — see [[multi-parent]] §7. Do NOT rank by any single component directly.
- **`/pull <task-id>`**: call `mcp__pkb__get_task(id="<task-id>")`. If it has children, descend to the first `queued` leaf. Dispatch that leaf, not the parent.
- **Nothing queued**: report "no queued tasks to dispatch" and stop. Do not reach into `ready`/`inbox` to manufacture work, and do not start doing anything yourself.

### Step 2: Route it to a surface (the dispatch-trigger heuristic)

Choose exactly one surface for the selected task — this is the same routing decision the program loop's decision-order step 2 makes, at one-task granularity:

- **Specialist sub-agent** — if the task (or its parent epic) has an `assignee` naming a specialist:
  - `aops-core:<name>` → dispatch with `subagent_type="<name>"` (strip the prefix).
  - `polecat` → dispatch with `subagent_type="polecat"`.
  - Known specialists: `marsha`, `rbg`, `pauli`, `james`, `junior`, `qa`, `enforcer`, `polecat`. Any value matching those namespaces is a specialist; the namespace is the trigger.
- **Polecat** — for repo-scoped, PR-shippable work (code/docs/tests) with no named specialist. Dispatch a polecat run; it claims, runs, and ships a PR. (There is no inline `polecat finish` step here — `/pull` does not run the task, so it has nothing to finish.)
- **Subagent (Task tool)** — for research/synthesis/triage that must return findings to this session rather than ship a PR.
- **Defer** — if the task is not actually ready to dispatch (missing inputs, genuinely blocked, or needs human judgment to even scope), do NOT force a dispatch and do NOT execute it yourself. Record why (`mcp__pkb__update_task` with a one-line note, or surface it to Nic) and stop.

**Dispatch brief must be self-contained** — the dispatched surface does not share this session's context. Include the task ID, title, full body, acceptance criteria, and any file paths in scope.

### Step 3: Record the dispatch and stop

Mark what you dispatched so the next `/pull` — or the program loop's next tick — is stateless and won't double-dispatch the same leaf:

- Claim-on-dispatch is the _surface's_ job, not `/pull`'s. When you hand a task to a polecat, the polecat claims it (`in_progress`) as it starts. Do **not** mark the task `in_progress` from this session and then walk away holding a claim you won't execute.
- If you need a durable marker that this leaf is in-flight (e.g. for a subagent dispatch that doesn't self-claim), set `assignee` to the dispatched surface and leave a one-line note via `mcp__pkb__update_task`. Never set status to a value that implies _this_ session is doing the work.

**Then HALT.** One dispatch per `/pull`. Do not loop, do not chain a second dispatch, and do not start executing the task you just dispatched. For continuous, multi-task advancement use the **program loop** (`/program`, driven by `/loop`), which is built for stateless repeated dispatch ticks — `/pull` is deliberately one-shot.

## Anti-patterns (these are the retired behaviour — do not do them)

- **Executing the task inline.** Editing files, running the task's tests, or committing its changes _in this session_ is the retired self-execution path. If you find yourself doing it, you have violated the contract — dispatch instead.
- **Holding a claim without executing.** Marking the task `in_progress` from this session is only correct if _this session is the executing surface_ — and under WS4 it never is. Let the dispatched surface claim.
- **Looping `/pull` to burn down the queue.** That re-creates the inline-grind treadmill one dispatch at a time. Use `/program` for sustained advancement.
- **Decomposing/triaging-then-doing.** If the selected task needs decomposition, that is a `/supervisor` / planner concern — route it there or defer; do not decompose-then-execute inline.

## Relationship to `/goal` and `/loop` (WS7 boundary — NOT built here)

A `/goal`- or `/loop`-driven session carries a session-scoped **Stop hook** that historically _pushed the session to keep grinding inline_ rather than dispatch-and-checkpoint. WS4 removes that push **from the `/pull` surface**: `/pull` now offers no inline-execution path for the hook to drive the session into — its only completion is a dispatch (or a clean "nothing to dispatch" stop).

WS4 does **not** build the termination mechanism. The **legal-exit path** — how a `/goal` or `/loop` session is _permitted to terminate_ without the Stop hook forcing another empty inline retry — is **WS7's deliverable (gate composition & exit semantics)**. The named boundary: _until WS7 lands, a `/pull` that finds nothing to dispatch (or has done its one dispatch) stops; if the `/goal`/`/loop` Stop hook re-fires it into another turn, that re-fire is the WS7 deadlock to fix in WS7 — `/pull` will not paper over it by manufacturing inline work._ This mirrors the WS7 boundary the program loop already names for its done-pending-Nic terminal state (see `skills/program/SKILL.md` → Terminal states → WS7 boundary).

## Arguments

- `/pull` — select the highest-`focus_score` queued task and dispatch it to the right surface.
- `/pull <task-id>` — dispatch a specific task (or its first queued leaf if it has children).

## Implementation Note

`/pull` owns exactly one decision: _which queued task to dispatch, and to which surface._ How that surface then executes, verifies, commits, and ships — those are the surface's responsibilities, never `/pull`'s. `/pull` is queue-advancement-by-dispatch, full stop.
