# Daily Note: Progress Sync

## 4. Daily progress sync

Update daily note from session JSON files and narrative path reconstruction.

### Step 4.1: Narrative Path Reconstruction (Compass Model)

Instead of a mechanical table, build a narrative timeline of the day's work using the `show_path.py` script. This helps the user recover context and identify "where they are" in the day's story.

```bash
uv run python3 aops-core/scripts/show_path.py --hours 24
```

**Format in daily note** (fully replace the `## Session Timeline` section):

Use the script output to create a "Today's Path" section grouped by project. Each project should show the threads of work, starting with the session goal/intent and listing key actions (Created, Finished, Claimed) in narrative format.

### Step 4.1.5: Load Closure History

Fetch recently completed tasks to provide context for today's story synthesis:

```python
mcp__pkb__list_tasks(status="done", limit=20)
```

**Purpose**: Completed tasks represent work that may not appear in session JSONs. This context enriches the daily narrative.

**Extract from completed tasks**:

- Issue ID, title, and project
- Closure date
- Brief description if available

**Deduplication**: Closed issues that also appear as session accomplishments should be mentioned once (prefer session context which has richer detail).

### Step 4.2: Load and Merge Sessions

Read each session JSON from `$ACA_SESSIONS/summaries/YYYYMMDD*.json`. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics
- Framework feedback: workflow_improvements, jit_context_needed, context_distractions, user_mood

**Incremental filtering**: After listing JSONs, read the current daily note's Session Log table. Extract session IDs already present. Filter the JSON list to exclude already-processed sessions. This prevents duplicate entries on repeated syncs.

### Step 4.2.5: Query Merged PRs

... (rest of the file) ...

Fetch today's merged PRs from the current repository:

```bash
gh pr list --state merged --json number,title,author,mergedAt,headRefName,url --limit 50 2>/dev/null
```

**Post-filter**: From the JSON output, filter to PRs where `mergedAt` falls on today's date (YYYY-MM-DD).

**Format in daily note** (fully replace the `## Merged PRs` section):

```markdown
## Merged PRs

| PR          | Title                        | Author                  | Merged |
| ----------- | ---------------------------- | ----------------------- | ------ |
| [#123](url) | Fix authentication bug       | @nicsuzor               | 10:15  |
| [#124](url) | Add daily skill merge review | @claude-for-github[bot] | 14:30  |

_N PRs merged today_
```

**Empty state**: If no PRs merged today:

```markdown
## Merged PRs

No PRs merged today.
```

**Error handling**: If `gh` CLI is unavailable or authentication fails, skip this section and note "GitHub CLI unavailable — skipped merge review" in the section.

### Step 4.2.6: Open PR Review (Decision Queue)

Fetch open PRs that need human decisions — approvals, problem triage, or closure:

<!-- NS: this needs to be made aware of our repo map, currently stored at ~/.aops/polecat.yaml -->

```bash
gh pr list --state open --json number,title,author,createdAt,headRefName,url,isDraft,reviewDecision,statusCheckRollup --limit 30 2>/dev/null
```

**For each open PR**, summarize:

- PR number, title, author
- Whether CI is passing, failing, or pending
- Whether reviews are blocking (CHANGES_REQUESTED) or clear
- One-line description of what the PR does (from title + branch name)
- Any problems that need attention (failing checks, conflicts, stale)

**Format in daily note** (fully replace the `## Open PRs` section):

```markdown
## Open PRs

| PR          | Title                | Author     | CI      | Reviews | Action needed    |
| ----------- | -------------------- | ---------- | ------- | ------- | ---------------- |
| [#639](url) | Fix failing pytests  | @nicsuzor  | pending | clear   | re-trigger CI    |
| [#630](url) | Fix crontab paths    | @nicsuzor  | failing | clear   | fix type check   |
| [#640](url) | Add extraction skill | @botnicbot | skipped | pending | review + approve |

_N open PRs — M need action_
```

**Decision-oriented**: The "Action needed" column is the key output. Classify each:

- **approve** — CI green, reviews clear, ready to merge
- **review + approve** — needs human review before merge
- **fix [issue]** — specific problem blocking merge
- **re-trigger CI** — checks didn't run or are stale
- **close** — draft/stale/superseded, suggest closing
- **waiting** — blocked on external dependency, nothing to do now

**Empty state**: If no open PRs: "No open PRs."

**Error handling**: If `gh` CLI is unavailable, use GitHub API via curl as fallback. If both fail, skip and note "GitHub unavailable — skipped open PR review."

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
# Semantic search via PKB
candidates = mcp__pkb__search(
    query=accomplishment_text,
    limit=5
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

| Scenario               | Behavior                                    |
| ---------------------- | ------------------------------------------- |
| PKB unavailable        | Skip semantic matching, continue processing |
| Task file not found    | Log warning, continue to next               |
| Unexpected task format | Skip that task, log warning                 |

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

- 2026-01-19: [accomplishment text]. See [[daily/20260119-daily.md]]
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
