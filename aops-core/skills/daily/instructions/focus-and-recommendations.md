# Daily Note: Focus and Recommendations

## 3. Today's Focus

Populate the `## Focus` section with priority dashboard and task recommendations. This is the FIRST thing the user sees after frontmatter.

### 3.1: Load Task Data

```python
# Get all tasks (limit=0 returns all)
tasks = mcp__plugin_aops-core_task_manager__list_tasks(limit=0)
```

Parse task data to identify priority distribution, overdue tasks, and blocked tasks.

#### Priority Distribution Counting (CRITICAL)

**Both numerator AND denominator MUST use the same filter.**

```python
# Actionable = excludes terminal (done, cancelled) and suspended/transient statuses
ACTIONABLE_STATUSES = ["active", "inbox", "in_progress", "blocked", "waiting", "review", "merge_ready"]

actionable_tasks = [t for t in tasks if t["status"] in ACTIONABLE_STATUSES]
total_actionable = len(actionable_tasks)

# Count by priority within actionable tasks
priority_counts = {0: 0, 1: 0, 2: 0, 3: 0}
for task in actionable_tasks:
    p = task.get("priority", 2)  # default P2 if missing
    if p in priority_counts:
        priority_counts[p] += 1
```

**Format**: `P0 ░░░░░░░░░░ 9/333` where:
- `9` = actionable P0 tasks
- `333` = total actionable tasks (NOT total including done/cancelled)

**Wrong**: `P0 9/779` (numerator filtered, denominator unfiltered)
**Right**: `P0 9/333` (both filtered consistently)

### 3.1.3: Load Strategy Document

Read the strategy document to inform DEEP and priority recommendations:

```bash
Read $ACA_DATA/context/strategy.md
```

Extract from the strategy document:
- **Active strategic priorities** (projects/goals marked as current focus)
- **Temporal windows** (deadlines, funding rounds, semester boundaries)
- **Neglected priorities** (strategic goals with no recent task activity)

Use this context in section 3.3 when selecting DEEP recommendations — tasks that advance stated strategic priorities should be preferred over tasks that merely seem important in isolation.

### 3.1.5: Generate Task Tree

After loading task data, generate the ASCII task tree for the `## Task Tree` section:

```python
mcp__plugin_aops-core_task_manager__get_task_tree(
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
# Get waiting tasks assigned to user
waiting_tasks = mcp__plugin_aops-core_task_manager__list_tasks(
    status="waiting",
    assignee="nic",
    limit=50
)

# Get review tasks assigned to user
review_tasks = mcp__plugin_aops-core_task_manager__list_tasks(
    status="review",
    assignee="nic",
    limit=50
)

# Filter to decision-type tasks (exclude project/epic/goal)
EXCLUDED_TYPES = ["project", "epic", "goal"]
decisions = [
    t for t in (waiting_tasks + review_tasks)
    if t.type not in EXCLUDED_TYPES
]

# Get topology for blocking counts, downstream_weight, and stakeholder_exposure
topology = mcp__plugin_aops-core_task_manager__get_tasks_with_topology()

# Count high-priority decisions (blocking 2+ tasks)
high_priority_count = sum(
    1 for d in decisions
    if get_blocking_count(d.id, topology) >= 2
)

decision_count = len(decisions)
```

This count appears in the Focus section summary.

### 3.1.8: Identify Newly-Unblocked Tasks (MOMENTUM)

Cross-reference today's ready tasks against recently-completed dependencies to find MOMENTUM candidates:

```python
# Tasks currently active that have depends_on entries where ALL dependencies are now done
# These are tasks that recently became actionable because their blockers were resolved
momentum_candidates = [
    t for t in tasks
    if t["status"] == "active"
    and t.get("depends_on")  # had dependencies
    # Check topology: blocked_by_count == 0 means all deps resolved
]
```

Sort by `downstream_weight` DESC — newly-unblocked tasks with high downstream impact should surface first.

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
**DEEP**: [ns-ghi] [[Write TJA paper]] - Advances ARC Future Fellowship research goals (strategy: Research Impact)
**MOMENTUM**: [ns-stu] [[Pipeline batch support]] - Unblocked by schema fix (dw: 6.0)
**ENJOY**: [ns-jkl] [[Internet Histories article]] - [[Jeff Lazarus]] invitation on Santa Clara Principles
**QUICK**: [ns-mno] [[ARC COI declaration]] - Simple form completion
**UNBLOCK**: [ns-pqr] Framework CI - Address ongoing GitHub Actions failures (dw: 7.25)

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

**SHOULD (deadline/commitment pressure)**:

- Check `days_until_due` - negative = overdue
- Priority: overdue → due this week → P0 without dates (note: "due today" now goes to DEADLINE TODAY)

**DEEP (long-term goal advancement)**:

- Cross-reference tasks against the strategy document (loaded in 3.1.3)
- Prefer tasks that advance *stated strategic priorities* over tasks that merely seem important
- Look for: research, design, architecture, foundational work
- Check `downstream_weight` from topology data — high-weight tasks have outsized graph impact
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

**MOMENTUM (newly-unblocked opportunities)**:

- Tasks that recently transitioned from blocked → active (dependencies just completed)
- Check topology data: tasks with `blocked_by_count == 0` but that previously had dependencies
- These represent fresh opportunities where prerequisite work just finished
- Format: `**MOMENTUM**: [id] [[Title]] - Unblocked by [completed-dep-title]`
- High energy signal: completing these validates the dependency chain and may unblock further work

**UNBLOCK (remove impediments)**:

- Tasks that unblock other work or team members
- Prefer tasks with high `downstream_weight` — these have the largest cascading impact
- Infrastructure/tooling improvements, blocked issues
- Technical debt slowing down current work

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### 3.4: Engage User on Priorities

After presenting recommendations, use `AskUserQuestion` to confirm priorities:

- "What sounds right for today?"
- Offer to adjust recommendations based on user context

**IMPORTANT**: User's response states their PRIORITY for the day. Record it in the `### My priorities` subsection of Focus. It is NOT a command to execute those tasks. After recording the priority:

1. Update the `### My priorities` subsection with user's stated priority
2. Continue to section 4 (progress sync)
3. After section 5 completes, output: "Daily planning complete. Use `/pull` to start work."
4. HALT - do not proceed to task execution

### 3.5: Present candidate tasks to archive

```
- [ns-xyz] **[[Stale Task]]** - [reason: no activity in X days]
```

Ask: "Any of these ready to archive?"

When user picks, use `mcp__plugin_aops-core_task_manager__update_task(id="<id>", status="cancelled")` to archive.
