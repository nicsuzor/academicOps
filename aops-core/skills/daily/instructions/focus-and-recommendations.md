# Daily Note: Focus and Recommendations

## 3. Today's Focus

Populate the `## Focus` section with priority dashboard and task recommendations. This is the FIRST thing the user sees after frontmatter.

### 3.1: Load Task Data

```python
# Get all tasks (limit=0 returns all)
tasks = mcp__pkb__list_tasks(limit=0)
```

Parse task data to identify priority distribution, overdue tasks, and blocked tasks.

#### Priority Distribution Counting (CRITICAL)

Call `task_summary` to get pre-computed counts. Do NOT count tasks manually.

```python
summary = mcp__pkb__task_summary()
# Returns: { "ready": N, "blocked": N, "by_priority": { "p0": N, "p1": N, "p2": N, "p3": N } }  # by_priority is a breakdown of ready tasks
```

`ready` = leaf tasks with claimable types (task/bug/feature), active status, all dependencies met.
This is the ONLY consumer-facing view. Use `summary["ready"]` as the denominator for priority bars.

> **Note (taxonomy)**: Daily planning legitimately surfaces `ready` (decomposed-but-not-yet-queued) tasks because the whole point of the daily review is to help the user decide what to promote from `ready` → `queued` for agent dispatch. See [[TAXONOMY]] §Status Values. Agent dispatch (`/pull`) pulls from `queued`, NOT `ready`.

**Format**: `P0 ░░░░░░░░░░ 9/333` where:

- `9` = `summary["by_priority"]["p0"]`
- `333` = `summary["ready"]` (total ready tasks)

**Wrong**: count by iterating all tasks and filtering by status strings
**Right**: use `task_summary` — counts are canonical and consistent with `list_tasks(status='ready')`

### 3.1.5: Generate Task Tree

After loading task data, generate the ASCII task tree for the `## Task Tree` section:

```python
mcp__pkb__get_task_network(
    exclude_status=["done", "cancelled"],
    max_depth=2
)
```

This provides a bird's eye view of active project hierarchy. The tree:

- Excludes completed and cancelled tasks
- Shows up to 2 levels deep (roots + children + grandchildren)
- Displays task ID, title, and status

**Format in daily note**:

```markdown
## Task Tree
```

[project-id] Project Name (status)
[task-id] Task title (status)
[subtask-id] Subtask title (status)

```
*Active projects with depth 2, excluding done/cancelled tasks*
```

Copy the `formatted` field from the response directly into the code block.

### 3.1.7: Query Pending Decisions

Count tasks awaiting user decisions (for decision queue summary):

```python
# Get ready tasks assigned to user (awaiting human promotion to queued)
ready_tasks = mcp__pkb__list_tasks(
    status="ready",
    assignee="nic",
    limit=50
)

# Get review tasks assigned to user (awaiting human judgment)
review_tasks = mcp__pkb__list_tasks(
    status="review",
    assignee="nic",
    limit=50
)

# Filter to decision-type tasks (exclude project/epic/goal)
EXCLUDED_TYPES = ["project", "epic", "goal"]
decisions = [
    t for t in (ready_tasks + review_tasks)
    if t.type not in EXCLUDED_TYPES
]

# Get topology for blocking counts
topology = mcp__pkb__get_task_network()

# Count high-priority decisions (blocking 2+ tasks)
high_priority_count = sum(
    1 for d in decisions
    if get_blocking_count(d.id, topology) >= 2
)

decision_count = len(decisions)
```

This count appears in the Focus section summary.

### 3.2: Build Focus Section

The Focus section combines priority dashboard AND task recommendations in ONE place.

When regenerating, **preserve user priorities**: If the Focus section contains a `### My priorities` subsection (user-written), keep it intact. Only regenerate the machine-generated content above it.

**Format** (all within `## Focus`):

```markdown
## Focus
```

P0 ░░░░░░░░░░ 3/85 → No specific tasks tracked
P1 █░░░░░░░░░ 12/85 → [ns-abc] [[OSB-PAO]] (-3d), [ns-def] [[ADMS-Clever]] (-16d)
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85

```
**Pending Decisions**: 4 (2 blocking other work) → `/decision-extract`

🚨 **DEADLINE TODAY**: [ns-xyz] [[ARC FT26 Reviews]] - Due 23:59 AEDT (8 reviews)
**SHOULD**: [ns-abc] [[OSB PAO 2025E Review]] - 3 days overdue
**SHOULD**: [ns-def] [[ADMS Clever Reporting]] - 16 days overdue
**DEEP**: [ns-ghi] [[Write TJA paper]] - Advances ARC Future Fellowship research goals
**ENJOY**: [ns-jkl] [[Internet Histories article]] - [[Jeff Lazarus]] invitation on Santa Clara Principles
**QUICK**: [ns-mno] [[ARC COI declaration]] - Simple form completion
**UNBLOCK**: [ns-pqr] Framework CI - Address ongoing GitHub Actions failures

*Suggested sequence*: Tackle overdue items first (OSB PAO highest priority given 3-day delay, then ADMS Clever).

### My priorities

(User's stated priorities are recorded here and never overwritten)
```

### 3.3: Reason About Recommendations

Select ~10 recommendations using judgment (approx 2 per category):

**🚨 DEADLINE TODAY (CRITICAL - always check first)**:

- Tasks with `due` date matching TODAY (within 24h)
- Format: `🚨 **DEADLINE TODAY**: [id] [[Title]] - Due HH:MM TZ (detail)`
- This category is NON-OPTIONAL - if ANY task has `due` within 24h, it MUST appear first
- Even if task seems low priority, imminent deadline overrides priority ranking
- `list_tasks(format="json")` now returns `due`, `effort`, `consequence`, and `focus_score` per task — use these fields when available
- `task_summary` returns `deadlines: { overdue, due_today, due_this_week }` counts — use these for the Deadline Dashboard (see below)
- When a task has a `consequence` field, include the consequence text in the recommendation (e.g. `🚨 **DEADLINE TODAY**: [id] [[Title]] - Due HH:MM TZ | Consequence: <consequence text>`)

**SHOULD (deadline/commitment pressure)**:

- Check `days_until_due` - negative = overdue
- Priority: overdue → due this week → P0 without dates (note: "due today" now goes to DEADLINE TODAY)
- **Effort-awareness**: If a task's `effort` estimate exceeds the time remaining before its deadline, treat it as critical and promote it to DEADLINE TODAY — regardless of absolute days remaining. Example: a task with `effort: "3 weeks"` due in 2 weeks is critical. Reference `urgency_ratio`: when `effort / time_remaining >= 1.0`, promote to DEADLINE TODAY.

**DEEP (long-term goal advancement)**:

- Tasks linked to strategic objectives or major project milestones
- Look for: research, design, architecture, foundational work
- Prefer tasks that advance bigger goals, not just maintain status quo
- Avoid immediate deadlines (prefer >7 days out or no deadline)

**ENJOY (variety/energy)**:

- Check `todays_work` - if one project has 3+ items, recommend different project
- Look for: papers, research, creative tasks
- Avoid immediate deadlines (prefer >7 days out)

**QUICK (momentum builder)**:

- Simple tasks: `subtasks_total` = 0 or 1
- Title signals: approve, send, confirm, respond, check
- Aim for <15 min

**UNBLOCK (remove impediments)**:

- Tasks that unblock other work or team members
- Infrastructure/tooling improvements, blocked issues
- Technical debt slowing down current work

### Deadline Dashboard

Before listing the first recommendation in the Focus section, insert a deadline summary line using `task_summary`:

```python
summary = mcp__pkb__task_summary()
deadlines = summary.get("deadlines", {})
overdue = deadlines.get("overdue", 0)
due_today = deadlines.get("due_today", 0)
due_this_week = deadlines.get("due_this_week", 0)
```

- If any count is non-zero, insert: `Deadlines: X overdue | Y due today | Z due this week`
- Omit the line entirely if all counts are zero
- If `overdue > 0`, surface overdue tasks first in the SHOULD section — include their `consequence` text if set
- This line appears immediately before the first recommendation (after the priority bars and Pending Decisions line)

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### 3.4: Check In and Engage User on Priorities

After presenting recommendations, check in with the user:

```
AskUserQuestion: "How are you feeling about your workstreams? Do the task statuses look accurate, or do things feel out of sync?"
Options: "Looks right" | "Out of sync" | "Need a reset"
```

**If "Out of sync"**: Walk through active workstreams with the user. For each, verify task statuses using `AskUserQuestion` batching: present 3–4 related tasks per question (including id, title, and current status) for fast triage, then apply the user's updates and continue until the active workstreams are in sync. Update the graph before continuing.

**If "Need a reset"**: Suggest `/strategy` session instead of continuing daily planning.

**If "Looks right"**: The recommendations are already on screen. Simply wait for the user to state their priorities for the day. Do NOT ask "What sounds right for today?".

**IMPORTANT**: User's response states their PRIORITY for the day. Record it in the `### My priorities` subsection of Focus. It is NOT a command to execute those tasks. The "My priorities" section is the SSoT for today-specific focus — agents answering "what are my priorities?" or "what should I work on?" should check this section first. After recording the priority:

1. Update the `### My priorities` subsection with user's stated priority
2. Continue to section 4 (progress sync)
3. After section 5 completes, output: "Daily planning complete. Use `/pull` to start work."
4. HALT - do not proceed to task execution

### 3.5: Present candidate tasks to archive

```
- [ns-xyz] **[[Stale Task]]** - [reason: no activity in X days]
```

Ask: "Any of these ready to archive?"

When user picks, use `mcp__pkb__update_task(id="<id>", status="cancelled")` to archive.
