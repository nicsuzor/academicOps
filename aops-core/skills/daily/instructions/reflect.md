# Daily Note: Reflection

Structured end-of-day and weekly reflection on work progress. This is a subset of the `/daily` skill — reflection is how work becomes learning.

Invoked when the user says "reflect", "end of day", "how did today go", "weekly review", or similar.

## End-of-Day Reflection

### Step 1: Load Context

Find today's daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md`. Read the `## Focus` section (including `### My priorities` if present) and the `## Today's Story` section.

### Step 2: Gather Today's Progress

Query PKB for tasks completed today:

```python
# Get tasks completed — use a high limit to avoid missing any
completed_today = mcp__pkb__list_tasks(status="done", limit=200)
# Filter to tasks with modified date matching today
```

Also check the daily note's work log for merged PRs and session summaries.

### Step 3: Compare Against Priorities

Compare completed work against the `### My priorities` subsection in today's Focus section:

- Which stated priorities got attention?
- Which were neglected?
- What unplanned work happened instead?

Present per-project progress:

```markdown
## Reflection: 2026-03-10

### Progress by project

**OSB Benchmarking** — 3 tasks completed (+15%)

- [ns-abc] Write methods section
- [ns-def] Run benchmark suite
- [ns-ghi] Clean dataset B

**academicOps** — 1 task completed

- [task-xyz] Fix CI pipeline

### Against priorities

- ✅ OSB study — strong progress
- ⏳ ARC report — started but not submitted
- ❌ Student feedback — didn't get to it

### Tomorrow's next actions

1. [ns-jkl] Draft results section — P1
2. [ns-mno] Create figures for Chapter 4 — P2

**Blockers**: [ns-pqr] Ethics approval — still waiting
```

### Step 4: Attention Check

Ask: "Did your stated priorities get the attention they deserved today?"

Options: "Yes" | "Some" | "No"

**If "No"**: Follow up: "What got in the way?" Options: "Interruptions" | "Different priority" | "Stuck" | "Energy"

If "Stuck": offer to create a blocker task or decompose further.

### Step 5: Priority Relevance

Ask: "Are your current priorities still the right focus for tomorrow?"

Options: "Yes, keep them" | "Adjust" | "Need a reset"

**If "Adjust"**: Update `### My priorities` in tomorrow's daily note. If tomorrow's note does not exist, create it before updating.
**If "Need a reset"**: Suggest `/strategy` session for strategic replanning.

### Step 6: Write Reflection

Append the reflection summary to the daily note's `## Today's Story` section. Write as concise prose, not raw data:

```markdown
Good progress on OSB study — methods section done, benchmark suite run. 75% complete.
Didn't touch the ARC report; interrupted by CI fixes and student emails.
Ethics approval still blocking dataset C work.
```

Include: per-project progress, priority comparison, blockers encountered, any priority changes, unplanned work noted.

## Weekly Review

Invoked with "weekly review" or similar.

### Step 1: Load Week's Data

Read daily notes from the past 7 days from `$ACA_DATA/daily/`. Review task completions across the week by project.

### Step 2: Per-Project Weekly Summary

Summarise progress by project:

```markdown
## Weekly Review: 2026-03-03 to 2026-03-10

### OSB Benchmarking

**Tasks completed**: 8
**Days with attention**: 5/7
**Current blockers**: Ethics approval (7 days waiting)
**Assessment**: Strong week. On track for completion by March 20.

### academicOps

**Tasks completed**: 3
**Days with attention**: 3/7
**Assessment**: Maintenance mode — CI fixes and graph health.
```

### Step 3: Time Allocation

Estimate how sessions were distributed across projects:

```markdown
### Time Allocation

- OSB study: ~60% (5 days)
- academicOps: ~20% (2 days)
- Admin/email: ~20% (ad hoc)
```

### Step 4: Next Week Planning

Ask: "What are your priorities for next week?"

Options: "Same as this week" | "Shift focus" | "Need to think"

### Step 5: Write Weekly Summary

Write to `$ACA_DATA/daily/YYYYMMDD-weekly-review.md` with the weekly summary.

## Philosophy

Reflection is not surveillance. It's about:

1. **Noticing patterns** — What keeps getting in the way? What energises you?
2. **Adjusting priorities** — Are you working on the right things? Has something changed?
3. **Celebrating progress** — 3 tasks completed toward a meaningful goal is a good day.
4. **Honest assessment** — "I didn't have the energy" is a valid answer. The system adapts.

The reflection should feel like a brief conversation with a supportive colleague, not a performance review.
