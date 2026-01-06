---
name: session-insights
category: instruction
description: Extract accomplishments and learnings from Claude Code sessions. Updates daily summary and mines for framework patterns.
allowed-tools: Read,Bash,Task,Edit,Write
version: 3.2.0
permalink: skills-session-insights
---

# Session Insights Skill

Routine command for daily session processing. Runs parallel agents for speed.

## Arguments

- `today` (default) - process today's sessions (batch mode)
- `YYYYMMDD` - process specific date (batch mode)
- `current` - analyze current session for reflection (real-time mode, see Step 7)
- `<path1> [path2] ...` - process specific session JSONL files (explicit mode, used by cron)

## Execution (Follow These Steps Exactly)

### Step 1: Find Sessions Needing Transcripts

**If args are explicit paths** (contain `/` or end in `.jsonl`):

- Skip the find_sessions.py script
- Use the provided paths directly
- Extract session_id from filename (e.g., `/path/to/abc12345.jsonl` → session_id = `abc12345`)
- Extract project from parent directory name
- Format as: `{path}|{session_id[:8]}|{project_shortname}`

**Otherwise**, run the discovery script:

```bash
cd $AOPS && uv run python skills/session-insights/scripts/find_sessions.py
# Or for a specific date:
cd $AOPS && uv run python skills/session-insights/scripts/find_sessions.py --date YYYYMMDD
```

Output: lines of `session_path|session_id_prefix|shortproject`

### Step 2: Generate Transcripts

For EACH line from Step 1, run Bash directly (no need for Task agents):

```bash
cd $AOPS && uv run python scripts/claude_transcript.py \
  {session_path} \
  -o $ACA_DATA/sessions/claude/YYYYMMDD-{shortproject}-{session_id}
```

Run multiple Bash calls in parallel for speed.

### Step 2b: Verify Transcripts

```bash
ls $ACA_DATA/sessions/claude/YYYYMMDD*-abridged.md | wc -l
```

If count < expected, check output for failures and re-run.

### Step 3: Extract Narrative Signals

Run the narrative extraction script to capture session context and abandoned todos:

```bash
cd $AOPS && uv run python skills/session-insights/scripts/extract_narrative.py --date YYYYMMDD
```

This outputs markdown sections for:

- **Session Context**: Timestamped first prompts showing what work was started
- **Abandoned Todos**: Items left pending/in_progress at session end

Save this output - you'll incorporate it into the daily note in the next step.

### Step 4: Initialize Daily Note (Lightweight)

**DO NOT read transcripts here.** Only set up the daily note skeleton with narrative signals from Step 3.

Update daily note at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

If the note exists:

- Read() the note (small file, ~50 lines)
- Add Session Context and Abandoned Todos from Step 3 output
- DO NOT delete existing content

If the note does NOT exist:

- Create from template in [[templates/daily.md]]
- Add Session Context and Abandoned Todos from Step 3 output

See [[templates/daily.md]] for daily note structure. Key sections: Today's Story, Focus Dashboard, Priority Burndown, Today's Priorities, Project Accomplishments, Abandoned Todos, Session Log/Timeline.

**Critical**: Claude does NOT read transcripts. Accomplishments come from Gemini-mined JSONs in Step 6.

### Step 5: Mine for Learnings (Parallel)

**Skip already-mined sessions**: Before mining, check if output JSON already exists.

For EACH abridged transcript:

1. **Check if already mined**:
   ```bash
   ls $ACA_DATA/dashboard/sessions/{session_id}.json 2>/dev/null
   ```
   - If file exists → SKIP this session (already processed)
   - If file does not exist → proceed with mining

2. **Spawn Task agent for Gemini analysis** (max 8 concurrent):

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Mine: {shortproject}",
  prompt="
Call mcp__gemini__ask-gemini with this prompt (substitute the metadata values):

@{transcript_path}

Analyze this Claude Code session transcript. Extract the following information.

SESSION METADATA (include these EXACTLY in your response):
- session_id: {session_id}
- date: {date}
- project: {project}

EXTRACTION TASKS:
1. SUMMARY - One sentence describing what was worked on
2. ACCOMPLISHMENTS - List of completed items
3. SKILL EFFECTIVENESS - Look for '**Skill(s)**: X' (suggested) and '🔧 Skill invoked: `Y`' (used)
4. CONTEXT TIMING - Was context injected at the right time?
5. USER CORRECTIONS - with heuristic mapping (H2=Skill-First, H3=Verification, H4=Explicit Instructions, H22=Indices First)
6. FAILURES - mistakes requiring intervention
7. SUCCESSES - tasks completed well
8. USER MOOD/SATISFACTION - Subjective assessment: -1.0 (frustrated) to 1.0 (satisfied), 0.0 neutral
9. CONVERSATION FLOW - List of [timestamp, role, content] tuples showing dialogue (user prompts verbatim, agent responses summarized)
10. VERBATIM USER PROMPTS WITH CONTEXT - All user prompts with preceding agent message (format: [timestamp, role, content] tuples)

Return JSON with this EXACT structure:
{
  \"session_id\": \"{session_id}\",
  \"date\": \"{date}\",
  \"project\": \"{project}\",
  \"summary\": \"one sentence description\",
  \"accomplishments\": [\"item1\", \"item2\"],
  \"learning_observations\": [{\"category\": \"...\", \"evidence\": \"...\", \"context\": \"...\", \"heuristic\": \"H[n] or null\", \"suggested_evidence\": \"...\"}],
  \"skill_compliance\": {\"suggested\": [...], \"invoked\": [...], \"compliance_rate\": 0.0-1.0},
  \"context_gaps\": [\"gap1\", \"gap2\"],
  \"user_mood\": 0.3,
  \"conversation_flow\": [[\"timestamp\", \"user\", \"prompt text\"], [\"timestamp\", \"agent\", \"response summary\"]],
  \"user_prompts\": [[\"timestamp\", \"agent\", \"preceding message\"], [\"timestamp\", \"user\", \"verbatim prompt\"]]
}

After receiving the JSON response, save it to: $ACA_DATA/dashboard/sessions/{session_id}.json
"
)
```

1. **Create sessions directory if needed**:
   ```bash
   mkdir -p $ACA_DATA/dashboard/sessions
   ```

### Step 5b: Verify Mining

**Wait for all mining agents to complete**, then verify:

```bash
# Count expected (transcripts for date)
ls $ACA_DATA/sessions/claude/YYYYMMDD*-abridged.md | wc -l

# Count actual (mined JSONs for date)
ls $ACA_DATA/dashboard/sessions/*.json 2>/dev/null | xargs -I{} grep -l '"date": "YYYY-MM-DD"' {} 2>/dev/null | wc -l
```

**If mined < expected**:

1. Identify unmined sessions (transcripts without matching JSONs)
2. Re-spawn mining agents for failed sessions (repeat Step 5 for those sessions only)
3. Re-verify until mined >= 80% of expected (some sessions may be too short to mine)

**Only proceed to Step 6 when verification passes.**

### Step 6: Synthesize (Claude Code Agent)

**AUTHORITATIVE SOURCE**: The daily note (`$ACA_DATA/sessions/YYYYMMDD-daily.md`) is the single source of truth for accomplishments. Session JSONs feed INTO the daily note; synthesis.json is a dashboard-optimized VIEW of the daily note.

**Claude reads small JSONs (~20 lines each), NOT transcripts. This is where accomplishments get populated.**

1. **Read all session JSONs for target date**:
   ```bash
   ls $ACA_DATA/dashboard/sessions/*.json
   ```
   Read each JSON file (they're small, ~500 bytes each). Filter to sessions matching the target date.

2. **Read existing files (if they exist)**:
   - `$ACA_DATA/sessions/YYYYMMDD-daily.md` (skeleton from Step 4)
   - `$ACA_DATA/dashboard/synthesis.json`

3. **Merge sessions** (idempotent by session_id):
   - For each session JSON: if session_id already in existing data → update, else → add
   - This ensures running from multiple machines integrates rather than duplicates

4. **Update daily.md with accomplishments from JSONs** at `$ACA_DATA/sessions/YYYYMMDD-daily.md`:

   **VERIFY DESCRIPTIONS**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

   **Task data**: Do NOT read `$ACA_DATA/tasks/index.json` directly (too large). Instead:
   - Use `grep -l '"scheduled": "YYYY-MM-DD"' $ACA_DATA/tasks/*.md` to find scheduled tasks
   - Or use `grep -l '"priority": "P0"' $ACA_DATA/tasks/*.md` for priority filtering

```markdown
# Daily Summary - YYYY-MM-DD

## Today's Story

Brief narrative of what was accomplished today (2-3 sentences synthesized from session summaries).

## 📊 Focus Dashboard

### Priority Burndown
```

P0 ████████░░ 80% (4/5) → [[task-name-1]], [[task-name-2]]
P1 ██░░░░░░░░ 20% (1/5) → [[task-name-3]]
P2 ░░░░░░░░░░ 0% (0/3)

```
### 🎯 Active Now
→ [[task-currently-in-progress]] (P0)

### ⏳ Blocked
- [[task-waiting]] - waiting on: external response



## Session Log
| Session | Project | Summary |
|---------|---------|---------|
| abc1234 | writing | Brief description of work |
| def5678 | aops | Another session summary |

## Session Timeline
| Time | Session | Terminal | Project | Activity |
|------|---------|----------|---------|----------|
| 10:15 | abc1234 | writing | aops | Started session-insights work |
| 10:23 | def5678 | tja | tja | Reviewed paper draft |
| 10:45 | abc1234 | writing | aops | Got sidetracked to fix bug |

(Extract terminal from session path: `YYYYMMDD-{terminal}-{session_id}`)
(Build timeline from conversation_flow timestamps across all sessions)

### Terminal Overwhelm Analysis
(Interpret the timeline to help user understand their work patterns)
- Which terminals had context switches between projects?
- Was user working on one thing then pulled to another?
- Patterns of sidetracking (started A, interrupted by B, returned to A?)
- Which terminals went idle (long gaps between activity)?

## [[academicOps]] → [[projects/aops]]
Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items
- [x] Accomplishment from aops sessions
- [x] Another accomplishment

## [[writing]] → [[projects/writing]]
Scheduled: ████░░░░░░ 4/10 | Unscheduled: 2 items
- [x] Accomplishment from writing sessions

## Session Insights
```

Skill Compliance ████████░░ 80%
Sessions Mined ████████░░ 8/10

```
**Top Context Gaps**: gap1, gap2
```

**Progress Metrics** (IMPORTANT - distinguish scheduled vs unscheduled):

- **Scheduled**: Tasks from `$ACA_DATA/tasks/` with `project:` matching this project and `scheduled:` date = today
- **Unscheduled**: Accomplishments from session mining that don't correspond to scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`
- If NO scheduled tasks exist for project: `Scheduled: n/a | Unscheduled: N items`
- Progress bar shows scheduled task completion ONLY (not accomplishment count)

**ASCII Progress Bar Helper** (for 10-char bars):

- Calculate: `filled = round(ratio * 10)`
- Use: `█` × filled + `░` × (10 - filled)
- Example: 75% → `████████░░`
- If no scheduled tasks: show `n/a` instead of bar

**Wikilink Rules**:

- Tasks: `[[YYYYMMDD-task-slug]]` (matches filename in tasks/)
- Projects: `[[projects/project-name]]`
- Quick Wins / ad-hoc items: Link if task file exists, otherwise plain text
- Sessions: plain text (session IDs, not linked)

1. **Write updated synthesis.json** at `$ACA_DATA/dashboard/synthesis.json`:

   synthesis.json is a **dashboard-optimized view** of the daily note - it should reflect ALL accomplishments from the daily note, not just those from mined session JSONs. If daily note has manually-added accomplishments, include them.

   Use grep to find P0/waiting tasks (see Task data note above) to populate next_action and waiting_on.

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "sessions": {
    "total": N,
    "by_project": {"aops": 2, "writing": 1},
    "recent": [
      {"session_id": "abc1234", "project": "writing", "summary": "..."},
      {"session_id": "def5678", "project": "aops", "summary": "..."}
    ]
  },
  "narrative": ["Started: session summary 1", "Also worked on: session summary 2"],
  "accomplishments": {
    "count": N,
    "summary": "brief text of top accomplishments",
    "items": [
      {"project": "aops", "item": "Completed feature X"},
      {"project": "writing", "item": "Fixed bug Y"}
    ]
  },
  "next_action": {
    "task": "First P0 task title from task index",
    "reason": "Highest priority task",
    "project": "project-name"
  },
  "alignment": {
    "status": "on_track|blocked|drifted",
    "note": "explanation if blocked or drifted"
  },
  "waiting_on": [
    {"task": "waiting task title", "blocker": "waiting on external"}
  ],
  "skill_insights": {
    "compliance_rate": 0.75,
    "corrections_count": N,
    "failures_count": N,
    "successes_count": N,
    "top_context_gaps": ["gap1", "gap2"]
  },
  "user_mood": {
    "average": 0.3,
    "by_session": {"abc1234": 0.5, "def5678": 0.1}
  },
  "session_timeline": [
    {"time": "10:15", "session": "abc1234", "terminal": "writing", "project": "aops", "activity": "Started work"},
    {"time": "10:45", "session": "abc1234", "terminal": "writing", "project": "aops", "activity": "Sidetracked"}
  ]
}
```

### Step 6b: Route Learnings

**For each learning observation with heuristic mapping:**

- Invoke `Skill(skill="learning-log", args="...")` to create/update GitHub Issues
- Run up to 8 skills in parallel

## Output Locations

See [[references/output-locations.md]] for artifact paths and output summary template.

## Constraints

- **Parallel execution**: Use multiple Bash calls for transcripts; Task agents only for Gemini mining
- **Idempotent**: Safe to run multiple times; do not delete existing information
- **No judgment**: Follow steps exactly, don't improvise

## Step 7: Session Reflection (for `current` mode only)

When invoked with `current` arg (e.g., via Stop hook or `/reflect`):

### 7a: Skip Steps 1-4

The current session transcript is already available. No need to generate transcripts.

### 7b: Mine Current Session

Read the current session transcript from the environment (provided by hook or read from `~/.claude/projects/*/sessions/*.jsonl`).

Run the Step 5 mining prompt on this single session.

### 7c: Present Suggestions for Approval

For each finding with a non-null `heuristic` field, present to user:

```
## Session Reflection

### [Category]: [Description]
**Pattern**: [What happened]
**Evidence**: [Quote or turn reference]
**Relates to**: H[n] ([Heuristic name])

**Suggested update**: Add evidence to H[n]
> "[suggested_evidence text]"
```

Then use AskUserQuestion:

```
AskUserQuestion(questions=[{
  "question": "Update HEURISTICS.md with these observations?",
  "header": "Reflect",
  "multiSelect": true,
  "options": [
    {"label": "Approve all", "description": "Add all suggested evidence entries"},
    {"label": "Skip", "description": "Dismiss without updating"}
  ]
}])
```

### 7d: Apply Approved Updates

For each approved suggestion:

1. Read `$AOPS/HEURISTICS.md`
2. Find the relevant H[n] section
3. Add the `suggested_evidence` text to the **Evidence** section with today's date
4. Write the updated file

### 7e: Log to GitHub Issue

For significant patterns, invoke `Skill(skill="learning-log")` to create/update a GitHub Issue for tracking.

## Triggers for `current` Mode

| Trigger     | How Invoked                                                          |
| ----------- | -------------------------------------------------------------------- |
| Session end | Stop hook injects: `Skill(skill="session-insights", args="current")` |
| Manual      | User runs `/reflect` command                                         |
