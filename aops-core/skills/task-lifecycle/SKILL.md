---
name: task-lifecycle
description: >
  The shared queue-to-execution spine for claiming work. Selects the next queued
  task, runs the premise + freshness gates, then either DISPATCHES it to a
  background surface (`/dispatch`) or CLAIMS and runs it INLINE in the current
  interactive session (`/pull`). Owns the select/gate/claim/verify/complete
  lifecycle so the two commands stay thin and never duplicate it. Invoked with a
  leading mode token: `dispatch: …` or `execute: …`.
triggers:
  - "task-lifecycle"
  - "claim a task"
  - "run the next task"
  - "dispatch the next task"
modifies_files: true
needs_task: false
mode: dispatch
domain:
  - operations
---

# task-lifecycle — Claim → (Dispatch | Execute) → Verify → Complete

This skill is the **single source of truth** for advancing one task from the
`queued` set into work. Two commands consume it; the only difference between them
is the tail (where the work runs):

- **`/dispatch`** → `Skill(task-lifecycle, "dispatch: …")` — route the selected
  task to a background execution surface, then halt. Never executes inline.
- **`/pull`** → `Skill(task-lifecycle, "execute: …")` — claim the selected task
  and run it **inline** in this interactive session, asking the user questions
  when needed, then verify and complete.

Everything up to the mode split — **Select** and **Gates** — is identical for
both. Author it once here; do not re-inline it in the command files.

## Invocation & Arguments

The first token of `args` is the **mode** (`dispatch` or `execute`), optionally
followed by a task id:

- `dispatch:` / `execute:` — select the highest focus-score queued task.
- `dispatch: <task-id>` / `execute: <task-id>` — select the specified task (or
  its first queued leaf).

If no mode token is present, default to `dispatch` (the safe, context-cheap path).

---

## 1. Select the Task (both modes)

- Search for task nodes with `status: "queued"`.
- If no task id is given, list the top candidates via
  `mcp__plugin_aops-core_pkb__list_tasks(status="queued")` and pick the one with
  the highest `focus_score`.
- Descend to leaf tasks if the selected task has children.

## 2. Gates (both modes — run before spending any compute)

These gates bind **every** path that pulls a task out of the `queued` set —
`/pull`, `/dispatch`, and the dispatch step of `/supervisor`. The whole point is
to refuse a bad task _before_ compute is spent, whether that compute is an
inline run or a dispatched worker.

### 2a. Premise gate (hard refuse — two-judge clearance)

Apply the **premise gate** to the selected candidate leaf task: (1) ensure the
task carries a legible, real premise sentence — record one from the task's intent
if a hand-queued task left none, or bounce if it is too vague to state; (2) clear
it through `/strategic-review <task>`, which runs `rbg` (axiom/rig) and
`pauli` (worth/shape) as judges. Any BOUNCE → hard-refuse, do not spend compute,
bounce the task back to the promoter. This is the last spend-stopper before either
mode acts on the task.

The full procedure — ensuring the premise is legible, why the judgment is deployed
to two agents and **never** reduced to a regex/field/heading presence-check
(`judgment-non-delegable`), and the exact bounce-back mechanics — is owned by
[[../remember/references/premise-gate.md]] §2. Follow it there; do not restate it
here.

### 2b. Freshness pre-check

For the selected candidate leaf task:

- **Path Resolution Check**: Read the task body and title and identify the paths
  the brief is actually asking you to act on, distinguishing them from paths
  merely mentioned in passing or as examples. Then, only if the task names a
  `project`/repo you have checked out in this session, verify each identified
  path resolves there (`Read`/`ls`); if no relevant checkout is available, skip
  this check rather than warn on a path you cannot verify.
  - If a verified path does not resolve, print a warning naming the stale
    reference: `[WARNING] Task brief references non-existent path: <stale-path>`
    (warn, do not hard-block — the caller decides).

- **Stale-leftover check**: A superseded or dropped task is not selectable
  because it is already out of the dispatchable set — supersession or a drop
  decision moves the task to a terminal status (`done` / `cancelled`), so the
  `queued`-only selection in §1 never surfaces it. No separate field check is
  needed here. What the select step *cannot* see is a leftover from a completed
  decomposition:
  - If the task has a parent, retrieve the parent's children (siblings) via
    `mcp__plugin_aops-core_pkb__get_task_children`. If **all** siblings are
    already `done` (a heuristic, not proof — parallel siblings legitimately
    finish at different times), the task may be a leftover from a completed
    decomposition. Print `[WARNING] Task <id>'s siblings are all done — may be a
    stale leftover` and flag it rather than proceeding silently; do not auto-skip
    on this signal alone.

---

## 3a. Mode: `dispatch` — route to a background surface, then halt

Performs exactly one dispatch step and exits. **Do not execute the task inline.**

- **Specialist Subagent**: If the task or parent has an assignee matching a known
  specialist (`marsha`, `rbg`, `pauli`, `james`, `ida`, `qa`, `rbg`,
  `polecat`), dispatch using `subagent_type="[name]"`.
- **Polecat**: For repo-scoped, PR-shippable code/docs/tests without a named
  specialist, dispatch to a polecat.
- **Subagent**: For research or synthesis requiring findings returned to the
  current session, dispatch using the `Task` tool.
- **Defer**: If the task lacks necessary inputs, is blocked, or needs manual
  scoping, update the task with a block note and exit without dispatching.

Record and exit:

- Do not mark the task as `in_progress` from this session — the executing surface
  claims it.
- If using a subagent that does not self-claim, update the task `assignee` and
  add a dispatch note via `mcp__plugin_aops-core_pkb__update_task`.
- The task ID propagates to the execution surface via the `$AOPS_TASK_ID`
  environment variable and the git branch name; do not synthesise a filesystem
  binding file.
- **Halt after dispatching.**

For the full dispatch contract (pre-flight summary, compose-then-dispatch
separation, surface templates) see
[[../supervisor/references/dispatch-rules.md]] and
[[../supervisor/instructions/worker-dispatch.md]].

## 3b. Mode: `execute` — claim and run inline (interactive)

Run the task **in this session**. Because this is interactive, you have explicit
licence to **ask the user questions** (`AskUserQuestion`) whenever a decision is
genuinely the user's to make — scope, ambiguous acceptance criteria, or a
hard-to-reverse step. Do not dispatch to a background worker.

1. **Claim.** Set `status: in_progress` and `assignee` to yourself via
   `mcp__plugin_aops-core_pkb__update_task`. (On the Cowork surface this claim
   step also drives the native-list mirror — see [[../cowork-sync/SKILL.md]].)
2. **Confirm the working context.** Verify the current working directory / repo
   matches the task scope before editing. On mismatch, switch context explicitly
   (note it on the task) or return the task to the queue with a context note
   rather than working in the wrong tree.
3. **Execute.** Do the work directly. Hold to the proof discipline: a change is
   not done until a runtime observation confirms the intended user-facing
   behaviour — "tests pass" is not the acceptance gate for a behaviour change.
   Ask the user when blocked on a decision only they can make.
4. **Verify.** Run the task's acceptance check (or the sanctioned harness if one
   is designated). State the observable that had to be true and confirm it.
5. **Complete.** Record the outcome on the task and move it to its terminal
   status (`done`, or `merge_ready` / `review` if it ships through a PR). Capture
   any follow-ups as new tasks. For a clean session close use [[../end_session/SKILL.md]].

---

## Relationship to `/pull`, `/dispatch`, and `/supervisor`

All three verbs run on this one spine — **Select → Gates → (Dispatch | Execute)**
— which lives here and is authored once:

- **`/pull`** runs the spine in `execute` mode (claim + run inline).
- **`/dispatch`** runs the spine in `dispatch` mode (route to a surface, halt).
- **`/supervisor`** is the multi-tick **delegate-and-verify** process. Its
  Dispatch phase **invokes this skill's `dispatch` mode** for the select + gate +
  route step rather than re-implementing it — then layers on top the discipline
  that is genuinely its own and has no meaning here: the pauli pre-flight
  confirmation summary and critic gate ([[../supervisor/instructions/worker-dispatch.md]]),
  proof, the ledger, evaluation, and escalation **across ticks**.

The rule is one-way: this skill knows nothing about ticks or ledgers; the
supervisor knows this skill owns Select + Gates + routing and does not restate
them.
