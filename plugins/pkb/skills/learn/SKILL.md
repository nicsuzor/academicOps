---
name: learn
description: Turn something that went wrong into a lesson that lands somewhere useful. Diagnoses the incident back to the structural cause that invited it, then routes the lesson to the one destination its scope actually claims — task record, project rule, PKB, framework source, or a tracked issue. Use on "/learn", "that last task should have been xyz", "review what went wrong in that session", or a session retro. Not for live debugging — a failing test or a bad diff in the work at hand wants a direct answer, not an incident review.
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

A lesson is diagnosed forensically: read the record, name the structural cause
that invited the failure, and stop there. The symptom is where you start, never
where you finish. Look for structural causes, architectural misfit, patterns that
recur across the record, and instruction-quality defects — compliance framing, a
missing artifact chain, an instruction that reads as advice.

**Diagnosis fixes the session under review. It never changes what future sessions
are directed to do.**

- **In scope, fix immediately**: the concrete mistake or leftover bad state _this
  session_ produced — a wrong file it wrote, a task it left mis-filed, a broken
  reference or typo it introduced or tripped over, an actual code bug in a hook,
  a gate, or a script bundled with a skill or tool. Fix these directly in the
  source, without seeking permission.
- **Out of scope, always**: adding, editing, or strengthening any rule — project
  rules included — or any axiom, persona instruction, gate, hook, or
  agent-definition text so that _future_ sessions behave differently — even one
  line, even when you are confident it is correct and well-scoped. That is a
  framework change, not a fix to the session under review. One incident is never
  sufficient warrant for it, however salient. Name the gap precisely and route
  it; do not close it.

A skill's own instruction text is not code. Fixing a bug in a script a skill
bundles is in scope; editing that skill's `SKILL.md` prose changes what future
sessions are directed to do, and is not.

**Diagnosis never decides where a lesson may be written.** Whether any standing
surface — a project rules file included — may be written at all, and under what
warrant, is a routing decision governed separately and reached after diagnosis
ends. Read the prohibition above as binding on this step, not as a veto on the
routing step that follows it.

**Framework and behavioural changes are never a diagnosis fix.** A change to what
an agent is directed to do — an instruction, persona edit, axiom, rule, hook,
gate, or chokepoint — is a framework change, at any tier, no matter how minor,
obviously correct, or narrowly scoped to the one incident it looks from inside
the review. Recurrence across multiple recorded findings, not the salience of one
record, is the evidence base for a framework change; deciding on one, including
which mechanism carries it, is a separate deliberate pass.

**"That last task should have been xyz"** — an instruction naming what should
have happened — is a directive to do **both** of these, never to pick one:

1. Fix the immediate problem now, per the in-scope/out-of-scope split above —
   the session's own mistake or leftover state, never the instructions governing
   future sessions.
2. Diagnose and route the lesson, carrying the "should have been xyz" framing as
   directive context.

Never substitute a framework change for either.

**Fix and route.** An immediate fix never replaces routing the lesson. The
systemic lesson must survive even when the local symptom is already patched.

**A recorded finding carries forensic facts only** — what failed, how the
framework contributed, concrete impact. No speculative remediation in the record
itself; that keeps it clean as evidence for the cross-incident pass that does
decide. This is a rule about what the _record_ contains. It is not a prohibition
on fixing the reviewed session's own mistakes, nor, in the other direction,
licence to change the framework's future behaviour.

**If an in-scope fix is too large, or needs permissions or runtime you do not
have**, route a follow-up rather than landing a partial fix that degrades
reliability.

**Anonymise.** No real names, emails, student details, or raw session dumps in
anything you write — the record, the fix, or the report.

## 3. Route

@include doctrine/lesson-routing.md

### The gate on universal-scope destinations

Framework source and the framework's issue tracker are writable only from inside
the framework's own source tree. Test it: the tree has both `lib/axioms/` and
`build/marketplace.toml`. If either is missing, you are in a consuming project and
those two destinations are closed to you.

**When gated out, degrade — never drop, and never redirect to a surface you have
no standing to write.** Record the lesson as a tracked improvement task tagged
`framework-gap`, carrying the diagnosis, the evidence, and the destination it was
headed for. Raise it as an issue on the framework repository only when the user
asks. A lesson written to the wrong destination because the right one was closed
is worse than one parked where someone can find it.

## Writing to each destination

- **Task record** — fold the preference into the task's checklist or pointers,
  in the section it belongs to, as one line. Not a dated entry, not a log.
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
  rather than opening a duplicate.

## Report

Name the diagnosis in one sentence, the scope you assigned, the destination, and
the id or path of what was written. If the scope was ambiguous, or a destination
was gated out, say that instead of picking something.
