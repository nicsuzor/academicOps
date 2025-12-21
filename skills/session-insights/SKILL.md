---
name: session-insights
description: Extract accomplishments and learnings from Claude Code sessions. Updates daily summary and mines for framework patterns.
allowed-tools: Read,Bash,Glob,Grep,Edit,Write,Skill,mcp__gemini__ask-gemini,mcp__memory__retrieve_memory,Skill(skill="remember"),mcp__memory__update_memory_metadata
version: 2.0.0
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

**Freshness check**: Generate if transcript missing OR session mtime > transcript mtime.

**Generate**: `Skill(skill="transcript")` for each needing update.

**Output**: `$ACA_DATA/sessions/claude/YYYYMMDD-<project>-<slug>-abridged.md`

---

## Step 2: Daily Summary

Update `$ACA_DATA/sessions/YYYYMMDD-daily.md` with accomplishments.

### Daily Note Format

**Structure**: Projects only, ordered by priority. No frontmatter summary sections.

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

- **Carry over**: Yesterday's `- [ ]` incomplete tasks only (not observations)
- **Add**: New `- [x]` accomplishments under their project section
- **Deduplicate**: Never duplicate tasks across sections
- **Progress bars**: Run `update_daily_note_dashboard()` after updating

See `lib/session_analyzer.py` for implementation details.

---

## Step 3: Data Mining (Gemini)

Load active experiments and learning themes, then extract via Gemini:
- Problems: user corrections, failures, verification skips
- Successes: patterns that worked
- Experiment evidence: hypothesis matches

**Route**: Known patterns → `learning/*.md`, novel → `LOG.md`, evidence → `experiments/*.md`

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
