---
name: learn
description: Turn something that went wrong into a lesson that lands somewhere useful. Diagnoses the incident back to the structural cause that invited it, then routes the lesson to the one destination its scope actually claims — task record, project rule, PKB, framework source, or a tracked issue. Use on "/learn", "that last task should have been xyz", "review what went wrong in that session", or a session retro. Not for live debugging — a failing test or a bad diff in the work at hand wants a direct answer, not an incident review.
agent: "pkb:pauli"
---

# Learn

Two moves, in order, both required: **diagnose**, then **route**. A diagnosis
nobody can act on is wasted, and a lesson filed to the wrong surface does damage
that outlasts the incident.

## 1. Identify the record

Diagnose the record you were pointed at, never one you went looking for.

- Given a description of what went wrong — "that last task should have been
  xyz" — the record is the current session, and the description is directive
  context: it tells you what the correct behaviour was.
- Given a session id or transcript path, resolve it under
  `$AOPS_SESSIONS/transcripts/YYYY-MM/` and read the markdown. Never fall back to
  the raw `.jsonl`, and never substitute a different session because the named one
  is unreadable — name the failed condition and stop.
- Given neither, ask which incident. Do not pick one.

Review the current session without seeking permission: this skill runs as a fresh
reviewer in a detached context, which is the boundary that makes self-review
honest.

## 2. Diagnose

@include doctrine/forensic-scope.md

## 3. Route

@include doctrine/lesson-routing.md

### The gate on universal-scope destinations

@include doctrine/universal-gate.md

## Writing to each destination

- **Task record** — write the preference into the task's body as current state,
  in the section it belongs to. Not a dated entry, not a log.
- **Project rule** — invoke the `add-rule` skill. Do not write
  `.agents/rules/RULES.md` yourself; that skill owns the file's shape and checks
  the frontmatter the in-session rule check depends on.
- **PKB** — invoke the `remember` skill. It searches first, augments the
  canonical note rather than creating a second one, and integrates the lesson
  into what is already there.
- **Framework source** (gated) — you are not fixing this now. Record the gap
  precisely enough that the deliberate cross-incident pass can act on it: which
  instruction, which agent, what it currently says, what the incident showed.
- **Tracked issue** (gated) — search open issues first and comment on the match
  rather than opening a duplicate. Forensic fields only: incident facts,
  structural shape, impact.

## Report

Name the diagnosis in one sentence, the scope you assigned, the destination, and
the id or path of what was written. If the scope was ambiguous, or a destination
was gated out, say that instead of picking something.

## Must not

- Route to more than one destination to be safe. One lesson, one home.
- Change what a shipped agent is directed to do because the incident made it
  obvious. That is the gated destination, and this pass does not have it.
- Write a lesson to a surface whose scope it does not claim because the right
  surface was closed.
