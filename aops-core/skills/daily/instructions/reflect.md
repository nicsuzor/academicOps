# Daily Note: Reflection

Structured end-of-day and weekly reflection on progress. This is a subset of the `/daily` skill — reflection is how work becomes learning.

Invoked when the user says "reflect", "end of day", "how did today go", "weekly review", or similar.

## End-of-Day Reflection

### Step 1: Load Context

Note today's date. Find today's daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md`. Load the user's stated priorities from the `### My priorities` section if present.

### Step 2: Today's Progress

List tasks completed today (status `done` and `modified` date matching today) using `mcp__pkb__list_tasks(status="done", limit=50)` and filter by today's date.

Group completed tasks by project/parent for readability:

```markdown
## Reflection: 2026-03-10

### OSB Benchmarking Study

**Tasks completed**: 3

- [ns-abc] Write methods section
- [ns-def] Run benchmark suite
- [ns-ghi] Clean dataset B

### Framework

**Tasks completed**: 1

- [aops-xyz] Fix CI pipeline

**Tomorrow's next actions**:

1. [ns-jkl] Draft results section — P1
2. [ns-mno] Create figures for Chapter 4 — P2

**Blockers**: [ns-pqr] Ethics approval — still waiting
```

### Step 3: Priority Alignment Check

Compare today's completed work against the user's stated priorities (from `### My priorities`). Ask: "Did today's work align with your priorities?"

Options: "Yes" | "Mostly" | "Got pulled away"

**If "Got pulled away"**: Follow up: "What got in the way?" Options: "Interruptions" | "Different priority" | "Stuck" | "Energy"

If "Stuck": offer to create a blocker task or decompose further.

### Step 4: Focus Check

Ask: "Are you working on the right things?"

Options: "Yes" | "Need to adjust" | "Not sure"

**If "Need to adjust"**: Help reprioritize — review P0/P1 tasks and suggest adjustments.

### Step 5: Unplanned Work

Identify tasks completed today that weren't in the user's stated priorities. Report them briefly and note whether they were worth the diversion.

### Step 6: Write Reflection

Append the reflection summary to the daily note's `## Today's Story` section. Write as concise prose, not raw data:

```markdown
Good progress on OSB study — methods section done, benchmark suite run.
Spent some time on CI fixes that weren't planned but were blocking the team.
Ethics approval still blocking dataset C work.
```

Include: progress summary, priority alignment assessment, blockers encountered, unplanned work noted.

## Weekly Review

Invoked with "weekly review" or similar.

### Step 1: Load Week's Data

Read daily notes from the past 7 days from `$ACA_DATA/daily/`. Review task completions across the week.

### Step 2: Per-Project Weekly Summary

Group completed tasks by project. Present progress:

```markdown
## Weekly Review: 2026-03-03 to 2026-03-10

### OSB Benchmarking Study

**Tasks completed**: 8
**Assessment**: Strong week. On track for completion by March 20.
**Current blockers**: Ethics approval (7 days waiting)

### Framework

**Tasks completed**: 3
**Assessment**: Maintenance work — CI fixes and small improvements.
```

### Step 3: Time Allocation

Estimate how sessions were distributed across projects:

```markdown
### Time Allocation

- OSB study: ~60% (5 days)
- Framework: ~20% (2 days)
- Admin/email: ~20%
```

### Step 4: Next Week Planning

Ask: "What should be the focus for next week?"

Options: "Same priorities" | "Shift focus" | "Need to think about it"

### Step 5: Write Weekly Summary

Write to `$ACA_DATA/daily/YYYYMMDD-weekly-review.md` with the weekly summary.

## Philosophy

Reflection is not surveillance. It's about:

1. **Noticing patterns** — What keeps getting in the way? What energises you?
2. **Adjusting priorities** — Are you working on the right things? Has something changed?
3. **Celebrating progress** — 3 tasks completed toward a meaningful goal is a good day.
4. **Honest assessment** — "I didn't have the energy" is a valid answer. The system adapts.

The reflection should feel like a brief conversation with a supportive colleague, not a performance review.
