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

**Steps 4.1, 4.1.5, 4.2, and 4.2.5 — run in parallel.** These data-gathering steps are independent: they read from different sources (shell scripts, PKB, session JSONs, GitHub) and produce separate outputs that are merged only at composition time. Agent teams should dispatch concurrent subagents for each; single-agent environments should issue all data-fetching tool calls simultaneously rather than sequentially.

### Step 4.1: Narrative Path Reconstruction (Compass Model)

Instead of a mechanical table, build a narrative timeline of the day's work using the `show_path.py` script. This helps the user recover context and identify "where they are" in the day's story.

```bash
uv run python3 aops-core/scripts/show_path.py --hours 24
```

**Use as an input to the editorial synthesis**, not as a section to render verbatim. The path output helps you see the threads of work per project — what was started, what was finished, what was claimed — so the Today's Log narrative can name them. There is no standalone `## Session Timeline` or `## Today's Path` section in the daily note; the synthesis absorbs these signals.

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

Use the user's prompt `description` text as the primary signal. Project name is a fallback — check the project's tags or category in ACA_DATA rather than hardcoding names.

**Classification is a signal, not a structure.** Work type tags are evidence the editorial synthesis can draw on — they are not an enforced grouping. The agent chooses the shape of Today's Log (by thread, by project, by chronology, by significance of outcome — see [[instructions/work-summary]] Step 5.3). What stays off-limits: do **not** weight research over infrastructure, or vice versa, as praise or criticism. Describe what happened factually; let the reader draw conclusions.

**Incremental awareness on repeat runs**: Read the current daily note's `## Today's Log` to see what was already synthesised. On a second run, the narrative should lead with what's new since the last write — not re-summarise the whole day.

### Step 4.2.5: Query Merged PRs

Fetch today's merged PRs from **all tracked repositories** defined in `$AOPS_SESSIONS/projects.yaml`.

**Repository discovery**: Read `$AOPS_SESSIONS/projects.yaml` to get the project registry. For each project, resolve the on-disk path via convention (`$AOPS_SRC_DIR/<repo>`) or `$POLECAT_HOME/local.yaml` `paths.<slug>`, then `cd` in and run the query. Skip repos that don't resolve locally.

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

### Step 4.2.6: (retired — moved to Outstanding Workflows)

Open PR handling lives in `## What Needs Attention / Outstanding Workflows` only. See [[instructions/workflow-monitor]] Step 6 for the bucketing rules (Ready to merge, Needs review, Needs fixes, Stale, Draft/autonomous), the `gh pr list` query, and the decision-oriented formatting. The Work Log does not carry a parallel Open PRs table.

When composing the Outstanding Workflows subsection, the agent may apply the PR-action classification heuristics below inline (e.g., note "fix type check + conflicts" next to the PR in its bucket) rather than in a separate table.

### Step 4.2.7: PR Action Pipeline

After classifying PRs, recommend specific agent actions for each. The available GitHub agents are:

| Agent              | Workflow               | Trigger                                                        | Purpose                                                              |
| ------------------ | ---------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Enforcer**       | `agent-enforcer.yml`   | `workflow_dispatch` with `target_type`, `target_number`, `ref` | Scope compliance review. APPROVE or REQUEST CHANGES                  |
| **Merge Prep**     | `agent-merge-prep.yml` | `workflow_dispatch` with `pr_number`, `ref`                    | Reads ALL review feedback, pushes fixes, sets Merge Prep status      |
| **`@claude`**      | `claude.yml`           | Comment `@claude <instruction>` on PR                          | Ad-hoc fixes. General-purpose                                        |
| **Copilot Worker** | Copilot Coding Agent   | `@copilot` comment or issue assignment                         | Autonomous task execution following `.github/agents/worker.agent.md` |
| **QA**             | `agent-qa.yml`         | `workflow_dispatch`                                            | End-to-end verification                                              |

**Typical pipeline for a new PR**:

1. Enforcer reviews (scope compliance) → APPROVE or REQUEST CHANGES
2. If CHANGES_REQUESTED → trigger Merge Prep to fix feedback
3. Merge Prep pushes fixes → CI re-runs → sets "Merge Prep" status
4. PR auto-merges when all checks pass

**Merge infrastructure awareness**: Different repos have different merge mechanics. When merge operations fail, note the blocker (merge queue, auto-merge disabled, token permissions) rather than retrying. Common blockers:

- **Merge queue enabled but auto-merge disabled** → human must enable in repo Settings > General
- **Squash-only policy** → use `--squash` not `--merge`
- **Branch protection / rulesets** → may block even `--admin` if rulesets are non-bypassable
- **Token scope** → `gh` token may lack admin permissions for repo settings

### Step 4.3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Do not propagate fabricated descriptions.

### Step 4.4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Today's Log**: Hand the gathered session data + accomplishments + merged PRs off to [[instructions/work-summary]] Step 5.3, which produces the editorial synthesis. Do **not** construct a Session Log table or Session Timeline table here — both have been retired. The collapsed Work Log contains Merged PRs and Completed Tasks only; session narration lives in `## Today's Log` as prose.

**Completed tasks** (Work Log): Render as a checklist with task IDs. Preserve any user-added notes.

### Step 4.4.5: Generate Goals vs. Achieved Reflection

If the daily note contains a goals section (e.g., "## Things I want to achieve today", "## Status", "### My priorities"), generate a reflection comparing stated intentions against actual outcomes.

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
