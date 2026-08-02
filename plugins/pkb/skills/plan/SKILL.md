---
name: plan
description: An on-demand lens for "plan this", "what should I do next", and "where does this work go" — fix the altitude, check the plan against the effectual commitments, and route each piece to the stage that owns it. Optional, never a pipeline stage; the enrichment work itself belongs to `situate`.
agent: "pauli"
---

# Plan

Planning here is **effectual, not causal**. A causal plan starts from a desired
end state and works backwards to the resources it would need. An effectual plan
starts from the means actually in hand — what is known, who is available, what is
already built — and asks what can be made with them. Under real uncertainty the
second one survives contact and the first one does not.

This is a lens, not a stage. Nothing waits on it and nothing downstream assumes
it ran. Reach for it when a plan needs checking or an ask needs a home.

## The four commitments

- **A plan is a hypothesis.** It is the current best guess about a sequence that
  works. Fresh evidence overrides it without ceremony. A plan defended past its
  evidence is the failure this lens exists to prevent.
- **Bird in hand.** Build from means, relationships, and knowledge that exist —
  not from what would be needed if things were otherwise.
- **Affordable loss, not expected return.** Ask what you can stand to spend
  finding out, not what the payoff would be if it works.
- **Probe, learn, adapt.** Under high uncertainty the correct move is a cheap
  experiment, not a more detailed plan. Detail spent on an untested assumption is
  waste that looks like progress.

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
that owns it, and stop there:

| The work in front of you                                | Stage                                |
| ------------------------------------------------------- | ------------------------------------ |
| Needs grounding in what is already known                | [`hydrate`](../hydrate/SKILL.md)     |
| Is a captured ask not yet placed, valued, or worked out | [`situate`](../situate/SKILL.md)     |
| Is a released task about to be dispatched               | [`brief`](../brief/SKILL.md)         |
| Needs a process assembled around it                     | [`workflow`](../workflow/SKILL.md)   |
| Is in flight but the graph's claims about it look stale | [`reconcile`](../reconcile/SKILL.md) |

**The assumption map, the fork ranking, and the probe design are `situate`'s.**
Do not reproduce them here, and do not answer in a turn what belongs on a task
body. If the question is "what should I do next", the answer is read off the
graph — the ready set, and the `## Decisions` lists waiting at the promotion
gate — not re-derived in conversation.

Where you do write, write into the task body: the altitude, the means, and the
chosen next step. One current statement of the plan, replacing whatever was
there before — not a decision log with dates. That an earlier plan was believed
is not part of the record.

## Must not

- Set `priority`, or set `severity` anywhere but a `type: target` node.
- Duplicate `situate`: sort assumptions, rank forks by information value, or
  design probes here.
- Plan the whole tree at once, or elaborate a wave that is not next.
- Present a plan as a commitment, or defend one against fresh evidence.
- Surface a decision the framework's own documents already answer. Decide it and
  record the reasoning. Surface only genuine trade-offs, naming calls, and
  anything where the user's preference is the deciding input.

## Fitness test

A reader can say what rung this is on, what means it is built from, and which
stage each piece went to. Anything more than that belongs on a task body, put
there by the stage that owns it.
