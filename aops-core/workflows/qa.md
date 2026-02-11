---
id: qa
category: quality-assurance
bases: [base-task-tracking, base-qa]
---

# QA

Quality assurance and verification workflows. Multiple modes for different verification needs.

## Routing Signals

- Feature complete, before final commit
- User-facing functionality changes
- Complex changes with acceptance criteria
- Building QA infrastructure
- Framework integration validation

## NOT This Workflow

- Code review / skeptical review → [[critic]]
- Bug investigation → [[debugging]]
- Trivial changes (typo fixes)

---

## Mode: Quick Verification

**Default mode.** Pre-completion sanity check. "Does it run without error?"

### When to Use

- Feature complete, tests pass
- Before final commit
- User-facing changes

### Invocation

```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA]. Check functionality, quality, completeness.")
```

### Verdicts

- **VERIFIED**: Proceed to completion
- **ISSUES**: Fix critical/major issues, re-verify

---

## Mode: Acceptance Testing

Full user acceptance testing workflow. Creates test plans, runs qualitative evaluations, tracks failures.

### When to Use

- End-to-end testing needed
- User perspective verification
- Quality beyond pass/fail

### Core Principles

1. **Black-box testing only**: Test as user would. Don't read source code.
2. **Qualitative over mechanical**: Judgment calls about quality, not just exit codes.
3. **Criteria from specs**: Never derive criteria from code.
4. **Failures are not excused**: Create task for each failure.

### Task Structure

```
[Epic] Acceptance Testing: [Feature]
├── [Task] QA Test Plan: [Feature]
├── [Task] Execute QA Tests: [Feature]
├── [Task] Fix: [Issue 1]
└── [Task] Retest: [Feature]
```

### Workflow Steps

1. Create test plan task with scope, acceptance criteria, test cases, qualitative rubric
2. Get plan approved (human reviews)
3. Execute tests: setup → trigger → capture → evaluate → score → document
4. Report results: summary table, qualitative scores, detailed findings
5. Handle failures: create task per failure, link to test plan

### Invocation

```
Task(subagent_type="qa",
     prompt="Execute acceptance test plan from task [TASK-ID]. Evaluate qualitatively, document failures as new tasks.")
```

---

## Mode: Qualitative Assessment

Criteria-based qualitative evaluation of a feature against its user stories. Not "does it work?" but "is it any good for the people it was designed for?" This is skilled interpretive assessment requiring empathy, design judgment, and domain expertise.

### When to Use

- Feature has user stories or acceptance criteria describing WHY it exists
- You need to evaluate fitness-for-purpose, not just functional correctness
- The question is "would this actually help the user?" not "does it run?"
- UX quality, information architecture, or design intent matters

### NOT This Mode

- Functional verification (does code run?) → Quick Verification
- Spec compliance (are all items present?) → Acceptance Testing
- Code quality review → [[critic]]

### Philosophy

A building inspector checks if the wiring meets code. An architecture critic evaluates whether the building serves its inhabitants. Both are necessary. This mode is the **critic**, not the inspector.

The difference matters: a checklist can be executed mechanically. Quality assessment requires the evaluator to think, interpret, and exercise judgment. If your assessment plan could be executed by someone who has never thought about the user's situation, it's a checklist, not a quality assessment.

### Creating the Assessment Plan

The plan MUST NOT be a table of pass/fail criteria. It must be a structured guide for expert evaluation that can only be executed by someone who understands the user's context.

#### Step 1: Persona Immersion

Write a paragraph inhabiting the user. Not demographics — their **situation** when they encounter this feature:

- What emotional state are they in? (Anxious? Rushed? Overwhelmed? Curious?)
- What just happened before they got here? What are they trying to do next?
- What cognitive constraints are active? (Time pressure, divided attention, low working memory, fatigue)
- What does "success" feel like to them? Not completing a task — the felt experience of the tool working.

> **Example**: "You're an academic with ADHD. You've been away from your desk for 3 hours. You had 4 concurrent sessions running across two projects. You come back and you've lost the thread. You're already anxious about the paper deadline. You open this dashboard. You need a lifeline, not a data dump."

This paragraph IS the foundation of the entire assessment. If the evaluator can't write it, they can't do this evaluation.

#### Step 2: Scenario Design

Design 2-3 realistic usage scenarios. Each scenario must include:

- **Entry state**: Where is the user coming from? What's their current cognitive/emotional load?
- **Goal**: What they're actually trying to accomplish (the REAL goal, not the feature's stated purpose)
- **Constraints**: Time, attention, competing priorities, knowledge level
- **Success feel**: What does it feel like when this works well? Not "information is present" but "I feel oriented / confident / ready to act"

Scenarios should cover:
1. The **golden path** — the primary use case the feature was designed for
2. A **stressed path** — the user under pressure, low patience, high stakes
3. An **edge case** that reveals design philosophy — what happens when things are incomplete, ambiguous, or unusual?

#### Step 3: Assessment Dimensions

For each scenario, define 3-5 assessment dimensions. Each dimension is a **question requiring interpretive judgment**, NOT a binary check.

| Anti-pattern (don't do this) | Qualitative dimension (do this) |
|---|---|
| "Does the header show the session goal? Yes/No" | "When you scan the headers, can you reconstruct your working narrative? How much cognitive effort does it take? Does the information hierarchy match your priority hierarchy?" |
| "Are timestamps in HH:MM format? Yes/No" | "Does the temporal information help you orient in time, or does it add visual noise? Would a different time representation better serve the user's orientation needs?" |
| "Is DROPPED THREADS shown first? Yes/No" | "Does the display create appropriate urgency about unfinished work without triggering anxiety? Does the visual hierarchy match the emotional priority?" |
| "Are there colored dots? Yes/No" | "Do the visual status indicators reduce cognitive load, or are they decorative? Can you grasp the state of your work in a glance?" |

Dimensions should address:

1. **Immediate comprehension**: First 5 seconds — what does the eye land on? Does the visual hierarchy match the user's priority hierarchy?
2. **Cognitive load**: Does the information architecture work WITH the user's cognitive constraints, or against them?
3. **Task fitness**: Does the feature serve the user's actual goal (not just the feature's stated purpose)?
4. **Emotional response**: Does this reduce anxiety / create confidence / feel trustworthy? Or does it overwhelm / confuse / create doubt?
5. **Graceful degradation**: When data is incomplete or unusual, does the feature handle it in a way that maintains trust?

#### Step 4: Quality Spectrum

For each dimension, describe what **excellent** and **poor** look like — narratively, not as checkboxes:

> **Excellent**: The dropped-threads callout creates gentle urgency — it surfaces abandoned work prominently enough to see but frames it as "pick up where you left off" rather than "you failed to finish these." The user feels oriented and ready to act, not shamed.
>
> **Poor**: Dropped threads are listed in the same visual register as completed work. The user must scan everything equally to find what needs attention. Or worse: dropped threads are flagged with alarming styling that triggers anxiety rather than action.

The evaluator places the feature somewhere on this spectrum and **explains why with specific evidence**.

#### Step 5: Assessment Output

The output MUST be **narrative prose**, not tables. Structure:

1. **Context**: Brief restatement of who this is for and why it matters
2. **Per-scenario evaluation**: Walk through each scenario. For each dimension, write a paragraph of assessment citing specific evidence from the feature. What works? What doesn't? Why?
3. **Synthesis**: A holistic judgment. The whole may be more or less than the sum of its parts. A feature can pass every individual criterion and still feel wrong, or fail several and still fundamentally work.
4. **Recommendations**: Specific, actionable, empathetic to both user AND developer. Not "improve X" but "X falls short because [evidence]; consider [approach] because [reasoning about user need]"

### Executing the Assessment

1. **Read the spec and user stories.** Understand the INTENT — what problem is this solving and for whom? What emotional need does it address?
2. **Immerse in the persona.** Spend real time understanding who this is for. If the user story says "overwhelmed academic with ADHD," think about what that means for how they process information.
3. **Walk each scenario.** Use the feature as the persona would. Notice your own reactions — confusion, relief, frustration, delight. These are data.
4. **Evaluate each dimension in prose.** Cite specific evidence. "The header says X, which tells me Y but doesn't tell me Z, which means the user still has to..."
5. **Synthesize.** Step back. Does this feature fundamentally serve its purpose? Is it good?
6. **Recommend.** Be specific and constructive. Ground recommendations in user needs, not abstract quality standards.

### Assessment Plan Anti-Patterns

| Anti-Pattern | Why It Fails | Instead |
|---|---|---|
| Pass/Fail tables | Reduces nuance to binary; evaluator stops thinking | Narrative evaluation on a quality spectrum |
| Point scoring | Creates false precision; 73/100 means nothing | Qualitative judgment with evidence |
| "Is X present?" | Presence ≠ quality; a timestamp exists but is it useful? | "How well does X serve the user's need for Y?" |
| Checklist mindset | Can be executed without understanding the user | Require persona immersion before evaluation |
| Spec-as-checklist | Specs describe WHAT, not HOW WELL | Specs provide context; evaluate quality independently |
| Identical weight | Not all criteria matter equally to the user | Weight by impact on user's actual experience |
| Scoring rubrics | Invite mechanical execution; "3/4 = Good" | Require the evaluator to argue their judgment |

### Invocation

```
Task(subagent_type="qa",
     prompt="Qualitative assessment of [FEATURE] against user stories in [SPEC/TASK].
     Inhabit the user persona. Walk the scenarios. Evaluate fitness-for-purpose
     in narrative prose. Is this good for the people it was designed for?"
)
```

---

## Mode: Integration Validation

Framework integration testing. "Does it connect properly?"

### When to Use

- Validating new framework capabilities
- Verifying structural changes (relationships, computed fields)
- After framework modifications

### Unique Steps

1. **Baseline**: Capture state before running feature
2. **Execute**: Run feature as user would
3. **Verify**: Check structural changes
4. **Report**: Evidence table (expected vs actual)

### Evidence Format

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key] | [value]  | [value]| ✅/❌    |

### Invocation

```
Task(subagent_type="qa",
     prompt="Validate framework integration: [FEATURE]. Capture baseline, execute, verify structural changes, report evidence.")
```

---

## Mode: System Design

Design acceptance testing infrastructure for a project.

### When to Use

- "Design QA system", "build acceptance testing"
- New project needs verification strategy
- Existing tests pass but don't catch problems

### Core Principle

**Outcome over execution**: Tests that pass but don't detect problems are worse than no tests.

### Task Chain Pattern

```
[Epic: Acceptance Testing System]
├── T1: Inventory (what exists?)
├── T2: Gap Analysis (what's missing?) → depends on T1
├── T3: Design Workflow → depends on T2
├── T4: Define Test Cases → depends on T3
└── T5+: Implementation → depends on T4
```

### Phases

1. **Inventory**: Survey existing test frameworks, verification scripts, review processes
2. **Gap Analysis**: Assess against outcome-based QA capabilities
3. **Design Workflow**: Reviewer lifecycle, test case format, batch execution, reporting
4. **Define Test Cases**: Feature, expected behavior, fail condition, reproducible scenario
5. **Implementation**: Build the designed system

### Anti-Patterns

| Anti-Pattern | Why It Fails | Instead |
|--------------|--------------|---------|
| Pattern matching | Passes without understanding | Reviewer examines output |
| "Did it run?" tests | Passes broken behavior | Verify outcome is useful |
| Success = no errors | Silent failures pass | Define positive criteria |
| Skip to implementation | Build wrong thing | Complete design first |

---

## Cross-Client Robustness

AcademicOps supports multiple AI clients. Verify:

- Environment variables from one client don't break another
- Instructions are tailored to active client
- Tool output schemas are robust across client versions
