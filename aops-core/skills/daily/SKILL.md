---
name: daily
category: instruction
description: Daily note lifecycle - morning briefing, task recommendations, session sync. SSoT for daily note structure.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move
version: 1.0.0
permalink: skills-daily
---

# Daily Note Skill

Manage daily note lifecycle: morning briefing, task recommendations, and session sync.

## Path Resolution

**CRITICAL**: This skill requires the `$ACA_DATA` environment variable to be set.

- `$ACA_DATA` points to the user's data directory (contains daily notes, tasks, etc.)

Location: `$ACA_DATA/daily/YYYYMMDD-daily.md`

## CRITICAL BOUNDARY: Planning Only

**This skill is for PLANNING, not EXECUTION.**

- `/daily` captures priorities in the daily note
- `/daily` does NOT execute tasks, even if user states priorities
- When user answers "what sounds right for today?" → record in Focus section, then COMPLETE
- After daily note is updated: output "Daily planning complete. Use `/pull` to start work." and HALT

**User stating a priority ≠ authorization to execute that priority.**

## Invocation Modes

The daily skill integrates sync into every run to keep the daily note current:

| Mode          | Trigger                          | Sections Run              | User Approval  |
| ------------- | -------------------------------- | ------------------------- | -------------- |
| **Morning**   | `/daily` (no args, note missing) | 1 → 2 → 3 → 4 (auto-sync) | Required (3.4) |
| **Refresh**   | `/daily` (note exists)           | 2 → 3 → 4 (auto-sync)     | Required (3.4) |
| **Full Sync** | `/daily sync`                    | 4 only                    | Required (4.8) |

**Mode Detection Logic:**

```
if args contains "sync":
    mode = "Full Sync"  # Explicit sync-only with approval
elif daily_note_exists():
    mode = "Refresh"    # Briefing update + auto-sync
else:
    mode = "Morning"    # Full creation + auto-sync
```

**Auto-Sync Behavior**: When running Morning or Refresh modes, sync (section 4) runs automatically after section 3 completes. Auto-sync skips the approval step (4.8) to avoid interrupting the flow. Session data is processed and merged silently.

**Full Sync Use Case**: Run `/daily sync` explicitly when you want:

- End-of-day synthesis with user approval of the narrative
- To verify/correct auto-synced content
- To process sessions without re-running email triage

## Section Ownership

| Section                 | Owner    | Updated By                              |
| ----------------------- | -------- | --------------------------------------- |
| Focus                   | `/daily` | Morning briefing + task recommendations |
| Task Tree               | `/daily` | Task hierarchy snapshot                 |
| Today's Story           | `/daily` | Session JSON synthesis                  |
| FYI                     | `/daily` | Email triage                            |
| Session Log/Timeline    | `/daily` | Session JSON synthesis                  |
| Project Accomplishments | `/daily` | Session JSON synthesis                  |
| Reflection              | `/daily` | End-of-day sync (Step 4.4.5)            |
| Abandoned Todos         | `/daily` | End-of-day                              |

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers in generated content (only valid in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax (e.g., `[[Greg Austin]]`, `[[academicOps]]`)
3. **Task IDs**: Always include task IDs when referencing tasks (e.g., `[ns-abc] Task title`)

## 1. Create note

Check `$ACA_DATA/daily/YYYYMMDD-daily.md`.

**If missing**: Create from template (see Daily Note Structure above), then:

1. Read the previous working day's daily note
2. Identify any incomplete tasks and copy to "## Carryover from Yesterday" section
3. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
4. Note overdue items from yesterday's Focus Dashboard

### 1.2: Load Recent Activity

Read last 3 daily notes to show project activity summary:

- Which projects had work recently
- Current state/blockers per project

## 2. Update daily briefing

### 2.0: Load User Context for Email Classification

Before classifying emails, load domain context to filter by relevance:

```bash
Read $ACA_DATA/CORE.md        # User profile, research focus
Read $ACA_DATA/context/strategy.md  # Active projects and domains
```

**Use this context during classification**: Emails about funding, CFPs, conferences, or opportunities OUTSIDE the user's research domains should be classified as **Skip** (domain-irrelevant), not FYI. The user's domains are visible in strategy.md under "Projects" and "Strategic Logic Model".

### 2.1: Email Triage

Fetch recent emails via Outlook MCP:

```
mcp__outlook__messages_list_recent(limit=50, folder="inbox")
```

**CRITICAL - Check sent mail FIRST**: Before classifying ANY inbox email, you MUST fetch sent mail and cross-reference to avoid flagging already-handled items:

```
mcp__outlook__messages_list_recent(limit=20, folder="sent")
```

**For EACH inbox email**: Compare subject line (ignoring Re:/Fwd: prefixes) against sent mail subjects. If a matching sent reply exists, classify as **Skip** (already handled). This cross-reference is MANDATORY - skipping it causes duplicate task creation.

**Classify each email** using [[workflows/triage-email]] criteria (LLM semantic classification, not keyword matching).

### 2.2: FYI Content in Daily Note

**Goal**: User reads FYI content in the daily note itself, not by opening emails.

**Thread grouping**: Group emails by conversation thread (same subject minus Re:/Fwd:). Present threads as unified summaries, not individual emails.

**For each FYI thread/item**, fetch full content with `mcp__outlook__messages_get` and include:

- Thread participants and who said what (if multiple contributors)
- **Actual content**: The key information - quote directly for short emails, summarize for long ones

**Format in briefing**:

```markdown
## FYI

### [Thread Topic]

[Participants] discussed [topic]. [Key content/decision/info].

> [Direct quote if short]

### [Single Email Topic]

From [sender]: [Actual content or summary]
```

**CRITICAL - For each FYI item, IMMEDIATELY after writing it:**

1. **If action required** (feedback, review, response, decision, "review X before Y") → `mcp__plugin_aops-core_task_manager__create_task()` NOW
   - Include deadline if mentioned or implied (e.g., "before Planning Day" = Planning Day date)
   - **Then add task link to FYI content**: `- **→ Task**: [task-id] Task title`
2. **If links to existing task** → `mcp__plugin_aops-core_task_manager__update_task()` with the info
3. **If worth future recall** → `mcp__memory__store_memory()` with tags

Do NOT batch these to a later step. Task creation AND linking happens AS you process each email, not after.

**Archive flow (user confirmation required)**:

1. Present FYI content in daily note (complete section 2.2)
2. **DO NOT offer to archive yet** - user needs time to read and process the content
3. **Wait for user signal** - user will indicate when they've read the content (e.g., responds to the briefing, asks a question, or says "ok" / "got it")
4. Only AFTER user has acknowledged the content, use `AskUserQuestion` to ask which to archive
5. Exception: Obvious spam (promotional, irrelevant newsletters) can be offered for archive immediately

**Archiving emails**: Use `messages_move` with `folder_path="Archive"` (not "Deleted Items" - that's trash, not archive). If the Archive folder doesn't exist for an account, ask the user which folder to use.

**Empty state**: If no FYI emails, skip this section.

### 2.3: Verify FYI Persistence (Checkpoint)

Before moving to section 3, verify you completed the inline persistence from 2.2:

- [ ] Each action-requiring FYI has a task created
- [ ] Each created task is linked back in the FYI section (`→ Task: [id]`)
- [ ] Relevant existing tasks updated with new info
- [ ] High-value FYI items stored in memory

**Rule**: Information captured but not persisted is information lost. Daily note is ephemeral; memory and tasks are durable.

If you skipped any, go back and create tasks NOW before proceeding.

## 3. Today's Focus

Populate the `## Focus` section with priority dashboard and task recommendations. This is the FIRST thing the user sees after frontmatter.

### 3.1: Load Task Data

```python
mcp__plugin_aops-core_task_manager__list_tasks(limit=100)
```

Parse task data from output to identify:

- Priority distribution (P0/P1/P2/P3 counts)
- Overdue tasks (negative days_until_due)
- Today's work by project
- Blocked tasks

### 3.1.5: Generate Task Tree

After loading task data, generate the ASCII task tree for the `## Task Tree` section:

```python
mcp__plugin_aops-tools_task_manager__get_task_tree(
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

# Get topology for blocking counts
topology = mcp__plugin_aops-core_task_manager__get_tasks_with_topology()

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

### 3.4: Engage User on Priorities

After presenting recommendations, use `AskUserQuestion` to confirm priorities:

- "What sounds right for today?"
- Offer to adjust recommendations based on user context

**IMPORTANT**: User's response states their PRIORITY for the day. This goes into the daily note's Focus section. It is NOT a command to execute those tasks. After recording the priority:

1. Update the Focus section with user's stated priority
2. Run auto-sync (Section 4, steps 4.1-4.7) to update daily note with session progress
3. Output: "Daily planning complete. Use `/pull` to start work."
4. HALT - do not proceed to task execution

### 3.5: Present candidate tasks to archive

```
- [ns-xyz] **[[Stale Task]]** - [reason: no activity in X days]
```

Ask: "Any of these ready to archive?"

When user picks, use `mcp__plugin_aops-core_task_manager__update_task(id="<id>", status="cancelled")` to archive.

### 4. Daily progress (Sync)

**See [[instructions/sync-workflow.md]] for complete sync workflow (Steps 4.1-4.8).**

Summary: Update daily note from session JSON files. Auto-sync runs as part of Morning/Refresh modes; Full sync (`/daily sync`) requires user approval.

## Error Handling

- **Outlook unavailable**: Skip email triage, continue with recommendations
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`
- **Memory server unavailable**: Skip semantic task matching (Step 4.5), continue with daily.md updates
- **Task file not found**: Log warning "Task file missing: {path}", continue to next accomplishment
- **Unexpected task format**: Log warning "Skipping task {id}: unexpected format", continue processing

## Daily Note Structure (SSoT)

See the note template at `aops-core/skills/daily/references/note-template.md` (relative to $AOPS)
or `[[references/note-template]]` (Obsidian wikilink) for the complete daily note template.
