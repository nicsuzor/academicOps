---
name: daily
category: instruction
description: Daily note lifecycle - briefing, task recommendations, progress sync, and work summary. SSoT for daily note structure.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move
version: 2.0.0
permalink: skills-daily
---

# Daily Note Skill

Manage daily note lifecycle: briefing, task recommendations, progress sync, and work summary.

Location: `$ACA_SESSIONS/YYYYMMDD-daily.md`

## CRITICAL BOUNDARY: Planning Only

**This skill is for PLANNING, not EXECUTION.**

- `/daily` captures priorities in the daily note
- `/daily` does NOT execute tasks, even if user states priorities
- When user answers "what sounds right for today?" → record in Focus section, then COMPLETE
- After daily note is updated: output "Daily planning complete. Use `/pull` to start work." and HALT

**User stating a priority ≠ authorization to execute that priority.**

## Invocation

Every `/daily` invocation runs the **full pipeline** and updates the daily note in place. There are no separate modes — the skill is designed to be run repeatedly throughout the day.

```
/daily          # Run full pipeline (create note if missing, then update everything)
/daily sync     # Alias — same behavior, kept for muscle memory
```

**Pipeline**: 1 (create if missing) → 2 (email briefing) → 3 (focus & recommendations) → 4 (progress sync & merged PRs) → 5 (work summary)

**Idempotent updates**: Each section is updated in place using the Edit tool. User-written content is **never deleted**:

- **Purely machine sections** (Task Tree, Session Log, Session Timeline, Merged PRs): fully replaced on each run
- **Mixed sections** (Focus, FYI, Project Accomplishments): machine content is regenerated above a `<!-- user notes -->` marker; anything the user writes below that marker is preserved
- **User sections** (any section/text the user adds that isn't in the template): left untouched entirely

**Incremental data handling**: Email triage skips already-processed emails (cross-ref against FYI section + sent mail). Session sync skips already-processed session JSONs (cross-ref against Session Log table). Merged PR listing always refreshes from GitHub API.

## Section Ownership

| Section                 | Owner    | Updated By                                  |
| ----------------------- | -------- | ------------------------------------------- |
| Focus                   | `/daily` | Task data + user priorities (mixed)         |
| Task Tree               | `/daily` | Task hierarchy snapshot (machine)           |
| Today's Story           | `/daily` | Synthesis from merges + sessions + tasks    |
| FYI                     | `/daily` | Email triage (mixed)                        |
| Merged PRs              | `/daily` | GitHub API query (machine)                  |
| Session Log/Timeline    | `/daily` | Session JSON synthesis (machine)            |
| Project Accomplishments | `/daily` | Session JSON synthesis (mixed)              |
| Reflection              | `/daily` | Goals vs achieved analysis (machine)        |
| Abandoned Todos         | `/daily` | End-of-day (user)                           |

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers in generated content (only valid in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax (e.g., `[[Greg Austin]]`, `[[academicOps]]`)
3. **Task IDs**: Always include task IDs when referencing tasks (e.g., `[ns-abc] Task title`)

## 1. Create note

Check `$ACA_SESSIONS/YYYYMMDD-daily.md`.

**If exists**: Skip to section 2. The note is updated in place.

**If missing**: Create from template (see [[references/note-template]]), then:

1. Read the previous working day's daily note
2. Identify task IDs from yesterday's Focus/Carryover sections
3. **Verify each task exists** (Step 1.1 below)
4. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
5. Note overdue items from yesterday's Focus Dashboard

### 1.1: Verify Carryover Tasks (CRITICAL)

**Before including ANY task from yesterday's note in today's carryover:**

```python
for task_id in yesterday_task_ids:
    result = mcp__plugin_aops-core_task_manager__get_task(id=task_id)
    if not result["success"]:
        # Task was archived/deleted - EXCLUDE from carryover
        continue
    if result["task"]["status"] in ["done", "cancelled"]:
        # Task completed - EXCLUDE from carryover
        continue
    # Task still active - include in carryover
    carryover_tasks.append(result["task"])
```

**Why this matters**: Tasks archived between daily notes appear as "phantom overdue" items if copied blindly from yesterday's note. Always verify against the live task system.

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

**Incremental**: Also cross-reference against the existing FYI section in today's note. If an email thread is already summarised there, skip it.

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

1. **If action required** (feedback, review, response, decision) → `mcp__plugin_aops-core_task_manager__create_task()` NOW
   - Include deadline if mentioned or implied
   - **Then add task link to FYI content**: `- **→ Task**: [task-id] Task title`
2. **If links to existing task** → `mcp__plugin_aops-core_task_manager__update_task()` with the info
3. **If worth future recall** → `mcp__memory__store_memory()` with tags

Do NOT batch these to a later step. Task creation happens AS you process each email, not after.

**Archive flow (user confirmation required)**:

1. Present FYI content in daily note (complete section 2.2)
2. **DO NOT offer to archive yet** - user needs time to read and process the content
3. **Wait for user signal** - user will indicate when they've read the content (e.g., responds to the briefing, asks a question, or says "ok" / "got it")
4. Only AFTER user has acknowledged the content, use `AskUserQuestion` to ask which to archive
5. Exception: Obvious spam (promotional, irrelevant newsletters) can be offered for archive immediately

**Archiving emails**: Use `messages_move` with `folder_path="Archive"` (not "Deleted Items" - that's trash, not archive). If the Archive folder doesn't exist for an account, ask the user which folder to use.

**Empty state**: If no new FYI emails, leave existing FYI content unchanged.

### 2.3: Verify FYI Persistence (Checkpoint)

Before moving to section 3, verify you completed the inline persistence from 2.2:

- [ ] Each action-requiring FYI has a task created
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

## 4. Daily progress sync

Update daily note from session JSON files and GitHub merge data.

### Step 4.1: Find Session JSONs

```bash
ls $ACA_SESSIONS/summaries/YYYYMMDD*.json 2>/dev/null
```

**Incremental filtering**: After listing JSONs, read the current daily note's Session Log table. Extract session IDs already present. Filter the JSON list to exclude already-processed sessions. This prevents duplicate entries on repeated syncs.

### Step 4.1.5: Load Closure History

Fetch recently completed tasks to provide context for today's story synthesis:

```python
mcp__plugin_aops-core_task_manager__list_tasks(status="done", limit=20)
```

**Purpose**: Completed tasks represent work that may not appear in session JSONs. This context enriches the daily narrative.

**Extract from completed tasks**:

- Issue ID, title, and project
- Closure date
- Brief description if available

**Deduplication**: Closed issues that also appear as session accomplishments should be mentioned once (prefer session context which has richer detail).

### Step 4.2: Load and Merge Sessions

Read each session JSON. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics
- Framework feedback: workflow_improvements, jit_context_needed, context_distractions, user_mood

### Step 4.2.5: Query Merged PRs

Fetch today's merged PRs from the current repository:

```bash
gh pr list --state merged --json number,title,author,mergedAt,headRefName,url --limit 50 2>/dev/null
```

**Post-filter**: From the JSON output, filter to PRs where `mergedAt` falls on today's date (YYYY-MM-DD).

**Format in daily note** (fully replace the `## Merged PRs` section):

```markdown
## Merged PRs

| PR | Title | Author | Merged |
|----|-------|--------|--------|
| [#123](url) | Fix authentication bug | @nicsuzor | 10:15 |
| [#124](url) | Add daily skill merge review | @claude-for-github[bot] | 14:30 |

*N PRs merged today*
```

**Empty state**: If no PRs merged today:

```markdown
## Merged PRs

No PRs merged today.
```

**Error handling**: If `gh` CLI is unavailable or authentication fails, skip this section and note "GitHub CLI unavailable — skipped merge review" in the section.

### Step 4.3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

### Step 4.4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Session Log**: Add/update session entries (fully replace table).

**Session Timeline**: Build from conversation_flow timestamps (fully replace table).

**Project Accomplishments**: Add `[x]` items under project headers. Preserve any user-added notes below items.

**Progress metrics** per project:

- **Scheduled**: Tasks with `scheduled: YYYY-MM-DD` matching today
- **Unscheduled**: Accomplishments not matching scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`

### Step 4.4.5: Generate Goals vs. Achieved Reflection

If the daily note contains a goals section (e.g., "## Things I want to achieve today", "## Focus", "### My priorities"), generate a reflection comparing stated intentions against actual outcomes.

**For each stated goal/priority**:

1. Check if corresponding work appears in session accomplishments
2. Check if related tasks were completed (from Step 4.1.5)
3. Classify as: Achieved | Partially/Spawned | Not achieved

**Generate reflection section**:

```markdown
## Reflection: Goals vs. Achieved

**Goals from "[section name]":**

| Goal     | Status       | Notes                               |
| -------- | ------------ | ----------------------------------- |
| [Goal 1] | Achieved     | Completed in session [id]           |
| [Goal 2] | Partially    | Task created but no completion data |
| [Goal 3] | Not achieved | No matching work found              |

**Unplanned work that consumed the day:**

- [Major unplanned item] (~Xh) - [brief explanation]

**Key insight**: [One-sentence observation about drift, priorities, or patterns]
```

### Step 4.5: Task Matching (Session → Task Sync)

Match session accomplishments to related tasks using semantic search.

**4.5.1: Search for Candidate Tasks**

For each accomplishment from session JSONs:

```python
# Semantic search via memory server
candidates = mcp__memory__retrieve_memory(
    query=accomplishment_text,
    limit=5,
    similarity_threshold=0.6
)
```

**4.5.2: Agent-Driven Matching Decision**

For each accomplishment with candidates:

1. **High confidence match** (agent is certain):
   - Action: Update task file (Step 4.6) + add task link to daily.md

2. **Low confidence match** (possible but uncertain):
   - Action: Note in daily.md as "possibly related to [[task]]?" - NO task file update

3. **No match** (no relevant candidates):
   - Action: Continue to next accomplishment

**Matching heuristics**:

- Prefer no match over wrong match (conservative)
- Consider task title, body, project alignment

**4.5.3: Graceful Degradation**

| Scenario                  | Behavior                                    |
| ------------------------- | ------------------------------------------- |
| Memory server unavailable | Skip semantic matching, continue processing |
| Task file not found       | Log warning, continue to next               |
| Unexpected task format    | Skip that task, log warning                 |

### Step 4.6: Update Task Files (Cross-Linking)

For each **high-confidence match** from Step 4.5:

**4.6.1: Update Task Checklist**

If accomplishment matches a specific checklist item in the task:

```markdown
# Before
- [ ] Implement feature X

# After
- [x] Implement feature X [completion:: 2026-01-19]
```

**Constraints**:

- Mark sub-task checklist items complete
- NEVER mark parent tasks complete automatically
- NEVER delete any task content

**4.6.2: Append Progress Section**

Add progress note to task file body:

```markdown
## Progress

- 2026-01-19: [accomplishment text]. See [[sessions/20260119-daily.md]]
```

If `## Progress` section exists, append to it. Otherwise, create it at end of task body.

**4.6.3: Update Daily.md Cross-Links**

In the Project Accomplishments section, add task links:

```markdown
### [[academicOps]] → [[projects/aops]]

- [x] Implemented session-sync → [[tasks/inbox/ns-whue-impl.md]]
- [x] Fixed authentication bug (possibly related to [[tasks/inbox/ns-abc.md]]?)
- [x] Added new endpoint (no task match)
```

### Step 4.7: Update synthesis.json

Write `$ACA_DATA/dashboard/synthesis.json`:

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "sessions": {
    "total": N,
    "by_project": {"aops": 2, "writing": 1},
    "recent": [{"session_id": "...", "project": "...", "summary": "..."}]
  },
  "narrative": ["Session summary 1", "Session summary 2"],
  "accomplishments": {
    "count": N,
    "summary": "brief text",
    "items": [{"project": "aops", "item": "Completed X"}]
  },
  "merged_prs": {
    "count": N,
    "items": [{"number": 123, "title": "...", "author": "..."}]
  },
  "next_action": {"task": "P0 task", "reason": "Highest priority"},
  "alignment": {"status": "on_track|blocked|drifted", "note": "..."},
  "waiting_on": [{"task": "...", "blocker": "..."}],
  "skill_insights": {
    "compliance_rate": 0.75,
    "top_context_gaps": [],
    "workflow_improvements": [],
    "jit_context_needed": [],
    "context_distractions": [],
    "avg_user_tone": 0.0
  },
  "session_timeline": [{"time": "10:15", "session": "...", "activity": "..."}]
}
```

## 5. Work Summary

After progress sync, generate a brief natural language summary of the day's work. This is the **key output** that the user sees both in the daily note and in the terminal.

### Step 5.1: Gather Inputs

Collect from the sections already populated:

- **Merged PRs** (from Step 4.2.5): titles and count
- **Session accomplishments** (from Step 4.2): what was done in each session
- **Completed tasks** (from Step 4.1.5): tasks closed today
- **Focus goals** (from `### My priorities`): what the user intended to do

### Step 5.2: Generate Today's Story

Write a 2-4 sentence natural language summary to the `## Today's Story` section. This replaces (not appends to) the existing Today's Story content.

**Style guide**:

- Write in past tense, first person plural or third person ("Merged 3 PRs..." / "The day focused on...")
- Lead with the most impactful work, not chronological order
- Mention specific PR numbers and task IDs for traceability
- Note any significant merges, completions, or milestones
- If goals were set in Focus, note alignment or drift briefly

**Example**:

```markdown
## Today's Story

Consolidated the PR review and merge workflows into a single pipeline (#415), fixing the broken LGTM merge trigger. Updated the daily skill to include GitHub merge tracking and natural language summaries. Three PRs merged today, all related to the academicOps framework infrastructure push. Focus stayed on framework work despite planning to tackle the OSB review — that carries to tomorrow.
```

### Step 5.3: Terminal Briefing Output

After updating the daily note, output a concise briefing to the terminal:

```
## Daily Summary

[Today's Story text from 5.2]

**Merged today**: N PRs (#123, #124, #125)
**Sessions**: N across [projects]
**Tasks completed**: N

Daily note updated at [path].
Daily planning complete. Use `/pull` to start work.
```

This gives the user a quick snapshot without needing to open the note.

## Error Handling

- **Outlook unavailable**: Skip email triage, continue with recommendations
- **GitHub CLI unavailable**: Skip merged PR listing, note in section
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`
- **Memory server unavailable**: Skip semantic task matching (Step 4.5), continue with daily.md updates
- **Task file not found**: Log warning "Task file missing: {path}", continue to next accomplishment
- **Unexpected task format**: Log warning "Skipping task {id}: unexpected format", continue processing

## Daily Note Structure (SSoT)

See [[references/note-template]] for the complete daily note template.
