---
name: design-rubric
type: skill
category: instruction
description: Design-stage fitness rubric — persona immersion, scenario design, dimensions that define what excellence looks like for the people a feature serves. Two modes — author (produce a rubric for a new spec) and critique (red-team an existing spec). Output lives on the spec, not in the verification brief. Owned by pauli.
triggers:
  - "design the rubric"
  - "fitness criteria"
  - "what does success look like"
  - "evaluate design"
  - "red team this spec"
  - "will this overwhelm the user"
  - "AC for fitness"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - quality-assurance
  - design
owner: pauli
version: 0.1.0
permalink: skills-design-rubric
---

# /design-rubric — Fitness-for-Purpose at Design Time

## Why this is a design skill, not a QA skill

Persona immersion done at QA time is too late. The reviewer has the artifact in front of them, no original context, and the temptation to rationalise. Persona immersion done at design time shapes the spec — the acceptance criteria encode the persona's needs, and the verifier's job becomes simple: did the artifact meet the AC the persona drove?

The rubric is part of the spec. Marsha never re-derives it; she reads it. If marsha is invoking this skill, something has gone wrong upstream.

## Two modes

**Author mode** — you are writing a new spec or epic body. The deliverable has a real user. You need to define what excellence looks like before anyone builds anything.

**Critique mode** — a spec or decomposition already exists. Before dispatch, you red-team it: _if we build this as specified, will it serve the user, or overwhelm them?_ The output is the same shape as author mode (a Fitness Rubric on the spec), but the work is mostly identifying gaps and unstated assumptions.

Both modes produce a `## Fitness Rubric` section on the spec or epic body.

## When to invoke

- Authoring a spec or epic body where the deliverable is judged on fitness (UX, prose, design output, dashboard).
- Pauli's preflight on a high-blast-radius task that will produce user-facing work.
- Strategic review of a proposed plan or decomposition before dispatch.
- During decomposition, when planner sets up acceptance criteria for a user-facing epic.

Not needed for purely mechanical work (lint fix, test repair, dependency bump). If you can't name a user whose situation matters, you don't need a rubric.

### Five diagnostic signals that the bar is qualitative

Any one is sufficient to require a Fitness Rubric:

1. The acceptance bar uses adjectives of experience — "intuitive", "calm", "readable", "beautiful", "helpful", "useful".
2. The brief names a persona emotional or cognitive state — "tired", "anxious", "overwhelmed", "rushed", "depleted".
3. The intended consumer is a human in a cognitively-loaded context, not a downstream system or test runner.
4. Two reasonable evaluators could disagree on PASS/FAIL using the same evidence.
5. The brief uses fitness-for-purpose language — "serves the user", "lifeline not data dump", "lands softly".

If a task triggers one of these and arrives at marsha without a `## Fitness Rubric`, the verdict is `REVISE — fitness rubric missing; escalate to pauli/design-rubric`. Marsha does not improvise the rubric.

### Mixed-bar tasks

A single artifact often has both a mechanical bar (does it run / render / parse?) and a qualitative bar (is it any good for the user?). The rubric does not replace mechanical AC — it sits alongside them. At verify time, marsha checks both. Expect the qualitative judgement to take more reviewer attention than the mechanical check; if the brief makes the mechanical check dominate, the verdict will silently collapse to mechanical-pass-equals-ship.

## The four-step rubric

### 1. Persona — one paragraph, situational

Inhabit the user at the moment they encounter this feature. Not demographics, not identity. _Situation_: emotional state, what just happened, what's about to happen, cognitive constraints active right now, what success would feel like.

Example: "Nic, with ADHD, back at his desk after three hours away. Four sessions ran while he was gone. He's lost the thread. The paper deadline is this week. He opens the dashboard. He needs a lifeline, not a data dump."

If you can't write the persona paragraph without resorting to generic prose ("a busy professional who values efficiency"), you don't understand the user well enough yet. Stop and gather context.

### 2. Three scenarios

Each scenario is a short paragraph naming entry state, real goal (which may differ from the stated goal), constraints active in that moment, and what success _feels_ like.

- **Golden path** — the primary case the feature is designed for.
- **Stressed path** — the user under pressure (tired, late, divided attention, depleted).
- **Edge** — when data is partial, late, ambiguous, or wrong.

The stressed path is where most features quietly fail. Spend the most time here.

### 3. Dimensions — 3 to 5 per scenario, framed as judgement questions

A dimension is a question that requires interpretation, not a checkbox.

| Anti-pattern (don't)                    | Dimension (do)                                                              |
| --------------------------------------- | --------------------------------------------------------------------------- |
| "Does the header show session goal?"    | "Can the user reconstruct their working narrative? At what cognitive cost?" |
| "Are timestamps HH:MM?"                 | "Does temporal info help orient, or add noise?"                             |
| "Is the dropped-threads section first?" | "Does the display create appropriate urgency without triggering shame?"     |

Dimensions to consider in most rubrics:

- Immediate comprehension (first 5 seconds — does visual hierarchy match priority hierarchy?)
- Cognitive load (does it work _with_ constraints active in the scenario?)
- Task fitness (does it serve the real goal, not the stated one?)
- Emotional response (does it reduce anxiety or add to it?)
- Graceful degradation (when data is incomplete, does the feature maintain trust?)

### 4. Quality spectrum — narrative, not numeric

For each dimension, describe what _excellent_ and _poor_ look like in prose. Not "9/10". Not "meets standard." Sentences that a reviewer can later cite.

> **Excellent:** the dropped-threads callout creates gentle urgency — surfaces abandoned work prominently but frames it as "pick up where you left off" rather than "you failed."
>
> **Poor:** dropped threads listed in the same visual register as completed work. The user must scan everything equally.

### Load-bearing dimension (optional)

If one user concern clearly dominates the design, flag one dimension as `**load-bearing**`. This is not a numeric weight — it's a tie-breaker the verifier's synthesis paragraph must address explicitly. Marsha cannot reach PASS if the load-bearing dimension is poor, even if every other dimension is excellent. Use sparingly; if every dimension is load-bearing, none is.

## Output: the Fitness Rubric section

The rubric lives on the spec or epic body under `## Fitness Rubric`. Shape:

```markdown
## Fitness Rubric

**Persona:** <one paragraph, situational>

**Scenarios:**

- Golden: <entry / real goal / constraints / success feel>
- Stressed: ...
- Edge: ...

**Dimensions & quality spectrum:**

- <dimension question> — excellent: <prose>; poor: <prose>
- ...

**Red-team notes (critique mode only):**

- <gap or unstated assumption surfaced during review>
```

That section is what marsha reads at verify time. Pauli's verify-brief points at it; the brief does not duplicate it.

## Critique mode specifics

When red-teaming an existing spec, the work is mostly:

1. Read the spec as written. Walk the scenarios. Where does the spec assume something the user can't actually do in that state?
2. Name unstated assumptions. "This assumes the user has 30 seconds of uninterrupted attention" — if the stressed-path persona doesn't, that's a fit failure already baked into the design.
3. Identify dimensions the spec doesn't address. If the spec only talks about happy-path correctness and ignores the depleted-user case, the rubric should add the dimensions the spec missed.
4. Surface as "Red-team notes" on the rubric. These are inputs for the spec author to revise before dispatch.

The output is still a Fitness Rubric — but it now also documents the gaps that were closed (or are still open) before any worker is dispatched.

## What this skill does NOT do

- Run the QA pass. That's marsha + `/verify` against the rubric.
- Re-derive the rubric at verify time. That's contamination.
- Replace acceptance criteria. AC are concrete deliverables; the rubric is what excellence looks like, and it _informs_ AC at design time.
- Get invoked from a verification brief. If you're reading this from marsha's context, escalate upstream.

## Anti-Patterns

| Anti-pattern               | Why it fails                                                | Instead                                              |
| -------------------------- | ----------------------------------------------------------- | ---------------------------------------------------- |
| Pass/Fail tables           | Reduces nuance to binary; reviewer stops thinking           | Narrative quality spectrum                           |
| Point scoring              | False precision; 73/100 means nothing                       | Qualitative judgement with cited evidence            |
| Demographics-first persona | Treats persona as identity, not situation                   | Situation-first: what's happening _right now_        |
| Rubric in the brief        | Becomes a checklist when copied into the verifier's hands   | Rubric lives on the spec; brief links to it          |
| Generic personas           | "Busy professional who values efficiency" tells you nothing | Specific situation, real constraints, real day       |
| Skipping stressed path     | Most features fail at the depleted-user moment              | Stressed path gets the most attention, not the least |

## Relationship to other skills

- **/strategic-review** may invoke /design-rubric in critique mode when reviewing a proposed plan. The strategic review evaluates the proposal as a whole; the rubric is the persona-and-fitness slice.
- **/planner decompose** invokes /design-rubric (author mode) when the epic being decomposed has a real user-facing deliverable. The rubric lands on the epic body alongside acceptance criteria.
- **/verify** reads the rubric. Does not author or re-derive it.

## Invocation

```
Task(subagent_type="aops-core:pauli",
     prompt="Author a Fitness Rubric for <spec or epic>. Mode: author / critique.
     The rubric is for <user persona at a glance>.
     Land it on the spec body under `## Fitness Rubric`.")
```
