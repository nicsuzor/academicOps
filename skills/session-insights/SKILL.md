---
name: session-insights
description: Extract accomplishments and learnings from Claude Code sessions. Updates daily summary and mines for framework patterns.
allowed-tools: Read,Bash,Task,Edit,Write
version: 3.1.0
permalink: skills-session-insights
---

# Session Insights Skill

Routine command for daily session processing. Runs parallel agents for speed.

## Arguments

- `today` (default) - process today's sessions (batch mode)
- `YYYYMMDD` - process specific date (batch mode)
- `current` - analyze current session for reflection (real-time mode, see Step 7)

## Execution (Follow These Steps Exactly)

### Step 1: Find Sessions Needing Transcripts

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

### Step 4: Update Daily Summary

Update daily note at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

If the note exists:
- Read() the ENTIRE note
- incorporate new information into the existing structure
- you MUST consolidate and synthesise related information - merge minor observations and tasks into meanginful groups
- BUT DO NOT delete unique user observations or tasks from other machines that have not been synthesised yet

If the note does NOT exist:
- Create the note from the template in [[templates/daily.md]]

Read the generated abridged transcripts and extract accomplishments:

```bash
ls $ACA_DATA/sessions/claude/YYYYMMDD*-abridged.md
```

For each transcript, identify completed work items and add to daily note under appropriate project headers.

**Daily note format:**
```markdown
# Daily Summary - YYYY-MM-DD

## Focus (Today's priorities)
<!-- User generated. Do not edit. -->

- [ ] Priority task 1
- [ ] Priority task 2

## Session Context
- 10:23 AM: Started on prompt hydrator context improvements
- 11:45 AM: Switched to dashboard investigation
- 2:30 PM: SNSF review triple-check


## [[projects/slug]]
- [x] Accomplishment from sessions
- [ ] Outstanding task

## Abandoned Todos
- [ ] Task left pending (from session abc123)
- [ ] In-progress item not completed (from session def456)

## Session Log
| Session | Project | Summary |
|---------|---------|---------|
| abc123 | writing | Brief description |
```

**Note**: Accomplishments are recorded under their respective project headers with `[x]` markers. Session Context and Abandoned Todos come from the narrative extraction script.

### Step 5: Mine for Learnings (Parallel)

For EACH abridged transcript, spawn a Task agent for Gemini analysis (max 8 concurrent):

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Mine: {shortproject}",
  prompt="
Call mcp__gemini__ask-gemini with this prompt:

@{transcript_path}

Analyze this Claude Code session transcript. Extract:

1. SKILL EFFECTIVENESS - Look for '**Skill(s)**: X' (suggested) and '🔧 Skill invoked: `Y`' (used)
   - Were recommended skills invoked? Was the skill useful when invoked?
   - Did agent struggle without recommended context when skill was skipped?

2. CONTEXT TIMING - Was context injected at the right time?
   - Did missing/late context cause mistakes?
   - What context should have been available earlier?

3. USER CORRECTIONS - where user corrected agent behavior

4. FAILURES - mistakes requiring intervention (categories: navigation|verification|instruction|hallucination|skill-bypass|context-gap|other)

5. SUCCESSES - tasks completed well, especially when skills were properly invoked

6. HEURISTIC MAPPING - For each correction/failure, identify which heuristic from HEURISTICS.md it relates to:
   - H2 (Skill-First) - skill bypass patterns
   - H3 (Verification Before Assertion) - claiming success without testing
   - H4 (Explicit Instructions Override Inference) - doing X when asked for Y
   - H22 (Indices Before Exploration) - exploring without checking index files first
   - Other H[n] as appropriate

Return JSON:
{
  \"skill_effectiveness\": [{\"skill_suggested\": \"...\", \"skill_invoked\": \"...\", \"followed_suggestion\": true/false, \"was_useful\": true/false/null, \"notes\": \"...\"}],
  \"context_issues\": [{\"issue\": \"...\", \"consequence\": \"...\", \"missing_context\": \"...\", \"suggested_injection_point\": \"...\"}],
  \"corrections\": [{\"action\": \"...\", \"feedback\": \"...\", \"lesson\": \"...\", \"heuristic\": \"H[n] or null\", \"suggested_evidence\": \"YYYY-MM-DD: [observation]\"}],
  \"failures\": [{\"description\": \"...\", \"category\": \"...\", \"heuristic\": \"H[n] or null\", \"suggested_evidence\": \"YYYY-MM-DD: [observation]\"}],
  \"successes\": [{\"description\": \"...\", \"skill_contributed\": \"...\"}]
}
"
)
```

### Step 6: Save Insights & Route Findings

**Save mining results to JSON for dashboard:**

Write aggregated Gemini outputs to `$ACA_DATA/dashboard/insights.json`:

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "sessions_analyzed": N,
  "skill_effectiveness": [/* aggregated from all sessions */],
  "context_issues": [/* aggregated */],
  "corrections": [/* aggregated */],
  "failures": [/* aggregated */],
  "successes": [/* aggregated */],
  "summary": {
    "compliance_rate": 0.0-1.0,
    "skills_suggested": ["framework", "python-dev"],
    "skills_invoked": ["framework"],
    "top_context_gaps": ["description1", "description2"]
  }
}
```

**Update daily note with insights section:**

Add to daily note `$ACA_DATA/sessions/YYYYMMDD-daily.md`:

```markdown
## Session Insights

**Skill Compliance**: X% (N/M turns followed suggestions)
**Top Skills**: framework (67%), python-dev (100%)
```

**Route learnings:**
- For each correction/failure, invoke `Skill(skill="learning-log", args="...")`
- Run up to 8 skills in parallel

---

## Output Locations

| Artifact | Location | Format |
|----------|----------|--------|
| Transcripts (full) | `$ACA_DATA/sessions/claude/YYYYMMDD-{project}-{sessionid}-*-full.md` | Markdown with YAML frontmatter |
| Transcripts (abridged) | `$ACA_DATA/sessions/claude/YYYYMMDD-{project}-{sessionid}-*-abridged.md` | Markdown with YAML frontmatter |
| Daily summary | `$ACA_DATA/sessions/YYYYMMDD-daily.md` | Markdown with insights section |
| Mining results | `$ACA_DATA/dashboard/insights.json` | JSON for dashboard |
| Learning observations | GitHub Issues (nicsuzor/academicOps) | Via `/log` skill → Issues |

## Output Summary

```
## Session Insights - YYYY-MM-DD

### Transcripts
- Generated: N | Skipped: M

### Daily Summary
- Updated: sessions/YYYYMMDD-daily.md

### Learnings
- insight ...
- insight ...

```

## Constraints

- **Parallel execution**: Use multiple Bash calls for transcripts; Task agents only for Gemini mining
- **Idempotent**: Safe to run multiple times; do not delete existing information
- **No judgment**: Follow steps exactly, don't improvise

---

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

---

## Triggers for `current` Mode

| Trigger | How Invoked |
|---------|-------------|
| Session end | Stop hook injects: `Skill(skill="session-insights", args="current")` |
| Manual | User runs `/reflect` command |
