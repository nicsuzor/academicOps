---
name: design-rubric
type: skill
category: instruction
description: Design-stage fitness rubric -- persona immersion, scenario design, and the dimensions that define what excellence looks like for the people a feature serves. Two modes -- author (produce a rubric for a new spec) and critique (red-team an existing spec). Use for "design the rubric", "fitness criteria", "what does success look like", "red team this spec", "will this overwhelm the user". Output lands on the spec, never in the verification brief. Owned by pauli.
permalink: skills-design-rubric
---

# /design-rubric -- Design-Stage Fitness Rubric

Create or red-team a qualitative fitness rubric for a user-facing feature, defining what excellence looks like on the spec or epic body under `## Fitness Rubric`. Authoring and red-teaming require premise-and-fit judgment, so this runs as `pauli`.

## When a Rubric Is Required

1. Criteria use qualitative terms ("intuitive", "calm", "beautiful").
2. The brief describes emotional or cognitive user states ("anxious", "depleted").
3. The primary consumer is a human.
4. Two evaluators could disagree on PASS/FAIL from the same evidence.
5. The task turns on a fitness-for-purpose threshold.

If these apply and no rubric exists at verification time, halt with `REVISE -- fitness rubric missing; escalate to pauli/design-rubric`.

## The Four Steps

1. **Persona** -- one situational paragraph covering the user's emotional state, cognitive constraints, and what success feels like (situation first, never a demographic profile).
2. **Three scenarios** (one short paragraph each): **Golden** (primary happy path), **Stressed** (user under pressure: tired, late, attention divided), and **Edge** (incomplete, late, or corrupted data).
3. **Dimensions** -- 3 to 5 qualitative judgment questions covering comprehension, cognitive load, task fitness, and degradation.
4. **Quality spectrum** -- narrative prose contrasting _excellent_ vs _poor_ execution for each dimension (never a number or binary). Mark `**load-bearing**` where applicable: verification cannot PASS if that dimension is poor.

## Self-Instance Requirement

Where the feature surfaces the user's own data or view ("show me my sessions", "my tasks", "where I was"), a generic instance is not proof. Name the user's concrete identifying signal -- exact fields, account, host, or launch context -- so verification can reproduce their literal view and confirm their own data appears. This is load-bearing on any personal-view feature: a generic-instance pass is a FAIL.

## Output Schema

Save directly to the spec or epic task body:

```markdown
## Fitness Rubric

**Persona:** <situational paragraph>

**Scenarios:**

- Golden: <entry / goal / constraints / success feel>
- Stressed: ...
- Edge: ...

**Dimensions & quality spectrum:**

- <dimension question> -- excellent: <prose>; poor: <prose>

**Red-team notes (critique mode only):**

- <unveiled assumptions / gaps identified>
```

## Critique Mode

1. Map scenarios to find where the spec assumes capabilities the user lacks under pressure.
2. Document unstated assumptions (such as uninterrupted attention).
3. Identify missing qualitative dimensions and append findings under `Red-team notes`.
