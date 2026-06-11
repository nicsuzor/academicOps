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

# /design-rubric — Design-Stage Fitness Rubric

Create or red-team a qualitative Fitness Rubric for user-facing features to define what excellence looks like. The rubric lives directly on the spec or epic body under `## Fitness Rubric`.

## Modes of Operation

1. **Author Mode**: Write a new rubric on a spec/epic body before implementation begins.
2. **Critique Mode**: Red-team an existing spec/decomposition before dispatch to identify gaps and unstated assumptions.

## When to Invoke

- Authoring a spec or epic body for user-facing deliverables (UX, prose, design output, dashboards).
- High-risk task preflights.
- Strategic reviews of plans.
- _Do not invoke_ for purely mechanical tasks (e.g. lint fixes, dependency bumps).

## Qualitative Bar Signals

A rubric is required if:

1. Criteria use qualitative terms ("intuitive", "calm", "beautiful").
2. The brief describes emotional/cognitive user states ("anxious", "depleted").
3. The primary consumer is a human.
4. Two evaluators could disagree on PASS/FAIL using the same evidence.
5. The task fits a fitness-for-purpose threshold.

If these apply and a rubric is missing at verify time, halt with: `REVISE — fitness rubric missing; escalate to pauli/design-rubric`.

## The Four-Step Rubric

1. **Persona**: One situational paragraph detailing the user's emotional state, cognitive constraints, and what success feels like. Do not write generic demographic profiles.
2. **Three Scenarios**: One short paragraph each.
   - **Golden**: Primary happy path.
   - **Stressed**: User under pressure (tired, late, divided attention).
   - **Edge**: Incomplete, late, or corrupted data.
3. **Dimensions**: 3 to 5 qualitative judgment questions. Focus on comprehension, cognitive load, task fitness, and degradation.
4. **Quality Spectrum**: Narrative description (not numeric) of _excellent_ vs. _poor_ execution for each dimension. Mark one critical dimension as `**load-bearing**` if applicable (marsha cannot PASS if this dimension is poor).

## Self-Instance Requirement

When the feature surfaces the user's OWN data or view ("show me my sessions", "my tasks", "where I was"), a generic instance of the thing appearing is not proof. The rubric must name the principal's concrete identifying signal — the exact fields, account, host, or launch-context that mark the artifact as HIS instance — so verification can later reproduce the principal's literal view and confirm his own data is present. Treat this as load-bearing on any "show MY X" feature: a generic-instance pass is a FAIL.

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

- <dimension question> — excellent: <prose>; poor: <prose>

**Red-team notes (critique mode only):**

- <unveiled assumptions / gaps identified>
```

## Critique Mode Protocol

1. Map scenarios to identify where the spec assumes capabilities the user lacks under pressure.
2. Document unstated assumptions (e.g., uninterrupted attention).
3. Identify missing qualitative dimensions.
4. Append findings to the "Red-team notes" section on the rubric.

## Anti-Patterns

| Anti-pattern               | Instead                                           |
| :------------------------- | :------------------------------------------------ |
| Binary Pass/Fail tables    | Narrative quality spectrum                        |
| Point scoring (e.g. 7/10)  | Qualitative judgment citing evidence              |
| Demographic personas       | Situation-first personas (current context, state) |
| Rubric in the verify brief | Rubric in the spec; brief links to it             |
| Skipping the stressed path | Focus on the depleted-user scenario               |

```json
Task(
  subagent_type="aops-core:pauli",
  prompt="Author a Fitness Rubric for <spec or epic>. Mode: <author | critique>. Land it on the spec body under `## Fitness Rubric`."
)
```
