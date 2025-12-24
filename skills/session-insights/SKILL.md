---
name: session-insights
description: Extract accomplishments and learnings from Claude Code sessions. Updates daily summary and mines for framework patterns.
allowed-tools: Read,Bash,Task,Edit,Write
version: 3.0.0
permalink: skills-session-insights
---

# Session Insights Skill

Routine command for daily session processing. Runs parallel agents for speed.

## Arguments

- `today` (default) - process today's sessions
- `YYYYMMDD` - process specific date

## Execution (Follow These Steps Exactly)

### Step 1: Find Sessions Needing Transcripts

Run this exact command:

```bash
cd /opt/nic/writing/academicOps && uv run python -c "
from lib.session_reader import find_sessions
from datetime import datetime, timezone
import os, glob

target_date = datetime.now(timezone.utc).date()  # or parse arg
transcript_dir = '/opt/nic/writing/data/sessions/claude'
os.makedirs(transcript_dir, exist_ok=True)

sessions = [s for s in find_sessions()
            if s.last_modified.date() == target_date
            and 'claude-test' not in s.project
            and os.path.getsize(s.path) > 5000]

for s in sessions:
    existing = glob.glob(f'{transcript_dir}/*{s.session_id[:8]}*-abridged.md')
    needs_gen = not existing or s.last_modified.timestamp() > os.path.getmtime(existing[0])
    if needs_gen:
        shortproject = s.project.split('-')[-1]
        print(f'{s.path}|{s.session_id[:8]}|{shortproject}')
"
```

This outputs lines like: `/path/to/session.jsonl|abc12345|writing`

### Step 2: Generate Transcripts (Parallel)

For EACH line from Step 1, spawn a Task agent (max 8 concurrent):

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Transcript: {shortproject}",
  prompt="
Run this exact command and report success/failure:

cd /opt/nic/writing/academicOps && uv run python scripts/claude_transcript.py \\
  {session_path} \\
  -o /opt/nic/writing/data/sessions/claude/YYYYMMDD-{shortproject}-{session_id}

Report: Generated or Failed (with error)
"
)
```

**Spawn up to 8 agents in ONE message** for parallel execution.

### Step 2b: Verify Transcripts

After Task agents complete, verify outputs exist:

```bash
ls -la /opt/nic/writing/data/sessions/claude/YYYYMMDD*-abridged.md | wc -l
```

If count < expected, check for failures and re-run failed ones.

### Step 3: Update Daily Summary

After transcripts complete, create/update daily note at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

Read the generated abridged transcripts and extract accomplishments:

```bash
ls /opt/nic/writing/data/sessions/claude/YYYYMMDD*-abridged.md
```

For each transcript, identify completed work items and add to daily note under appropriate project headers.

**Daily note format:**
```markdown
# Daily Summary - YYYY-MM-DD

## PRIMARY: [Project] → [[projects/name]]
- [x] Accomplishment from sessions
- [x] Another accomplishment

## SECONDARY: [Project]
- [x] Work done

---
## Session Log
| Session | Project | Summary |
|---------|---------|---------|
| abc123 | writing | Brief description |
```

### Step 4: Mine for Learnings (Parallel)

For EACH abridged transcript, spawn a Task agent for Gemini analysis (max 8 concurrent):

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Mine: {shortproject}",
  prompt="
Call mcp__gemini__ask-gemini with this prompt:

@{transcript_path}

Analyze this Claude Code session. Extract:
1. USER CORRECTIONS - where user corrected agent behavior
2. FAILURES - mistakes requiring intervention
3. SUCCESSES - tasks completed well

Return JSON:
{
  \"corrections\": [{\"action\": \"...\", \"feedback\": \"...\", \"lesson\": \"...\"}],
  \"failures\": [{\"description\": \"...\", \"category\": \"...\"}],
  \"successes\": [{\"description\": \"...\"}]
}
"
)
```

### Step 5: Route Findings

Collect Gemini outputs. For each user correction found:

```
Skill(skill="learn", args="User correction: {action} → {feedback}. Lesson: {lesson}")
```

For other findings, append to LOG.md.

---

## Output

```
## Session Insights - YYYY-MM-DD

### Transcripts
- Generated: N | Skipped: M

### Daily Summary
- Updated: sessions/YYYYMMDD-daily.md

### Learnings
- Corrections: N | Failures: N | Successes: N
```

## Constraints

- **Parallel execution**: Use Task tool, spawn up to 8 agents at once
- **Idempotent**: Safe to run multiple times
- **No judgment**: Follow steps exactly, don't improvise
