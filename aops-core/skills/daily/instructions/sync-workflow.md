# Daily Progress Sync Workflow

Update daily note from session JSON files.

**Invocation**:
- **Auto-sync**: Runs automatically as part of Morning/Refresh modes (steps 4.1-4.7, skips 4.8 approval)
- **Full sync**: `/daily sync` runs section 4 only with user approval (4.8)

**Incremental behavior**: Each sync run is additive—it processes only NEW session JSONs since the last sync. Previously processed sessions are identified by their presence in the Session Log table.

## Step 4.1: Find Session JSONs

```bash
ls $ACA_DATA/../sessions/summaries/YYYYMMDD*.json 2>/dev/null
```

**Incremental filtering**: After listing JSONs, read the current daily note's Session Log table. Extract session IDs already present. Filter the JSON list to exclude already-processed sessions. This prevents duplicate entries on repeated syncs.

## Step 4.1.5: Load Closure History

Fetch recently completed tasks to provide context for today's story synthesis:

```python
mcp__plugin_aops-core_task_manager__list_tasks(status="done", limit=20)
```

**Purpose**: Completed tasks represent work that may not appear in session JSONs (e.g., tasks completed in previous sessions, or completed without a dedicated session). This context enriches the daily narrative.

**Extract from completed tasks**:

- Issue ID, title, and project
- Closure date
- Brief description if available

**Deduplication**: Closed issues that also appear as session accomplishments should be mentioned once (prefer session context which has richer detail).

## Step 4.2: Load and Merge Sessions

Read each session JSON. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics
- Framework feedback: workflow_improvements, jit_context_needed, context_distractions, user_mood

## Step 4.3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

## Step 4.4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Today's Story**: Synthesize narrative from session summaries AND closed issues.

- Format in dot points, but use prose to provide detail
- Include recently closed issues from Step 4.1.5 as context (e.g., "Closed [ns-xyz] completing the X feature")
- Deduplicate: If a closed issue also appears as a session accomplishment, mention it once with session context

**Session Log**: Add/update session entries.

**Session Timeline**: Build from conversation_flow timestamps.

**Project Accomplishments**: Add `[x]` items under project headers.

**Progress metrics** per project:

- **Scheduled**: Tasks with `scheduled: YYYY-MM-DD` matching today
- **Unscheduled**: Accomplishments not matching scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`

## Step 4.4.5: Generate Goals vs. Achieved Reflection

If the daily note contains a goals section (e.g., "## Things I want to achieve today", "## Focus", or similar), generate a reflection comparing stated intentions against actual outcomes.

**Check for goals section**: Look for sections like:
- `## Things I want to achieve today`
- `## Focus` (the task recommendations from morning planning)
- `## Today's Work Queue` (scheduled tasks)

**For each stated goal/priority**:
1. Check if corresponding work appears in session accomplishments
2. Check if related tasks were completed (from Step 4.1.5)
3. Classify as: Achieved | Partially/Spawned | Not achieved

**Generate reflection section**:

```markdown
## Reflection: Goals vs. Achieved

**Goals from "[section name]":**

| Goal | Status | Notes |
|------|--------|-------|
| [Goal 1] | Achieved | Completed in session [id] |
| [Goal 2] | Partially | Task created but no completion data |
| [Goal 3] | Not achieved | No matching work found |

**Unplanned work that consumed the day:**
- [Major unplanned item] (~Xh) - [brief explanation]

**Key insight**: [One-sentence observation about drift, priorities, or patterns]
```

**Purpose**: This reflection reveals intention drift and helps understand why plans diverge from reality. Tracking "unplanned work that consumed the day" explains goal displacement.

## Step 4.5: Task Matching (Session -> Task Sync)

Match session accomplishments to related tasks using semantic search.

**Per spec** ([[session-sync-user-story]]): The agent receives accomplishments + candidate task files and decides which tasks match. Agent-driven matching, NOT algorithmic.

### 4.5.1: Search for Candidate Tasks

For each accomplishment from session JSONs:

```python
# Semantic search via memory server
candidates = mcp__memory__retrieve_memory(
    query=accomplishment_text,
    limit=5,
    similarity_threshold=0.6
)
```

### 4.5.2: Agent-Driven Matching Decision

For each accomplishment with candidates:

1. **High confidence match** (agent is certain):
   - Accomplishment clearly relates to a specific task
   - Example: "Implemented session-sync" matches task "Add session-end sync feature"
   - Action: Update task file (Step 4.6) + add task link to daily.md

2. **Low confidence match** (possible but uncertain):
   - Accomplishment might relate to a task but agent is unsure
   - Action: Note in daily.md as "possibly related to [[task]]?" - NO task file update

3. **No match** (no relevant candidates):
   - Accomplishment in daily.md only, no link
   - Action: Continue to next accomplishment

**Matching heuristics**:
- Prefer no match over wrong match (conservative)
- Consider task title, body, project alignment
- "Implemented X" accomplishment matches "Add X feature" or "X" task
- Framework work -> framework tasks; project work -> project tasks

### 4.5.3: Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Memory server unavailable | Skip semantic matching, continue processing |
| Task file not found | Log warning, continue to next |
| Unexpected task format | Skip that task, log warning |

## Step 4.6: Update Task Files (Cross-Linking)

For each **high-confidence match** from Step 4.5:

### 4.6.1: Update Task Checklist

If accomplishment matches a specific checklist item in the task:

```markdown
# Before
- [ ] Implement feature X

# After
- [x] Implement feature X [completion:: 2026-01-19]
```

Use Edit tool to add `[x]` and `[completion:: YYYY-MM-DD]`.

**Constraints**:
- Mark sub-task checklist items complete
- NEVER mark parent tasks complete automatically
- NEVER delete any task content

### 4.6.2: Append Progress Section

Add progress note to task file body:

```markdown
## Progress

- 2026-01-19: [accomplishment text]. See [[sessions/20260119-daily.md]]
```

If `## Progress` section exists, append to it. Otherwise, create it at end of task body.

### 4.6.3: Update Daily.md Cross-Links

In the Project Accomplishments section, add task links:

```markdown
### [[academicOps]] -> [[projects/aops]]

- [x] Implemented session-sync -> [[tasks/inbox/ns-whue-impl-aggregate-session-insights-to-dailymd.md]]
- [x] Fixed authentication bug (possibly related to [[tasks/inbox/ns-abc-auth-refactor.md]]?)
- [x] Added new endpoint (no task match)
```

## Step 4.7: Update synthesis.json

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

## Step 4.8: User Approval of Synthesis (Full Sync Only)

**Mode check**: Skip this step entirely when running as auto-sync (part of Morning/Refresh modes). Auto-sync processes session data silently without interrupting the flow.

**For Full Sync mode** (`/daily sync`): Do NOT consider daily progress sync complete without user approval.

After updating the daily note and synthesis.json, present a summary to the user for approval:

### 4.8.1: Present Synthesis Summary

Output the key synthesized content for review:

```markdown
## Daily Progress Synthesis - Review Required

**Today's Story** (synthesized narrative):
> [The narrative text from Today's Story section]

**Sessions Processed**: [N] sessions across [projects]

**Accomplishments** ([count] items):
- [First 3-5 accomplishments listed]
- ...

**Task Matches Made**:
- [List of high-confidence task matches, if any]
```

### 4.8.2: Request Approval

Use `AskUserQuestion` to get explicit approval:

```python
AskUserQuestion(
    questions=[{
        "question": "Does this synthesis accurately capture today's progress?",
        "header": "Synthesis",
        "options": [
            {"label": "Looks good", "description": "Synthesis is accurate, proceed to save"},
            {"label": "Needs edits", "description": "I'll make manual corrections to the daily note"},
            {"label": "Regenerate", "description": "Re-run synthesis with different approach"}
        ],
        "multiSelect": false
    }]
)
```

### 4.8.3: Handle Response

| Response | Action |
|----------|--------|
| "Looks good" | Proceed to completion, output "Daily sync complete." |
| "Needs edits" | Output "Daily note ready for your edits at [path]. Run `/daily` again after editing to re-sync." HALT without marking complete. |
| "Regenerate" | Ask what should change, then re-run Steps 4.4-4.7 |

**Rationale**: Per AXIOM #3 (Don't Make Shit Up), Gemini-mined accomplishments may contain inaccuracies. User approval catches hallucinations before they persist in the daily record.
