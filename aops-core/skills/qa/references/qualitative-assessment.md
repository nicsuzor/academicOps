# Qualitative Assessment Mode

Criteria-based qualitative evaluation of a feature against its user stories. Not "does it work?" but "is it any good for the people it was designed for?" This is skilled interpretive assessment requiring empathy, design judgment, and domain expertise.

## When to Use

- Feature has user stories or acceptance criteria describing WHY it exists
- You need to evaluate fitness-for-purpose, not just functional correctness
- The question is "would this actually help the user?" not "does it run?"
- UX quality, information architecture, or design intent matters

## NOT This Mode

- Functional verification (does code run?) → Quick Verification
- Spec compliance (are all items present?) → Acceptance Testing
- Code quality review → [[critic]]

## Philosophy

A building inspector checks if the wiring meets code. An architecture critic evaluates whether the building serves its inhabitants. Both are necessary. This mode is the **critic**, not the inspector.

The difference matters: a checklist can be executed mechanically. Quality assessment requires the evaluator to think, interpret, and exercise judgment.

## Creating the Assessment Plan

The plan MUST NOT be a table of pass/fail criteria. It must be a structured guide for expert evaluation.

### Step 1: Persona Immersion

Write a paragraph inhabiting the user. Not demographics — their **situation** when they encounter this feature:

- What emotional state are they in? (Anxious? Rushed? Overwhelmed? Curious?)
- What just happened before they got here? What are they trying to do next?
- What cognitive constraints are active? (Time pressure, divided attention, low working memory, fatigue)
- What does "success" feel like to them?

> **Example**: "You're an academic with ADHD. You've been away from your desk for 3 hours. You had 4 concurrent sessions running across two projects. You come back and you've lost the thread. You're already anxious about the paper deadline. You open this dashboard. You need a lifeline, not a data dump."

### Step 2: Scenario Design

Design 2-3 realistic usage scenarios. Each scenario must include:

- **Entry state**: Where is the user coming from? What's their current cognitive/emotional load?
- **Goal**: What they're actually trying to accomplish (the REAL goal)
- **Constraints**: Time, attention, competing priorities, knowledge level
- **Success feel**: What does it feel like when this works well?

Scenarios should cover:

1. The **golden path** — the primary use case
2. A **stressed path** — the user under pressure
3. An **edge case** — what happens when things are incomplete or unusual?

### Step 3: Assessment Dimensions

For each scenario, define 3-5 assessment dimensions. Each dimension is a **question requiring interpretive judgment**, NOT a binary check.

| Anti-pattern (don't do this)                    | Qualitative dimension (do this)                                                                |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| "Does the header show the session goal? Yes/No" | "Can you reconstruct your working narrative? How much cognitive effort does it take?"          |
| "Are timestamps in HH:MM format? Yes/No"        | "Does the temporal information help you orient, or does it add visual noise?"                  |
| "Is DROPPED THREADS shown first? Yes/No"        | "Does the display create appropriate urgency without triggering anxiety?"                      |

Dimensions should address:

1. **Immediate comprehension**: First 5 seconds — does the visual hierarchy match priority hierarchy?
2. **Cognitive load**: Does the information architecture work WITH cognitive constraints?
3. **Task fitness**: Does the feature serve the actual goal?
4. **Emotional response**: Does this reduce anxiety / create confidence?
5. **Graceful degradation**: When data is incomplete, does the feature maintain trust?

### Step 4: Quality Spectrum

For each dimension, describe what **excellent** and **poor** look like — narratively, not as checkboxes:

> **Excellent**: The dropped-threads callout creates gentle urgency — surfaces abandoned work prominently but frames it as "pick up where you left off" rather than "you failed."
>
> **Poor**: Dropped threads are listed in the same visual register as completed work. The user must scan everything equally.

### Step 5: Assessment Output

The output MUST be **narrative prose**, not tables. Structure:

1. **Context**: Brief restatement of who this is for and why it matters
2. **Per-scenario evaluation**: Walk through each scenario. For each dimension, write a paragraph citing specific evidence.
3. **Synthesis**: A holistic judgment. The whole may be more or less than sum of parts.
4. **Recommendations**: Specific, actionable, empathetic to both user AND developer.

## Executing the Assessment

1. **Read the spec and user stories.** Understand the INTENT.
2. **Immerse in the persona.** Spend real time understanding who this is for.
3. **Walk each scenario.** Use the feature as the persona would. Notice your reactions.
4. **Evaluate each dimension in prose.** Cite specific evidence.
5. **Synthesize.** Step back. Does this feature fundamentally serve its purpose?
6. **Recommend.** Be specific and constructive.

## Assessment Plan Anti-Patterns

| Anti-Pattern      | Why It Fails                                             | Instead                                        |
| ----------------- | -------------------------------------------------------- | ---------------------------------------------- |
| Pass/Fail tables  | Reduces nuance to binary; evaluator stops thinking       | Narrative evaluation on a quality spectrum     |
| Point scoring     | Creates false precision; 73/100 means nothing            | Qualitative judgment with evidence             |
| "Is X present?"   | Presence ≠ quality                                       | "How well does X serve the user's need for Y?" |
| Checklist mindset | Can be executed without understanding the user           | Require persona immersion before evaluation    |
| Identical weight  | Not all criteria matter equally                          | Weight by impact on user's actual experience   |

## Invocation

```
Task(subagent_type="qa",
     prompt="Qualitative assessment of [FEATURE] against user stories in [SPEC/TASK].
     Inhabit the user persona. Walk the scenarios. Evaluate fitness-for-purpose
     in narrative prose. Is this good for the people it was designed for?"
)
```
