---
name: evaluate-dashboard
title: Evaluate Overwhelm Dashboard
description: User-centered evaluation of the Overwhelm Dashboard — does it reduce overwhelm for an ADHD user returning to work?
triggers: [evaluate dashboard, overwhelm dashboard, visual QA, dashboard evaluation, dashboard QA]
---

# Workflow: Evaluate Overwhelm Dashboard

This is not a test matrix. This is an evaluation of whether the dashboard **serves its user** — an academic with ADHD who is already overwhelmed, returning to work after a break, trying to reconstruct what was happening across multiple projects and machines.

The primary question is always: **does opening this dashboard make Nic feel more oriented, or more stressed?**

## 1. Setup

Start the dashboard:

```bash
uv sync --extra viz
uv run streamlit run lib/overwhelm/dashboard.py --server.headless true
```

Read the current specs before evaluating:

- `specs/overwhelm-dashboard.md` — acceptance criteria and ADHD design principles
- `specs/task-map.md` — task graph spec

## 2. The Cold Open (do this FIRST, before any technical checks)

Navigate to the dashboard. Pretend you are Nic at 9am. You slept badly. You have 6 projects, agents ran overnight, you can't remember what you were doing yesterday. You open this page.

**Narrate what you see and feel**, section by section, as you scroll:

- What's the first thing your eyes land on? Does it answer a question you actually have?
- How many seconds before you feel oriented? Before you feel _calm_?
- Is there a moment where the page makes you feel _worse_ — more confused, more overwhelmed, more lost?
- When you reach the bottom, can you articulate what you should do next?
- Did anything feel like noise — information that exists because the system has it, not because you need it?

Write this narration honestly. It is the most important part of the evaluation.

## 3. The Three Questions Test

Without scrolling, within 5 seconds of the page loading, can you answer:

1. **"What's running right now?"** — How many agents are active? Do any need me?
2. **"What got dropped?"** — What did I start yesterday that isn't done?
3. **"What needs me?"** — Is anything blocked on my input?

For each question: note whether the answer is _visible_, _findable with effort_, or _not there at all_. Note how it makes you feel — relieved, frustrated, anxious?

## 4. Section-by-Section Experience Review

For each visible section, evaluate through the user's lens:

| Question                                   | What to look for                                                    |
| ------------------------------------------ | ------------------------------------------------------------------- |
| **Does this section earn its space?**      | Would removing it make the page better or worse?                    |
| **Is this scannable in 3 seconds?**        | Can you get the gist without reading? Color, shape, density.        |
| **Does this create anxiety or reduce it?** | Long uncollapsible lists create anxiety. Progress bars reduce it.   |
| **Is the framing directive?**              | "YOUR PATH" vs "Session History". "NEEDS YOU" vs "Status: waiting". |
| **Would Nic actually use this?**           | Or is it there because it was in the spec?                          |

Pay special attention to:

- **YOUR PATH**: Is it signal or noise? Do "/clear" and "commit and push" sessions help or clutter?
- **Synthesis**: Does the narrative match the lived experience? Or is it generic?
- **Project Grid**: Can you find a specific project in under 5 seconds?
- **Page length**: How much scrolling? Does it feel like "there's a lot going on but I can handle it" or "oh god"?

## 5. Technical Verification

Now — and only now — check the spec compliance. Use `qa/dashboard-qa.md` for the detailed check matrix (D1-D9 per-task checks, E2E scenarios).

For each technical check, note not just pass/fail but: **does the user care?** A feature that passes its spec check but doesn't serve the user is still a problem. A feature that fails its spec check but the dashboard works better without it is fine.

Check data integrity against `$ACA_DATA/tasks/index.json` and `$ACA_DATA/outputs/graph.json`.

## 6. Write the Report

Write results to `qa/dashboard-qa-results-{date}.md`.

**Structure the report with the user experience FIRST:**

1. **Cold Open narration** — what you saw and felt
2. **Three Questions verdict** — could you answer them? How did it feel?
3. **Section experience review** — which sections earn their space?
4. **Emotional assessment** — overall, does this dashboard reduce overwhelm?
5. **Technical checks** — spec compliance matrix (pass/fail/untested)
6. **Issues** — prioritized by user impact, not spec severity
7. **Verdict**: VERIFIED or ISSUES

## 7. Decomposition & Task Creation

After the report, create follow-up work:

1. Prioritize by **user impact**, not spec compliance. A missing feature that nobody notices is P3. A rendering issue that creates anxiety is P1.
2. Each task's acceptance criteria should describe the _user experience change_, not just the technical fix. Not "add STALE badge" but "user sees clear indicator that synthesis is outdated and knows how to refresh it."
3. Link tasks to the QA report and relevant spec section.
