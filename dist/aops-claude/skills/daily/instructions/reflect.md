# Daily Note: Reflection

Structured end-of-day and weekly reflection on intention progress. This is a subset of the `/daily` skill — reflection is how intentions become learning.

Invoked when the user says "reflect", "end of day", "how did today go", "weekly review", or similar.

## End-of-Day Reflection

### Step 1: Load Context

Read `$ACA_DATA/intentions.yaml` to get active intentions and their root IDs. Note today's date. Find today's daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md`.

### Step 2: Per-Intention Progress

For each active intention, use `mcp__pkb__get_task_children(id=root_id, recursive=True)` to get all descendants. Identify tasks that were completed today (status `done` and `modified` date matching today). Compute the progress delta (tasks done today and cumulative %). Identify what's ready for tomorrow.

Present per intention:

```markdown
## Reflection: 2026-03-10

### Get the OSB benchmarking study out

**Today's progress**: 3 tasks completed (+15%, now 75%)

- [ns-abc] Write methods section
- [ns-def] Run benchmark suite
- [ns-ghi] Clean dataset B

**Tomorrow's next actions**:

1. [ns-jkl] Draft results section — P1
2. [ns-mno] Create figures for Chapter 4 — P2

**Blockers**: [ns-pqr] Ethics approval — still waiting
```

### Step 3: Intention Health Check

For each intention, ask: "Did '[label]' get the attention it deserved today?"

Options: "Yes" | "Some" | "No"

**If "No"**: Follow up: "What got in the way?" Options: "Interruptions" | "Different priority" | "Stuck" | "Energy"

If "Stuck": offer to create a blocker task or decompose further.

### Step 4: Intention Relevance

Ask: "Are your current intentions still the right focus?"

Options: "Yes, keep them" | "Adjust" | "One is done"

**If "One is done"**: Trigger `/intend done` flow.
**If "Adjust"**: Suggest `/intend` to modify.

### Step 5: Unplanned Work

Look at tasks completed today (status `done`, modified today). Identify which ones fall outside all active intention subgraphs by comparing their project/parent chain against the intention root IDs and their descendants. Report any tasks completed outside intentions and ask: "Should any of this become an intention?"

### Step 6: Write Reflection

Append the reflection summary to the daily note's `## Today's Story` section. Write as concise prose, not raw data:

```markdown
Good progress on OSB study — methods section done, benchmark suite run. 75% complete.
Didn't touch the intentions feature today; interrupted by CI fixes and student emails.
Ethics approval still blocking dataset C work.
```

Include: per-intention progress with delta, attention assessment, blockers encountered, any intention changes, unplanned work noted.

## Weekly Review

Invoked with "weekly review" or similar.

### Step 1: Load Week's Data

Read daily notes from the past 7 days from `$ACA_DATA/daily/`. Load current intentions. Review task completions across the week.

### Step 2: Per-Intention Weekly Summary

For each intention (including any completed or replaced during the week), present:

```markdown
## Weekly Review: 2026-03-03 to 2026-03-10

### Get the OSB benchmarking study out

**Weekly progress**: 45% → 75% (+30%)
**Tasks completed**: 8
**Days with attention**: 5/7
**Current blockers**: Ethics approval (7 days waiting)
**Assessment**: Strong week. On track for completion by March 20.
```

### Step 3: Time Allocation

Estimate how sessions were distributed across intentions and outside work:

```markdown
### Time Allocation

- OSB study: ~60% (5 days)
- Intentions feature: ~20% (2 days)
- Outside intentions: ~20% (CI fixes, admin, email)
```

### Step 4: Next Week Planning

Ask: "Are these still the right intentions for next week?"

Options: "Keep same" | "Swap one" | "Fresh start"

### Step 5: Write Weekly Summary

Write to `$ACA_DATA/daily/YYYYMMDD-weekly-review.md` with the weekly summary.

## Philosophy

Reflection is not surveillance. It's about:

1. **Noticing patterns** — What keeps getting in the way? What energises you?
2. **Adjusting intentions** — Are you working on the right things? Has something changed?
3. **Celebrating progress** — 3 tasks completed toward a meaningful intention is a good day.
4. **Honest assessment** — "I didn't have the energy" is a valid answer. The system adapts.

The reflection should feel like a brief conversation with a supportive colleague, not a performance review.
