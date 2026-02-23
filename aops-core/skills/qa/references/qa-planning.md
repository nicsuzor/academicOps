# QA Planning Mode

Design acceptance criteria and QA plans that evaluate fitness-for-purpose, not just functional correctness. This is the upstream counterpart to qualitative assessment: where qualitative assessment evaluates an existing feature, QA planning designs the criteria and plans that future evaluation will use.

## When to Use

- Writing acceptance criteria for a spec or task
- Designing a QA plan for a feature epic
- Reviewing existing acceptance criteria for quality
- Any time you're defining what "done" looks like before work begins

## NOT This Mode

- Evaluating completed work → Qualitative Assessment or Quick Verification
- Running existing test plans → Acceptance Testing
- Designing test infrastructure → System Design

## Why This Mode Exists

Acceptance criteria are usually written as binary checklists: "Legend is visible", "Labels show titles not IDs", "Node size correlates with downstream_weight." These can be verified mechanically without understanding the user. They pass when the feature is technically present but experientially poor.

The qualitative-assessment reference describes how to evaluate features against user stories using persona immersion, scenarios, and narrative judgment. But that guidance only reaches the agent doing evaluation — the agent writing the criteria in the first place never sees it. The result: good evaluation methodology applied to mediocre criteria.

QA planning closes this gap by applying qualitative thinking at the point where criteria are designed.

## The Workflow

### Phase 1: Understand the Intent

Before writing any criteria, understand what the feature is FOR.

**Read the spec or user story.** Not to extract a checklist — to understand the intent. What problem does this feature solve? For whom? Under what constraints? If there's no spec, write one first (see [[skills/framework/workflows/06-develop-specification.md]]).

**Inhabit the persona.** Write a paragraph about the user's situation when they encounter this feature. Not demographics — their cognitive and emotional state:

- What just happened before they got here?
- What are they trying to accomplish (the real goal, not the surface task)?
- What constraints are active? (time pressure, divided attention, fatigue, anxiety)
- What does success FEEL like?

This paragraph anchors all subsequent criteria. If you skip it, you'll write mechanical checks.

**Identify the design principles.** What domain constraints shape this feature? For ADHD-facing features: scannable not studyable, dropped threads first, no flat displays at scale, support focus transitions. For research tools: reproducibility, traceability, integrity. These principles are the criteria behind the criteria — they explain WHY a check matters and help the evaluator exercise judgment.

### Phase 2: Design Criteria

**Write user stories first, criteria second.** User stories describe the need in the user's terms. Acceptance criteria describe how to verify the need is met. If you write criteria without stories, you get mechanical checklists that can pass while the user is still frustrated.

A user story for QA planning purposes needs:

- **Situation**: When/where the user encounters this (entry state, not just "as a user")
- **Need**: What they're trying to accomplish (real goal)
- **Constraint**: What makes this hard (cognitive load, time, scale, emotional state)
- **Success feel**: What it's like when this works well

**Transform binary checks into qualitative dimensions.** Every criterion should require interpretive judgment, not just observation:

| Binary check (avoid)                                    | Qualitative dimension (use)                                                                                  |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| "Legend is visible without interaction"                  | "Can a first-time viewer decode the graph's visual language without instructions?"                           |
| "Node size correlates with downstream_weight"            | "Does the visual hierarchy match the importance hierarchy? Can you spot the highest-impact work at a glance?" |
| "Labels show titles not IDs"                             | "Can you understand what each node represents without hovering or clicking?"                                 |
| "Stale sessions have archive prompt"                     | "Does the interface help you let go of stale work without anxiety about losing context?"                     |
| "Section order matches spec"                             | "Does the page answer your three questions (what's running, what's dropped, what needs me) before you scroll?"|

Binary checks are useful for regression testing after the feature ships. They are insufficient for evaluating whether the feature serves the user.

**Define quality spectra, not pass/fail criteria.** For each dimension, describe what excellent and poor look like — narratively, not as checkboxes:

> **Dimension**: "Can you spot the highest-impact work at a glance?"
>
> **Excellent**: Opening the graph, your eye is immediately drawn to 2-3 large, distinctly-shaped nodes. You can tell without reading any labels that these are the high-leverage points in your work. Size and color create a natural reading order — you know where to look first.
>
> **Poor**: All nodes are the same size. The graph is a cloud of identical circles. You have to read labels or hover to find anything important. The visual hierarchy communicates nothing about work importance.

The evaluator's job is to locate the actual implementation on this spectrum and cite specific evidence.

**Design scenarios, not test cases.** Each scenario should include:

- **Entry state**: Where is the user coming from? What's their current cognitive/emotional load?
- **Goal**: What they're actually trying to accomplish
- **Constraints**: Time, attention, competing priorities
- **Success feel**: What it feels like when this works well

Scenarios should cover:

1. The **golden path** — primary use case, reasonable conditions
2. A **stressed path** — user under pressure, limited attention
3. An **edge case** — incomplete data, unusual state, first-time use

### Phase 3: Write the QA Plan

**Per-task QA** should include:

- Which user story this task serves (the "why" — links the task to the user's actual need)
- 2-3 qualitative dimensions to evaluate (the "what" — questions requiring judgment)
- Quality spectrum for each dimension (what excellent/poor look like)
- One concrete scenario to walk through (the "how" — a realistic usage situation)
- Regression checks (binary checks that guard against breaking changes after the feature works)

Regression checks are the place for binary yes/no verification. They serve a different purpose than qualitative dimensions: they prevent backsliding, not evaluate fitness. Keep them separate and labeled as regression checks.

**E2E evaluation suites** evaluate the whole feature, not individual tasks. Structure them using the qualitative-assessment workflow:

1. Persona immersion (one paragraph, from the assessment plan)
2. Scenario walkthrough (entry state → actions → observations)
3. Per-dimension evaluation (narrative prose with specific evidence)
4. Synthesis (holistic judgment — the whole may be more or less than sum of parts)
5. Recommendations (specific, actionable, empathetic to both user and developer)

The E2E plan is a guide for a skilled evaluator, not a script for a robot. If an agent can execute the QA plan without understanding the user, the plan is too mechanical.

### Phase 4: Validate the Plan

Before finalizing, self-check:

- **Traceability**: Can I trace every criterion back to a user story? Criteria without stories are unanchored — they test what was built, not what was needed.
- **Evaluator independence**: Would a different evaluator, reading only this plan, understand what "good" means? Or does the plan assume knowledge the evaluator won't have?
- **Frustration detection**: Are there criteria that could all pass while the user is still frustrated? If so, the criteria are measuring the wrong things.
- **Outcome focus**: Am I testing outcomes (user can orient in 5 seconds) or implementation details (node size > 6px)? Implementation details belong in regression checks, not acceptance criteria.
- **Quality spectrum coverage**: Does every qualitative dimension have an excellent/poor description? Without the spectrum, the evaluator has no calibration.

## Worked Example

This example uses the task map visualization from the overwhelm dashboard (session 2026-02-23) to show the transformation from mechanical criteria to qualitative criteria.

### Before (mechanical criteria — the anti-pattern)

```
| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | Labels show titles not IDs | Now shows human-readable title |
| 2 | No ID fallback visible | No labels consist of hash-style IDs |
| 3 | Progressive reveal — zoomed out | Only goal/project labels visible |
| 4 | Label truncation reasonable | Truncated with ellipsis, not mid-word |
```

This can be evaluated by pattern matching. An agent can check these without understanding why labels matter or what the user is trying to do.

### After (qualitative criteria)

**User story**: You open the task map to figure out where to focus. You have 15 minutes before a meeting. The graph has ~200 visible nodes. You need to find the one thing that will unblock the most work.

**Dimension**: "Can you read the graph without zooming?"

**Excellent**: At default zoom, the nodes that matter have readable labels. Projects and goals announce themselves. Task-level labels appear only when you zoom into a cluster — reducing noise at overview level. You can navigate by reading, not by hunting.

**Poor**: Labels are truncated to meaninglessness ("overwhelm-da..."), or every node has a label creating a wall of overlapping text, or the labels that show are the least important ones (leaf tasks labeled, goals unlabeled).

**Scenario**: Open dashboard after reindex. Don't touch the zoom. Can you identify which project cluster the "cowork MCP integration" task sits in? How many steps does it take — zero (it's visible), one (zoom to the right cluster), or many (hunt across the graph)?

## Anti-Patterns in QA Plan Design

| Anti-Pattern                        | Why It Fails                                                    | Instead                                                              |
| ----------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------- |
| Criteria without user stories       | No anchor — tests what was built, not what was needed           | Always trace criteria back to a story                                |
| Pass/fail tables for acceptance     | Evaluator stops thinking; presence ≠ quality                    | Qualitative dimensions with quality spectra                          |
| Implementation-detail criteria      | "Node size > 6px" passes when nodes are 7px but still invisible | Outcome criteria: "Can you spot the important nodes?"                |
| Same format for acceptance and regression | Conflates "is this good?" with "did we break it?"          | Separate qualitative acceptance from binary regression               |
| Criteria only the author understands | "Synthesis panel renders correctly" — what does correctly mean? | Describe excellent and poor so any evaluator can calibrate           |
| No scenarios                        | Criteria evaluated in a vacuum, divorced from usage context     | Every evaluation grounded in a realistic usage scenario              |

## Integration with Other Modes

- **QA Planning** (this mode) → designs criteria and plans BEFORE development
- **Qualitative Assessment** → evaluates features AFTER development using persona immersion
- **Acceptance Testing** → executes test plans, tracks failures, creates fix tasks
- **Quick Verification** → pre-completion sanity check (does it run?)
- **System Design** → designs QA infrastructure for a project

The handoff: QA Planning produces the criteria and plan. The developer builds the feature. Qualitative Assessment and Acceptance Testing evaluate the result against the plan. Quick Verification catches obvious breaks.

## Invocation

```
Task(subagent_type="qa",
     prompt="QA Planning mode. Design acceptance criteria and QA plan for [FEATURE]
     based on spec [SPEC]. Inhabit the user persona. Write qualitative dimensions
     with quality spectra, not binary checklists. Design scenarios, not test cases.
     Output: acceptance criteria for the spec + per-task QA + E2E evaluation suites.")
```
