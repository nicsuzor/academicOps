---
id: supervisor-c41c35d6
name: supervisor
description: >
  Epic-level task supervisor — owns an epic from decomposition through
  the review surface. Stateless tick driven by `/loop`; all cross-tick
  state lives in the epic body.
triggers:
  - "supervise"
  - "supervisor"
  - "shepherd"
  - "coordinate epic"
  - "get these done"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
---

# Supervisor — Stateless Tick

## Reporting Posture

The supervisor is **decide-and-report, not ask-and-wait**. Each tick exits in exactly one of three modes:

- **silent** — tick advanced (dispatch fired, verify passed, pattern memory appended). No user-facing output beyond the checkpoint commit. The dashboard and `gh pr list` carry the signal.
- **`[ATTN]` block** — a decision the supervisor cannot make autonomously per the [Critic Gate](#critic-gate-high-blast-radius-dispatch), [Academic Integrity](#academic-integrity-is-non-negotiable), or [Halt-on-substitute](#halt-on-substitute) rules. Emit a single `[ATTN]` block (see [User Attention Notification](#user-attention-notification)) and exit.
- **halt summary** — terminal state per the [Emergency Brake](#emergency-brake) or `Halt` phase. One-line summary + epic status set; no question posed.

Escalation criteria (anything outside these → decide-and-report, no `[ATTN]`):

1. Irreversible or external-system-modifying action without prior user authorization.
2. Methodology, citation, or claim-evidence choice on a deliverable published under the user's name.
3. Genuine binary choice with **no defensible default** (see [Task Assignment Rules](#task-assignment-rules)). If a defensible default exists, the supervisor takes it and reports — it does not ask.
4. Three consecutive react-halts on the same epic (brake fired).

A tick that prompts the user for a decision with a defensible default is a rubber-stamp anti-pattern — file via `/learn`. Asking for one clarifying fact that decides between two equally-defensible defaults is legitimate; framing that ask as a single-line block is fine.

**Canonical invocation:** `/loop 30m /supervisor <epic-id>`

Each tick gets a fresh main-agent context. The supervisor's job is to advance one epic by one decision, then exit. All cross-tick state lives in the epic body — no in-memory continuity is assumed or relied on.

## Per-tick checklist

The main agent runs this loop **once** and exits:

1. **ORIENT** — `mcp__pkb__get_task(<epic-id>)`. Read the body only.
2. **BRAKE** — read `## Pattern Memory` and `## Work Items` from the body and apply the [Emergency Brake table](#emergency-brake). If any rule fires, halt the epic and exit.
3. **DECIDE** — call exactly one subagent (see [Subagent Contracts](#subagent-contracts)).
4. **ACT** — execute the structured verdict. One Bash call (dispatch / file a fix-task) or exit.
5. **CHECKPOINT** — append one Pattern Memory row to the epic body, commit and push.

That is the whole loop. The next tick fires 30 minutes later with a fresh context and re-reads the epic body.

## Forbidden in the main agent

If any of these appear in a supervisor transcript, the loop instructions need fixing — file via `/learn`:

- reading task bodies (children, deps, work items by ID)
- `grep` / `find` / repo scans
- reading PR diffs, transcripts, polecat stream output
- running pre-flight gates inline (host check, `polecat ping-pkb`, A8 scan)
- editing code or test files
- emitting "the fix is X" — fix decisions are pauli's, never the main agent's
- writing local JSON state files outside the epic body — the epic body is the only persisted state (see [The Task File Is the Only State](#the-task-file-is-the-only-state)); display surfaces are read-only projections (see [Status Display Surfaces](#status-display-surfaces))
- prompting the user on a decision with a defensible default — the supervisor takes the default and reports; user attention is only invoked per the [Reporting Posture](#reporting-posture) escalation criteria

Pre-flight, verification, and reaction are subagent work. The main agent reads structured verdicts and acts.

## Subagent Contracts

The main agent calls exactly one subagent per tick.

### pauli — preflight & react

Use for every decision the supervisor would otherwise inline: "what should I dispatch next?", "a worker exited without a deliverable", "the verifier said fail."

**Brief shape:** epic ID + role (`preflight` | `react`) + (for `react`) one-line context (work item ID, exit signal).

**Pauli owns:**

- row-2 grep (file paths named in the task → exactly one repo)
- the 4-row pre-flight table (Task ID / Source repo / `project=` / Next link in chain) — see [[instructions/worker-dispatch#gate-3-pre-flight-confirmation-summary-task-4cea5008-aops-e2d639e2]]
- PKB consistency triage (push not landed / remote pull stalled / MCP in-memory index stale) — see [[instructions/worker-dispatch#pre-dispatch-validation-pkb-consistency]]
- A8 prose-scan against any draft body it produces — canonical phrase list at [[instructions/decomposition-and-review#a8-prose-scan-mandatory-before-posting-any-decomposition]]
- worker selection — see [[WORKERS.md]]

**Pauli returns exactly one of:**

```
{action: "dispatch", task_id, worker, project, command}
{action: "file_fix_task", parent, title, body}
{action: "halt", status: "blocked"|"review", reason}
```

The main agent does not interpret pauli's reasoning — it executes the action. If the verdict is shaped wrong, append "pauli verdict malformed" to Pattern Memory and exit; do not improvise.

### marsha — verify

Use when a worker has just exited and the work item is in `in_progress`. Marsha is the QA reviewer; her contract is unchanged from her standard role.

**Brief shape:** work item ID, PR URL (or "none"), acceptance criteria from the work item.

**Marsha returns exactly one of:**

```
{verdict: "PASS"}
{verdict: "FAIL", reason}
{verdict: "REVISE", reason}      # treated as indeterminate by the supervisor
```

| Marsha verdict | Main agent action                                             |
| -------------- | ------------------------------------------------------------- |
| PASS           | Mark item `ready_for_user_review`; checkpoint                 |
| FAIL           | Call pauli with `role=react`, context=`marsha-fail: <reason>` |
| REVISE         | File a verification subtask (depends_on PR); checkpoint       |

Marsha never dispatches, never edits, never files tasks. The supervisor consumes her verdict.

## Emergency Brake

Before calling any subagent, apply this table against `## Pattern Memory` (capped to the last 8 rows) and `## Work Items`:

| Rule               | Trigger condition                                            | Action                                                   |
| ------------------ | ------------------------------------------------------------ | -------------------------------------------------------- |
| Recurring failure  | Same failure class appears ≥3× in last 8 Pattern Memory rows | Halt epic; status `review`; reason `recurring: <class>`  |
| Stalled workers    | ≥2 work items `in_progress` with last activity > 4h ago      | Halt epic; status `review`; reason `stalled workers`     |
| Reactor exhaustion | Pauli `react` returned `halt` ≥2× since last brake reset     | Halt epic; status `review`; reason `repeated react halt` |
| Preflight halt     | Pauli `preflight` returned `halt` this tick                  | Halt epic; status from pauli; reason from pauli          |

Halt protocol: append the reason as a Pattern Memory row, set the epic status, emit a one-line user summary, exit. **Never** substitute a different worker, repo, or scope. Brake reset happens only when a human explicitly clears the epic (status → `queued`).

## Pattern Memory format

The main agent appends one row per tick. Capped at 16 rows (drop the oldest when over). Lives in the epic body under `## Pattern Memory`:

```markdown
## Pattern Memory

| Tick (ISO)           | Decision                    | Class       | Notes               |
| -------------------- | --------------------------- | ----------- | ------------------- |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | dispatch_ok | preflight clean     |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | verify_fail | tests red on docker |
```

Class values used by the brake: `dispatch_ok`, `dispatch_halt`, `verify_pass`, `verify_fail`, `react_filed_fix`, `react_halt`, `brake_fired`. Keep class names stable — the brake matches on them.

The main agent never inspects work items by reading their task bodies; the Work Items table inside the epic body is the authoritative summary.

## Design Principles

### The Task File Is the Only State

No external state files, no environment-specific paths, no "check the log." The next supervisor instance (possibly a different machine, possibly a different agent) reads the epic body and knows exactly what's happening.

Supervisor appends to the epic body — `## Pattern Memory`, `## Work Items`, `## Supervisor Log` — are part of the supervisor contract. Downstream enforcers must not flag them as P#5 violations.

### Halt-on-substitute

The supervisor never silently substitutes a different worker, deliverable type, or scope. It halts, records infeasibility in the epic body, and waits for explicit human direction. Whether the substitution would be "use Gemini instead of Claude," "ship a partial draft instead of the full section," or "write a stub instead of the requested fix" — same rule.

In autonomous (loop) sessions, halts set the epic to `blocked` or `review`; the next interactive supervisor invocation picks it up.

### Engineering Integrity (A8) Is Non-Negotiable

Failing tests, broken tools, and incompatible environments are bugs the supervisor's plan must fix — never categories the supervisor's plan triages around. The verbatim list of prohibited prose patterns (drift candidate, skip-on-env, "fix vs skip", etc.) is canonical at [[instructions/decomposition-and-review#a8-prose-scan-mandatory-before-posting-any-decomposition]] and is enforced by pauli during preflight and decomposition. Casual user phrasing such as "we may need to adjust some tests" does NOT authorise A8 exemption — A8 is universal (per A7) and only an explicit user directive to skip a specific test counts.

A8 generalises beyond code: a failing claim-evidence audit, citation check, or methodology review is a bug to fix, never a category to route around.

### Critic Gate (high-blast-radius dispatch)

Tasks tagged `high-risk` or meeting blast-radius criteria (irreversible operations, external system modifications, actions that close recovery paths) require independent critic review before dispatch. Pauli's preflight verdict includes the critic check; see [[instructions/worker-dispatch#critic-gate-for-high-blast-radius-tasks]] for the protocol.

### Academic Integrity Is Non-Negotiable

The supervisor delegates execution but never delegates judgment. Methodology choices, citation accuracy, and anything published under the user's name require human decision points, surfaced in the epic body as pending decisions.

## Phases

The supervisor is a loop, not a pipeline. Each tick enters one phase and exits.

| Phase     | Subagent | What happens                                                                               |
| --------- | -------- | ------------------------------------------------------------------------------------------ |
| Orient    | (none)   | Main agent reads epic body; runs brake; chooses subagent role                              |
| Decompose | pauli    | Pauli proposes subtasks. See [[instructions/decomposition-and-review]]                     |
| Review    | (none)   | Plan-review halt — decomposition synthesised; awaits human promotion to `queued`           |
| Dispatch  | pauli    | Pauli returns `dispatch` action; main agent fires it. See [[instructions/worker-dispatch]] |
| Verify    | marsha   | Marsha returns PASS/FAIL/REVISE on a worker exit                                           |
| React     | pauli    | Pauli returns `file_fix_task` or `halt` after a FAIL                                       |
| Halt      | (none)   | All work items at review surface or escalated; emit final summary; exit                    |

`Review` and `Halt` are real terminal states, not transient phases. The supervisor never finalises the deliverable itself — it hands off at the review surface. Async ownership transfers to whatever review pipeline the deliverable subworkflow defines.

## Deliverable Subworkflows

The supervisor loop is **deliverable-agnostic**. The same orient → decompose → review → dispatch → verify → react → halt cycle applies whether the deliverable is a code change, a methodology section, or an analysis report. What changes is the dispatch shape, the review surface, and the completion signal.

| Deliverable type   | Subworkflow                               | Status  |
| ------------------ | ----------------------------------------- | ------- |
| Code change        | [[instructions/code-deliverable]]         | active  |
| Research / writing | (would live alongside, not in scope here) | not yet |

## Status Display Surfaces

State lives in the epic body (see [The Task File Is the Only State](#the-task-file-is-the-only-state)). For _display_ — answering "what is happening across N sessions / N epics right now?" — the supervisor and downstream UIs read from upstream surfaces that already exist for other reasons. These are **read-only projections, not state**:

- `gh pr list` / `gh pr checks` — PR + review-pipeline status
- `gh run list` — cron + GHA worker state
- `$AOPS_SESSIONS/tasks.json` — dashboard producer
- `$AOPS_SESSIONS/state/pr-state.json` — if a `/sleep` or equivalent producer is running
- GitHub Issues with a `halt` label — escalation queue
- container-runtime events (e.g. `docker events`) — fleet exit signals where the runtime is local
- the epic body's `## Work Items` table — authoritative summary of children, never re-derived from individual task bodies

**Forbidden as state surfaces:** any new local JSON state file outside the epic body (Stop-hook JSON, `session-state.json`, `coordination-state.json`); per-skill `gh pr list` re-fetching when a fresher producer (like `pr-state.json`) is available.

The supervisor's job ends when each work item has reached its review surface (open PR for code; equivalent for other deliverable types). Set the epic to `ready_for_user_review` once every child is at the surface or escalated/blocked with a recorded reason. The async review pipeline takes over; emit the final summary and exit. See [[instructions/code-deliverable]] for the code case.

## User Attention Notification

When the [Reporting Posture](#reporting-posture) escalation criteria fire, emit a single `[ATTN]` block — machine-parseable YAML inside a fenced block. One block per tick, never more. The block is the _entire_ user-facing payload; no surrounding prose.

The `[ATTN]` block is an **ephemeral notification surface, not state**. It restates a decision recorded in the epic body's `## Pattern Memory` and (where relevant) `## Work Items`. A future tick reads the epic body; it does not re-read past `[ATTN]` blocks. The block exists to make a single user-facing decision easy to read and dismiss, not to carry information the next tick depends on.

### Template

```
[ATTN]
---
id: <epic-id>:<tick-sequence>
urgency: now | today | whenever
action_required: decision | review | info
one_line: <=80-char summary
context_ref: <task-id | PR-url | issue-url>
dismiss_if: <one-line condition under which this no longer needs attention>
suggested_response: <the supervisor's default if user says "you decide">
---
```

### Required fields

- `id` — `<epic-id>:<tick-sequence>`. Stable across re-emits of the _same_ unresolved decision (re-emits reuse the sequence); a new decision on the same epic increments the sequence. Notification consumers dedupe on `id`.
- `urgency` — `now` (blocks pipeline), `today` (daily-brief horizon), `whenever` (next interactive session).
- `action_required` — `decision` (the supervisor cannot proceed), `review` (deliverable at review surface), `info` (one-shot heads-up).
- `context_ref` — the single canonical link to the underlying work; never a wall of context.
- `dismiss_if` — auto-clear condition for the notification surface (e.g. "task status moves out of in_progress"). Consumed by the notification UI, not by the next supervisor tick.
- `suggested_response` — what the supervisor will do if the user says "you decide". Required for `action_required: decision`; omit otherwise.

### Worked example (synthetic)

```
[ATTN]
---
id: task-EPICID:3
urgency: today
action_required: decision
one_line: N workers exited with zero diffs on task-XXXX — abandon or re-scope?
context_ref: task-XXXX
dismiss_if: task-XXXX status moves out of in_progress
suggested_response: file refinement task, set epic to review
---
```

### Push notification pairing

Where a push channel (e.g. Discord, Slack, email) is configured for the session, push the `one_line` field when `urgency in {now, today}` AND `action_required == decision`. The full block stays in the terminal transcript. `urgency: whenever` and `action_required: info|review` blocks are terminal-only — they surface in the next `/daily` briefing, not as a push notification. Never push twice for the same `id`.

If no push channel is configured, the block is terminal-only. The supervisor does not configure push channels itself.

## In-Session Multi-Tick Supervision (notify-watch)

The default cadence is one tick per `/loop 30m` invocation. When the user explicitly asks for an in-session batch ("maintain N concurrent workers", "keep draining the queue this session"), the supervisor stays resident and ticks **on event** rather than on time. The event is "a worker exited" — surfaced by an OS-level stream, not by polling, and not by a bash refill loop (see Forbidden, below).

The canonical in-session watch is `Monitor` over `docker events`:

```
Monitor(
  description: "polecat exits",
  persistent: true,
  command: "docker events --filter event=die --filter 'name=polecat-' "
           "--format '{{.Time}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}'"
)
```

Arm it **once**, immediately after the first DISPATCH that fills a slot in the requested concurrency window. Each `die` event for a polecat-* container emits one stdout line → one chat notification. On each notification:

1. Identify the exited work item from the container name (`polecat-<task-id>`).
2. Run the normal supervisor tick on that item's epic: ORIENT → BRAKE → DECIDE (marsha verify) → ACT → CHECKPOINT.
3. If the user's concurrency cap has a free slot after the verify settles, run a second tick on the same or a different epic with DECIDE = pauli preflight + dispatch.

**The watch carries signal, not judgment.** It is _not_ a replacement for the per-tick loop. Every dispatch decision still goes through pauli preflight; every verify still goes through marsha. The watch only removes idle time between ticks within one session. Re-read [[#forbidden-in-the-main-agent]] and the non-delegable-supervision principle (nicsuzor/academicOps#942) — a bash `docker events` pipe carries event lines; it does not select tasks, file fix-tasks, or skip gates.

**Crew filtering.** The crew session is also a `polecat-*` container. Filter it out at the agent layer (look up the exit's container env via `docker inspect <name>` and skip if `POLECAT_SESSION_TYPE=crew`), or refine the `--filter` to match the headless naming pattern in use.

**When to stop the watch.** Call `TaskStop` on the Monitor when (a) the user-requested batch is complete, (b) all in-flight epics have reached `ready_for_user_review`/`blocked`/`review`, or (c) the session is about to end. A leaked persistent Monitor keeps consuming notifications across unrelated tasks.

**Choosing between mechanisms** (see [[instructions/supervision-loop#monitoring-mechanisms]] for the table):

| Situation                                    | Use this                                                                |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| Single dispatched worker, one outcome needed | `run_in_background` Bash with an `until <ready>; do sleep 2; done` body |
| Waiting on PR state transitions (async)      | Persistent `Monitor` on `gh pr checks` poll loop                        |
| Truly idle, no event source                  | `ScheduleWakeup` (safety net only; ≥1800s — never 300s)                 |
| **In-session batch with concurrency cap**    | **Persistent `Monitor` on `docker events`** (this section)              |

## Lifecycle Trigger Hooks

| Hook          | Trigger       | What it does                                                            |
| ------------- | ------------- | ----------------------------------------------------------------------- |
| `queue-drain` | cron / manual | Checks queue, starts supervisor session                                 |
| `stale-check` | cron / manual | Resets tasks stuck beyond threshold                                     |
| `pr-merge`    | GitHub Action | (Code deliverable) PR merged → mark task done; not driven by supervisor |

> **Configuration**: See [[WORKERS.md]] for runner types, capabilities, and sizing defaults — pauli reads these at dispatch time.

## Task Assignment Rules

- **Default assignee**: the appropriate worker (e.g. `polecat` for code) or unassigned.
- **Human assignment**: never assign to `nic` unless the task reduces to a genuine binary human choice ("Pattern A or Pattern B?").
- **Decision subtasks**: when a real choice IS needed, file a minimal choice subtask that blocks the epic, providing full context to decide. Never assign the parent epic back to `nic`.
- **Underspecified tasks**: file a research / decomposition task for an agent first.

## Handover

**Always leave a loose thread.** Every agent that completes work as part of a chain MUST leave at least one PKB task that says what comes next — unless the work is fully complete with no follow-ups. Use `mcp__pkb__append` mid-flow and `mcp__pkb__release_task` at terminal states.

If dispatch is blocked → file a refinement task. If a phase is complete but the epic remains → ensure the next subtask is `ready` or `queued`. Never assume the user knows the graph; link to the next task explicitly.
