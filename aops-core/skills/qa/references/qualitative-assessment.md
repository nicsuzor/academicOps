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

## Philosophy

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

| Anti-pattern (don't do this)                    | Qualitative dimension (do this)                                                       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| "Does the header show the session goal? Yes/No" | "Can you reconstruct your working narrative? How much cognitive effort does it take?" |
| "Are timestamps in HH:MM format? Yes/No"        | "Does the temporal information help you orient, or does it add visual noise?"         |
| "Is DROPPED THREADS shown first? Yes/No"        | "Does the display create appropriate urgency without triggering anxiety?"             |

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

## Data Pipeline Verification

For any feature that produces computed, aggregated, or transformed output, surface-level inspection is necessary but insufficient. You must trace the data pipeline end-to-end to verify **correctness**, not just **presence**.

### When to Apply

- Dashboards showing aggregated or computed data
- Features displaying data from external sources (APIs, files, databases)
- Generated artifacts (transcripts, reports, exports, summaries)
- Processing pipelines (collection → transformation → output)
- Any system where the output could be plausible but wrong

### Methodology: Forensic Data Tracing

For each section or component of the feature:

1. **Identify the data source.** Read the source code to find where the output originates — what file, API, database query, or computation produces it?
2. **Verify the source exists and is populated.** Don't assume. Check: does the file exist? Does the API return data? Is the query valid? Are the expected events being captured?
3. **Check data freshness, not just existence.** For real-time displays, verify data updates as expected over time, not just that it exists at rest. Static data in a dynamic field is a failure.
4. **Check edge cases: empty, stale, and missing sources.** What happens when the data source is empty, stale, or missing? Does the feature degrade gracefully or silently produce wrong output?
5. **Cross-verify output against source.** Independently query the data source (curl the API, read the file, run the query, inspect raw events) and compare against what the feature produces. Do the values match? Are timestamps correct? Is anything silently dropped or misrepresented?
6. **Explicitly test fallback chains.** For each data field, check if there's a fallback (e.g., using a different source if primary fails). Disable the fallback and verify the primary source works independently. Fallbacks can silently mask broken primary pipelines.
7. **Test with real runtime state.** For real-time displays, verify during an active session or while the system is under load, not just at rest. Stale data often only appears when the system is actually running.
8. **Document discrepancies with precision.** When output is wrong, note: the file path and line where data is fetched/transformed, what it should produce vs. what it actually produces, and the root cause.

### The Key Question

> "Is this the RIGHT data?" — not just "Does data appear?"

A dashboard can render beautifully, a transcript can read plausibly, a report can look complete — and still be fundamentally broken if it's reading from the wrong source, misinterpreting data, dropping events, or showing stale values as current. Output that looks plausible is the most dangerous kind of incorrect output.

### Design-Level Findings are QA Findings

QA is not just about bugs; it's about fitness-for-purpose. If a section renders correctly and matches the spec, but the data is misleading or the UX doesn't serve its stated purpose in context, that's a QA finding. Examples:

- "The prompt count matches the database but includes failed attempts, making it misleading for cost estimation."
- "The fallback chain works, but it masks a critical failure in the primary data source that the user needs to know about."
- "The data is correct but the information density is too high for the 'anxious academic' persona."

### Anti-Pattern: Breadth-First Surface Sweeps

Taking 30 screenshots, or skimming 10 transcript sections, and noting "output appears correct" for each is not verification. Go deep on each section before moving to the next. One section thoroughly verified is more valuable than ten sections superficially inspected.

## Executing the Assessment

1. **Read the spec and user stories.** Understand the INTENT.
2. **Immerse in the persona.** Spend real time understanding who this is for.
3. **Walk each scenario.** Use the feature as the persona would. Notice your reactions.
4. **For data-driven features: trace the pipeline.** After surface inspection, follow the data from source → processing → output. Cross-verify against actual data sources.
5. **Evaluate each dimension in prose.** Cite specific evidence.
6. **Synthesize.** Step back. Does this feature fundamentally serve its purpose?
7. **Recommend.** Be specific and constructive.

## Assessment Plan Anti-Patterns

| Anti-Pattern      | Why It Fails                                       | Instead                                        |
| ----------------- | -------------------------------------------------- | ---------------------------------------------- |
| Pass/Fail tables  | Reduces nuance to binary; evaluator stops thinking | Narrative evaluation on a quality spectrum     |
| Point scoring     | Creates false precision; 73/100 means nothing      | Qualitative judgment with evidence             |
| "Is X present?"   | Presence ≠ quality                                 | "How well does X serve the user's need for Y?" |
| Checklist mindset | Can be executed without understanding the user     | Require persona immersion before evaluation    |
| Identical weight  | Not all criteria matter equally                    | Weight by impact on user's actual experience   |

## Browser-Driven UI Assessment

When assessing a running web application, use Playwright MCP tools to drive a real browser session.

### Workflow

1. **Navigate** to the target URL (e.g., `mcp__playwright__browser_navigate`)
2. **Wait** for the page to load (`browser_wait_for` with textGone for loading indicators)
3. **Resize** to desktop resolution (`browser_resize` to 1920×1080)
4. **Screenshot** each distinct view/section (`browser_take_screenshot`)
5. **Interact** with UI elements to test functionality (`browser_click`, `browser_type`)
6. **Snapshot** for accessibility tree analysis (`browser_snapshot`)
7. **Assess** each screenshot against user stories and Visual Analysis Protocol

### Screenshot Storage

Save screenshots to `$AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/`. These are ephemeral session data, not repo artifacts.

### Report Storage

Write QA reports to `$ACA_DATA/eval/<project>-qa-YYYY-MM-DD.md`. Reports are PKB knowledge artifacts.

### Spec Location

Specs should be colocated with their code. Look for `spec.md` or `docs/spec.md` in the project directory.

## Follow-Up Task Creation

After completing an assessment, you MUST create a follow-up task in the PKB for any user story that received a FAIL or PARTIAL verdict. This is not optional — QA findings without tracked remediation are noise.

### Task format

- **Title**: `Address <project> QA findings — <N>/M user stories failing`
- **Project**: The project that was assessed
- **Priority**: p2 (unless findings include broken core functionality, then p1)
- **Body**: Link to the QA report, list each FAIL/PARTIAL with one-line summary, acceptance criteria = re-run QA and achieve improved pass rate

### Why

The QA report is evidence. The task is the action. Without a task, findings rot in eval/ and nothing changes. The assessment workflow is: assess → report → file task → task gets worked → re-assess.

## Invocation

```
Task(subagent_type="qa",
     prompt="Qualitative assessment of [FEATURE] against user stories in [SPEC/TASK].
     Inhabit the user persona. Walk the scenarios.
     If the task involves UI changes or visual artifacts, you MUST apply the Visual Analysis Protocol in references/visual-analysis.md.
     For running web apps, use Playwright to navigate, screenshot, and interact.
     Save screenshots to $AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/.
     Save report to $ACA_DATA/eval/.
     After assessment, create a follow-up task in the PKB for FAIL/PARTIAL findings.
     Evaluate fitness-for-purpose
     in narrative prose. Is this good for the people it was designed for?"
)
```
