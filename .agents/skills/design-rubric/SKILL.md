---
name: design-rubric
type: skill
category: instruction
description: Design-stage fitness rubric — persona immersion, scenario design, and the dimensions that define what excellence looks like for the people a feature serves. Two modes — author (produce a rubric for a new spec) and critique (red-team an existing spec). Use for "design the rubric", "fitness criteria", "what does success look like", "red team this spec", "will this overwhelm the user". Output lands on the spec, never in the verification brief. Owned by pauli.
permalink: skills-design-rubric
---

# /design-rubric — design-stage fitness rubric

Create or red-team a qualitative fitness rubric for a user-facing feature, to
define what excellence looks like. The rubric lives on the spec or epic body
under `## Fitness Rubric`.

Authoring and red-teaming are premise-and-fit judgment, not template-filling, so
this runs as `aops:pauli` (`plugins/aops/agents/pauli.md`).

## When a rubric is required

1. Criteria use qualitative terms ("intuitive", "calm", "beautiful").
2. The brief describes emotional or cognitive user states ("anxious",
   "depleted").
3. The primary consumer is a human.
4. Two evaluators could disagree on PASS/FAIL from the same evidence.
5. The task turns on a fitness-for-purpose threshold.

Where these apply and no rubric exists at verify time, halt with:
`REVISE — fitness rubric missing; escalate to pauli/design-rubric`.

## The four steps

1. **Persona** — one situational paragraph: the user's emotional state,
   cognitive constraints, and what success feels like. Situation first, never a
   demographic profile.
2. **Three scenarios**, one short paragraph each. **Golden**: the primary happy
   path. **Stressed**: the user under pressure — tired, late, attention divided.
   **Edge**: incomplete, late, or corrupted data.
3. **Dimensions** — 3 to 5 qualitative judgment questions covering
   comprehension, cognitive load, task fitness, and degradation.
4. **Quality spectrum** — narrative prose describing _excellent_ against _poor_
   execution for each dimension, never a number or a binary. Mark one dimension
   `**load-bearing**` where one applies: marsha cannot PASS if that dimension is
   poor.

## Self-instance requirement

Where the feature surfaces the user's OWN data or view ("show me my sessions",
"my tasks", "where I was"), a generic instance of the thing appearing is not
proof. The rubric names the principal's concrete identifying signal — the exact
fields, account, host, or launch context that mark the artifact as HIS instance —
so verification can reproduce his literal view and confirm his own data is
present. This is load-bearing on any "show MY X" feature: a generic-instance pass
is a FAIL.

## Output schema

Save directly to the spec or epic task body:

```markdown
## Fitness Rubric

**Persona:** <situational paragraph>

**Scenarios:**

- Golden: <entry / goal / constraints / success feel>
- Stressed: ...
- Edge: ...

**Dimensions & quality spectrum:**

- <dimension question> — excellent: <prose>; poor: <prose>

**Red-team notes (critique mode only):**

- <unveiled assumptions / gaps identified>
```

## Critique mode

1. Map the scenarios to find where the spec assumes capabilities the user lacks
   under pressure.
2. Document the unstated assumptions, such as uninterrupted attention.
3. Identify the missing qualitative dimensions.
4. Append the findings under "Red-team notes" on the rubric.
