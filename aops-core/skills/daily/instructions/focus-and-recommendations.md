# Daily Note: Focus and Recommendations

## 3. Today's Focus

Populate the `## Focus` section with priority dashboard and task recommendations. This is the FIRST thing the user sees after frontmatter.

### 3.0: Check Active Intentions

Before loading task data, read `$ACA_DATA/intentions.yaml`. If the file exists and contains one or more entries in `active`, intentions are active.

**If intentions are active**: After loading task data (Step 3.1), skip Steps 3.2-3.3 and use Step 3.2i (Intention-Organized Focus) instead. Then continue to Step 3.4i.

**If no intentions**: Proceed with Steps 3.1-3.4 as normal (category-based SHOULD/DEEP/ENJOY/QUICK/UNBLOCK).

### 3.1: Load Task Data

```python
# Get all tasks (limit=0 returns all)
tasks = mcp__pkb__list_tasks(limit=0)
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
# Get waiting tasks assigned to user
waiting_tasks = mcp__pkb__list_tasks(
    status="waiting",
    assignee="nic",
    limit=50
)

# Get review tasks assigned to user
review_tasks = mcp__pkb__list_tasks(
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

### 3.2i: Intention-Organized Focus (when intentions are active)

**Use this instead of Steps 3.2-3.3 when intentions are active.**

For each active intention, call `mcp__pkb__get_task(id=root_id)` to load the root, then `mcp__pkb__get_task_children(id=root_id, recursive=True)` to get all descendants. From the descendants, identify:

- `total` — all descendants
- `done` — descendants with status `done`
- `ready` — descendants that are leaf tasks with all dependencies met (ready to work)
- `blocked` — descendants with unmet dependencies
- `in_progress` — descendants currently being worked on
- `progress_pct` — done / total (treat as 0 if total is 0)

**Staleness check**: For each intention, assess whether any tasks have been completed within the last 7 days by checking the `modified` date on `done` descendants. If no tasks were completed in 7+ days, flag it:

```markdown
⚠️ **Stale intention**: "Ship the intentions feature" — no progress in 9 days. Still the right focus?
```

**Format** (all within `## Focus`):

```markdown
## Focus

### Active Intentions

#### 1. Get the OSB benchmarking study out

**Root**: [[OSB Benchmarking Study]] (project)
**Progress**: ██████░░░░ 12/20 tasks (60%)
**Ready**: 4 | **Blocked**: 2 | **In Progress**: 1

**Next actions**:

1. [ns-abc] [[Write methods section]] — P1, advances Chapter 3
2. [ns-def] [[Run benchmark suite on dataset B]] — P1, unblocks results
3. [ns-ghi] [[Draft limitations paragraph]] — P2, quick win

**Blockers**: [ns-jkl] [[Ethics approval for dataset C]] — blocks 3 tasks

#### 2. Ship the intentions feature

**Root**: [[Intentions Feature]] (epic)
**Progress**: ██░░░░░░░░ 3/15 tasks (20%)
**Ready**: 2 | **Blocked**: 0

**Next actions**:

1. [ns-mno] [[Write intentions spec]] — P0
2. [ns-pqr] [[Implement /intend command]] — P1
```

**Guidance for building Next actions**:

- Show up to 3-5 ready tasks per intention, highest priority first
- Include brief context: what this task advances or unblocks
- For blockers: show what they block (count of downstream tasks)
- If an intention has deadline tasks due today, lead with those (DEADLINE TODAY format)

**Outside Intentions section**: After all intentions, add items that need attention but are NOT in any intention subgraph:

```markdown
### Outside Intentions

**SHOULD**: [ns-stu] [[Reply to ethics committee]] — 2 days overdue, external
**QUICK**: [ns-vwx] [[Approve PR #847]] — 5 min, maintenance
```

Use the same SHOULD/QUICK/UNBLOCK judgment as Steps 3.2-3.3, but only for tasks outside all intention subgraphs. Keep this section brief (3-5 items max). Focus on: overdue items, deadline items, items blocking in-progress work.

**Priority bars**: Move to a collapsed `<details>` block after the intention summary. Each row uses the total number of actionable tasks at that priority level as its denominator (i.e., filled = done tasks at that priority / total actionable tasks at that priority — not the total across all priorities):

```markdown
<details>
<summary>Priority distribution</summary>

P0 ██████████ 3/3
P1 ██████░░░░ 12/20
P2 ██████████ 55/55
P3 ████░░░░░░ 15/32

</details>
```

Then continue to Step 3.4i.

### 3.4i: Check In on Intentions

When intentions are active, remind the user what their current intentions are (label + progress bar for each), then ask:

```
AskUserQuestion: "How are your intentions going? Any shifts in what you want to focus on?"
Options: "On track" | "Shift focus" | "Out of sync" | "Need a reset"
```

**If "Shift focus"**: Suggest `/intend` to declare, complete, or replace intentions. Return to daily planning after.

**If "On track"**: The intention-organized Focus is already on screen. Wait for user to state any additional priorities. Record in `### My priorities`.

Other responses handled same as Step 3.4.

After recording priorities: continue to section 4 (progress sync). After section 5 completes, output: "Daily planning complete. Use `/pull` to start work on your intentions."

### 3.2: Build Focus Section

_(Used only when no intentions are active.)_

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

_(Used only when no intentions are active.)_

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

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### 3.4: Check In and Engage User on Priorities

_(Used only when no intentions are active.)_

After presenting recommendations, check in with the user:

```
AskUserQuestion: "How are you feeling about your workstreams? Do the task statuses look accurate, or do things feel out of sync?"
Options: "Looks right" | "Out of sync" | "Need a reset"
```

**If "Out of sync"**: Walk through active workstreams with the user. For each, verify task statuses using `AskUserQuestion` batching: present 3–4 related tasks per question (including id, title, and current status) for fast triage, then apply the user's updates and continue until the active workstreams are in sync. Update the graph before continuing.

**If "Need a reset"**: Suggest `/strategy` session instead of continuing daily planning.

**If "Looks right"**: The recommendations are already on screen. Simply wait for the user to state their priorities for the day. Do NOT ask "What sounds right for today?".

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

When user picks, use `mcp__pkb__update_task(id="<id>", status="cancelled")` to archive.
