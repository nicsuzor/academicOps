---
name: planner
description: Effectual planning — build a plan from the means at hand, treat it as a hypothesis, and sequence the next step by what it teaches rather than by what feels urgent. The entry point for "plan this", "what should I do next", and "where does this work go". Routes into hydrate, situate, decompose, and brief; wires the result onto the graph.
agent: "pauli"
---

# Planner

Planning here is **effectual, not causal**. A causal plan starts from a desired
end state and works backwards to the resources it would need. An effectual plan
starts from the means actually in hand — what is known, who is available, what is
already built — and asks what can be made with them. Under real uncertainty the
second one survives contact and the first one does not.

Four commitments follow, and they are load-bearing:

- **A plan is a hypothesis.** It is the current best guess about a sequence that
  works. Fresh evidence overrides it without ceremony. A plan defended past its
  evidence is the failure this skill exists to prevent.
- **Bird in hand.** Build from means, relationships, and knowledge that exist —
  not from what would be needed if things were otherwise.
- **Affordable loss, not expected return.** Ask what you can stand to spend
  finding out, not what the payoff would be if it works.
- **Probe, learn, adapt.** Under high uncertainty the correct move is a cheap
  experiment, not a more detailed plan. Detail spent on an untested assumption is
  waste that looks like progress.

## Step 1 — fix the altitude

Name which rung you are on before you plan anything:

**Success** (what would make this worth having done) → **Strategy** (which
approach, and why that one) → **Design** (what shape the thing takes) →
**Implementation** (how it gets built).

Lock the rung, then descend. Sliding into implementation detail without a
coherent strategy above it is the most common way planning goes wrong, and it is
invisible from inside — the work feels productive the whole way down. If you
cannot state the rung above the one you are on, you are on the wrong rung.

## Step 2 — start from the means

Before proposing anything, get concrete about what exists. `hydrate` gives you
this: what is already known, already tried, already decided, and what standards
this class of work carries. Never plan cold.

Then write the means down plainly: what is built, what is known, who is
available, what constraints are real. The plan is what those afford — not what
the goal demands.

## Step 3 — surface the load-bearing assumptions

Every plan rests on beliefs that, if false, invalidate it. Name them, and sort
them into two lists:

- **Tested** — you have evidence. Cite it.
- **Hopes** — you do not. Say so.

An unexamined assumption is a silent failure mode two steps downstream. The
hopes list is the input to the next step; it is where the information is.

## Step 4 — sequence by information value

The next step is the one that teaches the most, not the one that feels most
productive and not the one that shouts loudest.

```
information_value ≈ downstream_weight × assumption_criticality
```

- **`downstream_weight`** — how much other work is waiting on this. Read it off
  the graph: `get_dependency_tree(id, direction="downstream")`, and the
  `contributes_to` edges into the targets this serves.
- **`assumption_criticality`** — how much of the plan collapses if the assumption
  behind this step turns out to be wrong. Read it off your own hopes list.

High on both is the next step. High downstream weight on a _tested_ assumption is
just execution — schedule it, do not agonise over it. High criticality with low
downstream weight is a cheap probe worth running now precisely because it is
cheap.

**Where a hope is critical, design the probe rather than planning past it.** The
smallest experiment that discriminates between "the hope holds" and "it does
not", and a sentence on what each outcome changes about the plan. A probe with no
decision attached is not a probe.

Never sequence by recency, by stated urgency alone, or by what is easiest to
start. Do not use `priority` to express your own view of importance — that band
is the user's intent, not an estimate (see
[`../graph-maintenance/references/taxonomy.md`](../graph-maintenance/references/taxonomy.md)).
Weight is expressed as `contributes_to` edge weight and target `severity`.

## Step 5 — put it on the graph

A plan that lives only in a turn is not a plan. Route each piece to the stage
that owns it, and stop there:

| The work in front of you                                     | Stage                                                |
| ------------------------------------------------------------ | ---------------------------------------------------- |
| Needs grounding in what is already known                     | [`hydrate`](../hydrate/SKILL.md)                     |
| Is one new ask that belongs on the graph                     | [`situate`](../situate/SKILL.md)                     |
| Is a placed task that has come due and needs cutting         | [`decompose`](../decompose/SKILL.md)                 |
| Is a cut subtask about to be dispatched                      | [`brief`](../brief/SKILL.md)                         |
| Needs a process assembled around it                          | [`workflow`](../workflow/SKILL.md)                   |
| Is structurally wrong on the graph — edges, parents, orphans | [`graph-maintenance`](../graph-maintenance/SKILL.md) |

Write the plan itself into the task body: the altitude, the means, the assumption
lists with their evidence, the chosen next step and the information-value
reasoning behind it, and the probe if there is one. Not a decision log with dates
— one current statement of the plan, replacing whatever was there before. When
the plan changes, the body states the new plan; that an earlier one was believed
is not part of the record.

## Rolling wave

Detail only the wave about to become actionable. Leave everything downstream as
one coarse placeholder with a one-line scope and a dependency back to what must
land first. Planning three steps out spends budget on information that does not
exist yet, and produces a plan that will be rewritten before it is read.

Re-plan when a wave lands. Same skill, same discipline, informed by what the
wave actually produced.

## Must not

- Set `priority`, or set `severity` anywhere but a `type: target` node.
- Plan the whole tree at once, or elaborate a wave that is not next.
- Present a plan as a commitment, or defend one against fresh evidence.
- Surface a decision the framework's own documents already answer. Decide it and
  record the reasoning. Surface only genuine trade-offs, naming calls, and
  anything where the user's preference is the deciding input.

## Fitness test

From the written plan alone, a reader can say: what rung this is on, what means
it is built from, which beliefs it rests on and which of those are untested, what
the next step is and why that one teaches the most, and what would falsify it. If
any of those needs reconstructing from a conversation the reader did not see, the
plan is not written yet.
