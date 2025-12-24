---
name: session-insights
description: Extract accomplishments and learnings from Claude Code sessions. Updates daily summary and mines for framework patterns.
allowed-tools: Read,Bash,Glob,Grep,Edit,Write,Skill,mcp__gemini__ask-gemini,mcp__memory__retrieve_memory,Skill(skill="remember"),mcp__memory__update_memory_metadata
version: 2.4.0
permalink: skills-session-insights
---

# Session Insights Skill

Extract accomplishments and learnings from Claude Code sessions. Idempotent - safe to run anytime.

## Arguments

- `today` (default) - process today's sessions
- `YYYYMMDD` - process specific date

## Workflow

```
/session-insights [date|today]
    ↓
1. BATCH TRANSCRIPTS (generate missing, skip up-to-date)
    ↓
2. DAILY SUMMARY (accomplishments → daily note)
    ↓
3. DATA MINING (Gemini → patterns, problems)
    ↓
4. EXPERIMENT EVALUATION (report status)
```

---

## Step 1: Batch Transcripts

Find sessions via `lib.session_reader.find_sessions()` filtered by date.

```python
from lib.session_reader import find_sessions
from datetime import datetime, timezone

target_date = datetime.now(timezone.utc).date()  # or parse YYYYMMDD arg

# SessionInfo has: path, project, session_id, last_modified (NO start_time!)
sessions = [s for s in find_sessions() if s.last_modified.date() == target_date]
```

**Freshness check**: For EACH session returned:

```python
# Match by session ID (first 8 chars) - NOT by counting files
transcript_exists = any(transcript_dir.glob(f"*{session.session_id[:8]}*"))
needs_update = not transcript_exists or session.last_modified > transcript.mtime
```

⚠️ **CRITICAL**: Do NOT assume existing files match current sessions. Sessions from different machines have different IDs. Always match explicitly.

**Generate**: `Skill(skill="transcript")` for each needing update.

**Output**: `$ACA_DATA/sessions/claude/YYYYMMDD-<shortproject>-<sessionid>-<slug>-{full,abridged}.md`

**Both versions generated** - full for deep analysis, abridged for quick review.

---

## Step 2: Daily Summary

Update `$ACA_DATA/sessions/YYYYMMDD-daily.md` with accomplishments.

### Shared File Model

The daily note is a **shared file** - both user and skill write to it:

| Writer | Content | Examples |
|--------|---------|----------|
| User | Manual notes, observations, follow-ups | "Things to follow up on", tables, insights |
| Skill | Extracted accomplishments from transcripts | `- [x] Fixed transcript skill` |

**Rules**:
- ❌ NEVER delete user content
- ✅ Reorganize content to maintain structure
- ✅ Move orphaned content to appropriate sections
- ✅ Fix frontmatter if it's template boilerplate
- ✅ Add missing sections (projects, session log)

### Daily Note Format

**Structure**: Projects ordered by priority, user notes preserved in appropriate sections.

```markdown
# Daily Summary - YYYY-MM-DD

## 🎯 NOW: [Current Focus]
→ [Single next action]

## PRIMARY: [Project Name] → [[projects/name]]
████░░░░░░░░░░░░░░░░ N/M

- [ ] Incomplete task from yesterday
- [ ] Another incomplete task
- [x] Completed today
- [x] Also completed today

## SECONDARY: [Project Name] → [[projects/name]]
░░░░░░░░░░░░░░░░░░░░ 0/N

- [ ] Task
- [x] Done task

## TERTIARY: [Project Name]
...

---

## Notes
<!-- User observations, follow-ups, tables - preserved from manual edits -->

---

## Session Log
<!-- Machine-readable session tracking -->
```

### Format Rules

1. **No frontmatter summary** - No BLOCKERS/DONE sections at top (duplicates project lists)
2. **Projects in priority order** - PRIMARY, SECONDARY, TERTIARY, FILLER
3. **Burndown immediately after header** - Progress bar on line after `## PROJECT`
4. **One header per project** - Max one `##` per project
5. **Carryover incomplete tasks only** - Don't carry observations or schema notes
6. **Completed items under their project** - No separate "completed" section at bottom
7. **Rich linking** - Use wikilinks `[[projects/NAME]]` for project references

### Load Sessions

```bash
cd $AOPS && uv run python -c "
from lib.session_reader import find_sessions
from lib.session_analyzer import SessionAnalyzer
from datetime import datetime, timezone, timedelta
# ... extract and print session data
"
```

### Update Rules

- **Preserve user content**: Never delete observations, tables, notes the user wrote
- **Reorganize if needed**: Move orphaned content to `## Notes` section at bottom
- **Fix template frontmatter**: Replace "Clear Descriptive Title" with actual date title
- **Carry over**: Yesterday's `- [ ]` incomplete tasks only
- **Add**: New `- [x]` accomplishments under their project section
- **Deduplicate**: Never duplicate tasks across sections
- **Progress bars**: Run `update_daily_note_dashboard()` after updating

### Handling Existing Content

If file exists with user content:
1. Read existing content
2. Identify user-written sections (observations, tables, follow-ups)
3. Build proper structure around user content
4. Place user notes in `## Notes` section if no clear project fit
5. Never discard anything the user wrote

---

## Step 3: Data Mining (Gemini)

**Mine ALL transcripts** - even short sessions can have valuable learnings.

### 3a. Extract findings via Gemini (batched)

<<<<<<< Updated upstream
Call `mcp__gemini__ask-gemini` for ALL transcripts simultaneously. See `mining-prompt.md` for full prompt.

Key extraction categories:
1. **USER CORRECTIONS** (highest priority) - instances where the user corrected agent behavior
2. **OTHER PROBLEMS** - navigation failures, verification skipped, instructions ignored
3. **SUCCESSES** - correct tool usage, proper instruction following
4. **EXPERIMENT EVIDENCE** - behavior matching/contradicting hypotheses

### 3b. Route findings

**User corrections → /learn skill**

Each user correction gets passed to `/learn` with full context:
=======
Call `mcp__gemini__ask-gemini` in batches of 4 to avoid rate limits:
>>>>>>> Stashed changes

```
Skill(skill="learn", args="
User correction detected in session:

**Agent action**: [what agent was doing]
**Target**: [file/component being modified]
**User feedback**: [the correction]
**Suggested lesson**: [generalizable principle]

Evidence:
[transcript quote]
")
```

This provides `/learn` with enough context to:
- Identify the category of issue
- Check for prior occurrences
- Choose appropriate intervention level

**Other findings → /log skill**

```
Skill(skill="log", args="session-mining: <remaining_findings_json>")
```

The log skill routes by category to appropriate learning files.

---

## Step 4: Experiment Evaluation

Report: Which experiments got evidence? Any ready for decision?

---

## Output

```
## Session Insights - YYYY-MM-DD

### Transcripts
- Generated: N | Skipped: N

### Daily Summary
- Updated: sessions/YYYYMMDD-daily.md

### Learnings
- Problems: N | Successes: N | Evidence: N
```

## Constraints

- **Idempotent** - run multiple times safely
- **DO NOT** auto-apply learnings - route only
- **DO NOT** modify HEURISTICS.md directly
