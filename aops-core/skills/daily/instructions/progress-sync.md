# Daily Note: Progress Sync

## 4. Daily progress sync

Update daily note from session JSON files and narrative path reconstruction.

### Step 4.0: Task Completion Sweep

Before syncing progress, run a sweep of tasks in `merge_ready` and `review` status to synchronize with external signals (merged PRs, sent emails). This ensures the task graph accurately reflects completed, blocked, or stale work.

```bash
polecat sweep
```

**Outcome**: Tasks for merged PRs move to `done`, tasks with requested changes move back to `review`, and stale PRs are flagged.

**Extended sweep** (when `polecat sweep` is unavailable or as a supplement — mirrors SKILL.md Step 7, kept self-contained so it works without the full skill context):

1. Call `list_tasks(status="merge_ready")` and `list_tasks(status="review")` to get all candidate tasks.
2. For tasks with a `pr_url` in frontmatter: query the PR state via `gh pr view <number> --json state,mergedAt,url`. If `state == "MERGED"`, call `complete_task` with the merge timestamp + URL as evidence.
3. For tasks **without** a `pr_url`: match by `headRefName` substring or task ID in PR body against merged PRs fetched in Step 4.2.5. Same auto-complete rule applies.
4. **Sent-email evidence**: For tasks where the completion signal is a sent email (e.g., reply-required tasks from `/email`), cross-reference against recent sent items. Auto-close (using `mcp__pkb__complete_task`) only when the match is unambiguous — same correspondent, subject line matching (using whole-word boundaries), sent after task creation within ~48 hours.
5. **Ambiguous cases**: Surface in the daily note under "Needs your call" in "What Needs Attention" (see [[instructions/workflow-monitor]] Step 6.5). Never auto-close ambiguous cases.
6. **Report** in Work Log: `N tasks auto-closed from merged PRs`, `N tasks auto-closed from sent emails`, `N flagged for user decision`.

**Steps 4.1, 4.1.5, 4.2, 4.2.5, and 4.2.6 — run in parallel.** These data-gathering steps are independent: they read from different sources (shell scripts, PKB, session JSONs, GitHub) and produce separate outputs that are merged only at composition time. Agent teams should dispatch concurrent subagents for each; single-agent environments should issue all data-fetching tool calls simultaneously rather than sequentially.

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

Read each session JSON from `$AOPS_SESSIONS/summaries/YYYYMMDD*.json`. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics
- Framework feedback: workflow_improvements, jit_context_needed, context_distractions, user_mood
- **User prompt count and content**: Count `timeline_events` where `type == "user_prompt"`. Extract the `description` field of each (truncate to ~80 chars). This is the primary signal for human attention cost. If `timeline_events` is absent (older session format) and a `user_prompts` field is present, treat it as a list of `[timestamp, role, text]` entries: count only elements where `role == "user"` and use the `text` element (truncated to ~80 chars) as the prompt content. If neither `timeline_events` nor any `user` entries in `user_prompts` are available, classify engagement as **unknown** and note it in the log rather than defaulting to Autonomous.

**Session engagement classification** (derived from user prompt count):

| Prompts | Classification      | Meaning                                                                                          |
| ------- | ------------------- | ------------------------------------------------------------------------------------------------ |
| 0       | **Autonomous**      | Agent ran without human involvement. High output possible, zero attention cost. Fire-and-forget. |
| 1       | **Dispatched**      | Human kicked it off with a single instruction and moved on. Conductor work.                      |
| 2–3     | **Interactive**     | Human engaged in back-and-forth. Moderate attention.                                             |
| 4+      | **Deep engagement** | Sustained human involvement — debugging, discussing, iterating. Highest attention cost.          |

**Why prompt count, not duration**: A 337-minute autonomous session costs the human nothing. A 5-minute session with 4 prompts is where they were actually thinking. Duration measures agent compute time; prompt count measures human attention.

**Work type classification** (derived from project and prompt content):

| Signal                                                                                                                       | Classification     |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| Prompt mentions research/analysis/paper/methodology/data/literature; or project is tagged as research in ACA_DATA            | **Research**       |
| Prompt mentions teaching, supervision, HDR, marking, student                                                                 | **Academic**       |
| Prompt mentions PR/deploy/CI/infra/config/tooling; or project is framework, tooling, or personal config (tagged in ACA_DATA) | **Infrastructure** |
| Email, calendar, scheduling, admin                                                                                           | **Administrative** |

Use the user's prompt `description` text as the primary signal. Project name is a fallback — check the project's tags or category in ACA_DATA rather than hardcoding names. When ambiguous, prefer research classification — the daily skill's job is to surface research work, not bury it.

**Why this matters**: Session Flow and Today's Story must lead with research sessions. Infrastructure sessions with high output (many PRs, many tasks) are visually impressive but represent lower-significance work. An interactive research session with 4 prompts is the day's headline; 5 autonomous infrastructure sessions are a footnote.

**Incremental filtering**: After listing JSONs, read the current daily note's Session Log table. Extract session IDs already present. Filter the JSON list to exclude already-processed sessions. This prevents duplicate entries on repeated syncs.

### Step 4.2.5: Query Merged PRs

Fetch today's merged PRs from **all tracked repositories** defined in `$POLECAT_HOME/polecat.yaml`.

**Repository discovery**: Read `$POLECAT_HOME/polecat.yaml` to get the project registry. For each project, use the `path` field to `cd` into the repo and run the query. Skip repos that don't exist locally.

**Per-repo query**:

```bash
cd <repo_path> && gh pr list --state merged --json number,title,author,mergedAt,headRefName,url --limit 50 2>/dev/null
```

**Post-filter**: From the JSON output, filter to PRs where `mergedAt` falls on today's date (YYYY-MM-DD).

**Format in daily note** (fully replace the `## Merged PRs` section):

```markdown
## Merged PRs

### academicOps

| PR          | Title                  | Author | Merged |
| ----------- | ---------------------- | ------ | ------ |
| [#123](url) | Fix authentication bug | @user  | 10:15  |

### my-other-project

No PRs merged today.

_N PRs merged today across M repos_
```

**Empty state**: If no PRs merged today across all repos: "No PRs merged today."

**Error handling**: If `gh` CLI is unavailable or authentication fails for a repo, note it inline and continue to the next repo.

### Step 4.2.6: Open PR Review (Decision Queue)

Fetch open PRs that need human decisions from **all tracked repositories** in `$POLECAT_HOME/polecat.yaml`.

**Per-repo query** (use the enriched field set for decision support):

```bash
cd <repo_path> && gh pr list --state open --json number,title,author,createdAt,headRefName,url,isDraft,reviewDecision,statusCheckRollup,additions,deletions,changedFiles,mergeable,body,labels --limit 30 2>/dev/null
```

**For each open PR**, extract and summarize:

- **PR number, title, author** — basic identification
- **Size**: `+additions/-deletions (N files)` — helps gauge review effort
- **Age**: days since `createdAt` — flag PRs older than 7 days as stale
- **CI status**: Derive from `statusCheckRollup` — passing/failing/pending/skipped/no checks. For failing, name the specific check that failed (e.g., "type check failing" not just "failing")
- **Mergeable**: From `mergeable` field — MERGEABLE/CONFLICTING/UNKNOWN. Conflicts are blockers
- **Reviews**: From `reviewDecision` — APPROVED/CHANGES_REQUESTED/empty (pending)
- **Body preview**: First ~100 chars of `body` — gives context for what the PR does
- **Draft status**: From `isDraft` — drafts are lower priority

**Format in daily note** (fully replace the `## Open PRs` section), grouped by repo:

```markdown
## Open PRs

### academicOps (7 open)

| PR          | Title                        | Author | Size           | Age | CI                 | Mergeable | Action                     |
| ----------- | ---------------------------- | ------ | -------------- | --- | ------------------ | --------- | -------------------------- |
| [#631](url) | Agent launch controls in TUI | @agent | +144/-4 (2f)   | 0d  | passing            | conflict  | fix conflicts then merge   |
| [#630](url) | Fix crontab broken paths     | @user  | +149/-34 (6f)  | 0d  | type check failing | conflict  | fix type check + conflicts |
| [#640](url) | Add extraction skill         | @agent | +1048/-17 (6f) | 0d  | skipped            | unknown   | review — large new skill   |

### my-other-project (10 open)

| PR          | Title                   | Author | Size            | Age | CI      | Mergeable | Action                       |
| ----------- | ----------------------- | ------ | --------------- | --- | ------- | --------- | ---------------------------- |
| [#304](url) | Unify processor classes | @user  | +471/-424 (22f) | 74d | failing | conflict  | close or rebase — very stale |

_N open PRs across M repos — X ready to merge, Y need fixes, Z need review_
```

**Decision-oriented**: The "Action" column is the key output. Classify each:

- **merge** — CI green, reviews clear, no conflicts, ready to merge now
- **approve + merge** — CI green, no conflicts, needs human approval then merge
- **review** — needs substantive human review (add brief reason: "large new skill", "architectural change")
- **fix [specific issue]** — name the blocker (e.g., "fix type check", "fix conflicts", "fix lint")
- **trigger CI** — checks didn't run or are stale
- **close or rebase** — stale (>30 days) AND conflicting or superseded by newer work. Age alone is not enough to recommend closing; check if the work is still relevant
- **draft — [context]** — draft PR; describe what it's waiting for. Check the branch name and body for clues (e.g., "sub-PR of #630", "WIP: needs tests"). Never recommend closing a draft just because it's a draft — drafts represent in-progress work
- **waiting** — blocked on external dependency

**PR relationships**: Before classifying, check for relationships between PRs:

- Branch names like `copilot/sub-pr-630` or `fix/pr576-followup` indicate a PR is related to another. Note the relationship in the Action column (e.g., "draft — sub-PR of #630, addresses review feedback")
- Multiple PRs touching the same area may be a sequence — note which should merge first
- If a repo has systemic CI failures across many PRs, identify the root cause PR (often a CI/config fix) and recommend merging it first to unblock the rest

**Headline summary**: After the tables, add a brief narrative:

```markdown
### Summary

- **N open PRs** across M repos — **X ready to merge, Y need fixes**
- [repo] has N PRs with passing CI ready to merge right now
- [repo] has systemic CI failures — likely shared issue (describe)
- [repo] has a N-day-old stale PR — candidate for close
```

**Presentation**: Group PRs by theme/story, not just by repo. When multiple PRs form a coherent body of work (e.g., "TUI overhaul: 7 PRs ready to merge"), present them as a group with a narrative description of what they collectively achieve. Individual PR numbers are meaningless to the human — what matters is what's happening and what decisions are needed.

**Empty state**: If no open PRs across all repos: "No open PRs."

**Error handling**: If `gh` CLI is unavailable for a repo, note it inline and continue. If all repos fail, skip and note "GitHub unavailable — skipped open PR review."

### Step 4.2.7: PR Action Pipeline

After classifying PRs, recommend specific agent actions for each. The available GitHub agents are:

| Agent              | Workflow               | Trigger                                                        | Purpose                                                              |
| ------------------ | ---------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Custodiet**      | `agent-custodiet.yml`  | `workflow_dispatch` with `target_type`, `target_number`, `ref` | Scope compliance review. APPROVE or REQUEST CHANGES                  |
| **Merge Prep**     | `agent-merge-prep.yml` | `workflow_dispatch` with `pr_number`, `ref`                    | Reads ALL review feedback, pushes fixes, sets Merge Prep status      |
| **`@claude`**      | `claude.yml`           | Comment `@claude <instruction>` on PR                          | Ad-hoc fixes. General-purpose                                        |
| **Copilot Worker** | Copilot Coding Agent   | `@copilot` comment or issue assignment                         | Autonomous task execution following `.github/agents/worker.agent.md` |
| **QA**             | `agent-qa.yml`         | `workflow_dispatch`                                            | End-to-end verification                                              |

**Typical pipeline for a new PR**:

1. Custodiet reviews (scope compliance) → APPROVE or REQUEST CHANGES
2. If CHANGES_REQUESTED → trigger Merge Prep to fix feedback
3. Merge Prep pushes fixes → CI re-runs → sets "Merge Prep" status
4. PR auto-merges when all checks pass

**Merge infrastructure awareness**: Different repos have different merge mechanics. When merge operations fail, note the blocker (merge queue, auto-merge disabled, token permissions) rather than retrying. Common blockers:

- **Merge queue enabled but auto-merge disabled** → human must enable in repo Settings > General
- **Squash-only policy** → use `--squash` not `--merge`
- **Branch protection / rulesets** → may block even `--admin` if rulesets are non-bypassable
- **Token scope** → `gh` token may lack admin permissions for repo settings

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

### Step 4.7: Update synthesis.json (structural data only)

**Read-merge-write** to `$AOPS_SESSIONS/synthesis.json` (same file the cron mechanical synthesis writes to, and the dashboard reads from). Preserve any existing fields from the cron-generated version that you don't have data for.

**Important**: Do NOT generate `daily_story` here. The narrative is generated once in Step 5.3.1 (work-summary.md) after Today's Story has been composed with full day context. Writing a narrative here and overwriting it in 5.3.1 wastes tokens. Step 4.7 writes only structural/mechanical data.

**4.7.1: Assemble and write synthesis.json**

Read existing `$AOPS_SESSIONS/synthesis.json` if it exists, then merge your data on top:

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "daily_narrative": "Synthesized summary from Step 5.3",
  "daily_story": [
    "You started the morning reviewing the HDR extension request",
    "Got pulled into dashboard debugging around 10am",
    "HDR admin tasks still waiting, plus OSB review from yesterday"
  ],
  "narrative_generated": "ISO timestamp",
  "sessions": {
    "total": N,
    "by_project": {"aops": 2, "writing": 1},
    "recent": [{"session_id": "...", "project": "...", "summary": "..."}]
  },
  "narrative": ["[project] Session summary 1", "[project] Session summary 2"],
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

**Key fields**:

| Field                 | Source                            | Notes                                   |
| --------------------- | --------------------------------- | --------------------------------------- |
| `daily_story`         | Written by Step 5.3.1 only        | Do NOT write here — see work-summary.md |
| `narrative_generated` | Written by Step 5.3.1 only        | Updated alongside daily_story           |
| `narrative`           | Mechanical from session summaries | Backward compat; cron also writes this  |
| `merged_prs`          | From Step 4.2.5                   | Not available in cron version           |
| `next_action`         | From Step 3 recommendations       | Highest priority ready task             |
| `session_timeline`    | From session JSONs                | Chronological activity log              |

**Write atomically**: Read existing file, deep-merge your fields on top (don't discard fields you don't have data for like `skill_insights` from cron), write to temp file, then rename.
