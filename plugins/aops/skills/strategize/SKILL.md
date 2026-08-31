---
name: strategize
description: The thinking pass for "plan this", "what should I do next", and "where does this work go" — fix the altitude, test the plan against the effectual commitments, and route each piece to the stage that owns it.
---

# Strategize

Planning here is **effectual, not causal**. A causal plan starts from a desired
end state and works backwards to the resources it would need. An effectual plan
starts from the means actually in hand — what is known, who is available, what is
already built — and asks what can be made with them. Under real uncertainty the
second one survives contact and the first one does not.

This is a lens, not a stage. Nothing waits on it and nothing downstream assumes
it ran. Reach for it when a plan needs checking, an ask needs a home, or the
user asks what to do next.

## You think; pauli reads and writes

You hold no PKB tools. That is deliberate, and it shapes how this runs: **every
look at the graph is a question you commission from `aops:pauli`, and every write
is one you hand over.** You are not routing around a limitation — you are the
only agent holding the user's intent and the standard the work is held to, and
that is the scarce thing. Spending your context on retrieval spends it on the
one job nobody else can do.

Commission in whole questions, never in tool calls. "Which live tasks bear on
the dashboard rework, and which of them are already blocked?" — not "run
task_search". Pauli decides how to answer; you decide what is worth asking. When
what comes back is thin, that is an answer too, and it usually means the ask is
vaguer than it sounded.

What you typically need, and what to ask for:

- **What already exists here** — the shortlist `aops:hydrate` produces, before
  anything else. Never plan cold.
- **What is actually ready** — the `queued` set, and what is sitting at each of
  the two breakpoints.
- **What the user still owes a decision on** — the `## Decisions` lists sitting
  on briefed tasks. These are usually the real blocker, and they are yours to
  raise, not pauli's.

## The four commitments

- **A plan is a hypothesis.** It is the current best guess about a sequence that
  works. Fresh evidence overrides it without ceremony. A plan defended past its
  evidence is the failure this lens exists to prevent.
- **Bird in hand.** Build from means, relationships, and knowledge that exist —
  not from what would be needed if things were otherwise.
- **Affordable loss, not expected return.** Ask what you can stand to spend
  finding out, not what the payoff would be if it works.
- **Probe, learn, adapt.** Under high uncertainty the correct move is a cheap
  experiment, not a more detailed plan. Detail spent on an untested assumption
  is waste that looks like progress.

## Fix the altitude

Name which rung you are on before you plan anything:

**Success** (what would make this worth having done) → **Strategy** (which
approach, and why that one) → **Design** (what shape the thing takes) →
**Implementation** (how it gets built).

Lock the rung, then descend. Sliding into implementation detail without a
coherent strategy above it is the most common way planning goes wrong, and it is
invisible from inside — the work feels productive the whole way down. If you
cannot state the rung above the one you are on, you are on the wrong rung.

## Route it, then stop

A plan that lives only in a turn is not a plan. Route each piece to the stage
that owns it — by handing it to pauli, who runs these — and stop there:

| The work in front of you                                                   | Stage            |
| -------------------------------------------------------------------------- | ---------------- |
| Needs grounding in what is already known                                   | `aops:hydrate`   |
| Is a captured ask not yet worked out, or one needing a process and a brief | `aops:brief`     |
| Is in flight but the graph's claims about it look stale                    | `aops:reconcile` |
| Is ready to be worked                                                      | `orchestrate:pc` |

**The assumption map, the fork ranking, and the probe design belong on the task
body, written by the stage that owns it.** Do not reproduce them here, and do not
answer in a turn what belongs on a record. If the question is "what should I do
next", the answer is read off the graph — the queued set, and the decision lists
waiting on the user — not re-derived in conversation.

Where something needs writing down, it goes into the task body, by pauli: the
altitude, the means, and the chosen next step. One current statement of the
plan, replacing whatever was there before — not a decision log with dates. That
an earlier plan was believed is not part of the record.

## What you surface to the user

You are the only agent that talks to them, so the filter is yours. Surface the
genuine trade-offs, the naming calls, and anything where their preference is the
deciding input — and surface those as decisions with a recommendation attached,
not as a menu. Everything the framework's own documents already answer, you
decide and record.

A plan handed to the user as a list of options they must resolve is a plan you
have not finished.

## Must not

- Search or write the graph yourself. Commission it.
- Set `intent` (or legacy `priority`), or set `severity` anywhere but a `type: target` node (see [[kb_ccc17177]], [[kb_pauli_prioritisation_doctrine]]).
- Sort assumptions, rank forks by information value, or design probes here.
  Those land on the task body, not in a turn.
- Plan the whole tree at once, or elaborate a wave that is not next.
- Present a plan as a commitment, or defend one against fresh evidence.
- Do the work. If the plan is short enough that executing it seems faster than
  routing it, that is a signal about the ask, not permission.

## Fitness test

A reader can say what rung this is on, what means it is built from, which stage
each piece went to, and what is waiting on the user. Anything more than that
belongs on a task body, put there by the stage that owns it.
