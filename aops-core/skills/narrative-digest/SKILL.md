---
name: narrative-digest
type: skill
category: instruction
description: >
  Launder supervisor/worker task-log output into a Nic-facing narrative — what
  happened, where things are headed, and what (if anything) is genuinely his
  to decide. Never relays raw process detail (worker IDs, thread pointers, log
  paths) or verbatim task-log stream-of-consciousness.
triggers:
  - "what happened"
  - "give me the status"
  - "digest"
  - "summarize the epic"
  - "narrative summary"
modifies_files: false
needs_task: false
mode: instruction
domain:
  - operations
permalink: skills/narrative-digest
---

# Narrative Digest

Turn supervisor/worker task-log detail — dispatch records, review verdicts,
evidence bundles, escalations — into a short, accurate narrative for Nic. This
is the mechanism behind the head's Supervision Boundary obligation (P4/P5,
`head-role-charter.md`): the head does not run day-to-day dispatch, but it
must still report on what the supervisor produced, in a form Nic can read in
seconds, not a form he has to decode.

## Input

Whatever the supervisor/worker layer already emits and the head can read
without running its own investigation:

- Task/epic records and their status transitions (PKB `get_task`,
  `get_task_children`, `list_tasks`).
- Four/five-agent review verdicts and evidence bundles attached to a task.
- Supervisor escalations surfaced mid-epic (a blocker raised before the
  epic's terminal condition).
- Release summaries and handover/reflection blocks left by workers.

Never the raw dispatch/execution transcript itself — if only a raw log is
available, that is a signal the supervisor's output contract is incomplete,
not something to paraphrase line-by-line.

## Output

A digest fit for the charter's Fitness Criteria (response density, PKB as the
only persistence surface for anything durable, outcomes-not-threads). Three
parts, in order, each omitted if it would be empty rather than rendered as a
stale/empty placeholder:

1. **What happened** — one status line, then bullets per epic/task that
   changed state since the last digest. Outcomes only: "PR filed," "epic
   blocked on X," "task done" — never worker IDs, PIDs, thread pointers, or
   log paths (see the charter's Anti-Patterns list — this skill exists
   specifically to prevent that leak).
2. **Where things are headed** — the next terminal condition each open
   epic/task is working toward, in plain language, not a queue dump.
3. **What's actually Nic's** — at most one named decision, with pre-resolved
   options, if the supervisor raised a genuine blocker or an epic reached its
   terminal condition and needs the Ambition/Intent Check (see the charter).
   If nothing needs Nic, say so in one line rather than manufacturing an
   escalation to fill the section.

## Anti-patterns

- Reproducing a task-log stream-of-consciousness instead of synthesising it.
- Naming worker/session IDs, thread pointers, or file paths as if they were
  meaningful to Nic.
- Turning a routine status update into an escalation because the digest
  "needs" a decision section.
- Rendering a full stale/empty table when a data fetch or lookup came back
  empty — collapse to a one-line note instead (charter: Static Artifacts).
