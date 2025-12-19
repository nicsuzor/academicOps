---
name: session-analyzer
description: Analyze Claude Code session logs to extract semantic meaning - accomplishments, decisions, topics, blockers.
allowed-tools: Read,Bash,Write,Edit,mcp__bmem__write_note,mcp__bmem__edit_note,mcp__bmem__search_notes
version: 2.0.0
permalink: skills-session-analyzer
---

# Session Analyzer Skill

Analyze Claude Code session logs to extract semantic meaning using LLM understanding (not keyword matching). Produces curated daily summaries grouped by project.

## When to Use

- "What did I accomplish today?"
- "Summarize this session"
- "What decisions were made?"
- "What's been happening in my sessions?"
- `/analyze-sessions` command

## Arguments

When invoked via command, accepts optional argument:
- Session ID (8+ hex chars)
- Date (`YYYYMMDD`)
- `today` (default)

## Process

1. **Load session data** for target date
2. **Group by project** - combine sessions working on same project
3. **Curate** - focus on significant items, not everything
4. **Add rich links** - search bmem to link tasks, decisions, contacts
5. **Merge into daily note** (non-destructive - never overwrite existing content)

## Loading Session Data

```bash
cd $AOPS && uv run python -c "
from lib.session_reader import find_sessions
from lib.session_analyzer import SessionAnalyzer
from datetime import datetime, timezone, timedelta

# Parse arguments for date (replace \$ARGUMENTS with actual value)
args = '\$ARGUMENTS'.strip()
if args.isdigit() and len(args) == 8:
    target = datetime(int(args[:4]), int(args[4:6]), int(args[6:8]), tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
else:
    target = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = target + timedelta(days=1)

sessions = find_sessions()
analyzer = SessionAnalyzer()

# Group by project
projects = {}
for s in sessions:
    if target <= s.last_modified < next_day:
        proj = s.project_display
        if proj not in projects:
            projects[proj] = []
        projects[proj].append(s)

# Analyze most substantive session per project
for proj, sess_list in sorted(projects.items()):
    most_recent = sess_list[0]
    data = analyzer.extract_session_data(most_recent.path)
    print(analyzer.format_for_analysis(data))
    print('---')
"
```

## Analysis Guidelines

When analyzing session data:

1. **Read each prompt carefully** - understand intent, not just keywords
2. **Track the arc** - how did the session progress?
3. **Identify outcomes** - what changed as a result?
4. **Note decisions** - what choices were made and why?
5. **Find blockers** - what didn't get resolved?

## Daily Note Output

Session analysis is saved to a daily note at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**Format**: `20251219-daily.md` (strict naming)

### Core Format: Task Lists by Project

The daily note is **task lists grouped by project**. That's it.

Each project section:
- `## PROJECT-NAME → [[projects/link]]` heading
- Progress bar (auto-generated)
- Task list: `- [x]` completed, `- [ ]` incomplete
- Notes/observations as plain bullets (no checkbox)

### Session Analyzer's Job

When updating the daily note, the session analyzer:

1. **Reads existing content** - preserves ALL tasks and notes
2. **Adds new accomplishments** - from session data, as `- [x]` items
3. **Adds new blockers/issues** - as `- [ ]` items
4. **Cleans up formatting** - converts messy input to clean task format
5. **Deduplicates** - same task mentioned twice → keep one
6. **Never loses information** - if in doubt, keep it

### Formatting Rules

**Convert user notes to task format:**
- `- some task I did` → `- [x] some task I did`
- `- TODO: something` → `- [ ] something`
- `- [outcome] thing` → `- [x] thing`
- `- [blocker] issue` → `- [ ] issue (BLOCKING)`

**Keep as plain bullets (no checkbox):**
- Observations, decisions, notes that aren't tasks
- Reference information (like schema observations)

### Non-Destructive Merge (Cross-Machine Safety)

When merging session data from different machines:
1. Parse existing project sections
2. For each new item, check if similar content exists (fuzzy match)
3. If exists: skip or update
4. If new: append to appropriate project section
5. **Never delete** - only add or enrich

This ensures remote sessions don't overwrite local session data.

### Rich Linking (MANDATORY)

Before writing, search bmem for link targets:

```python
mcp__bmem__search_notes(query="task topic", project="main")
mcp__bmem__search_notes(query="projects/name", project="main")
```

Use wikilinks:
- **Projects**: `[[projects/PROJECT-NAME]]`
- **Decisions**: `[[projects/aops/decisions/TITLE]]`
- **Tasks**: `[[tasks/inbox/FILENAME]]`

### Daily Note Structure

```markdown
---
title: Daily Summary - YYYY-MM-DD
type: session_log
permalink: sessions-YYYYMMDD-daily
tags: [daily, sessions]
---

# Daily Summary - YYYY-MM-DD

## 🎯 PRIMARY: TJA Paper → [[projects/tja]]
████░░░░░░░░░░░░░░░░ 3/10

- [x] ExecutionTrace schema cleanup (Phases 1-4)
- [x] Data quality explorer page
- [x] Verify BigQuery serializability
- [ ] Fix buttermilk hash/save recursion (BLOCKING)
- [ ] Test trans workflow end-to-end
- [ ] Run full reliability batch
- [ ] Draft methods section
- [ ] Phase 5: Config URI reference
- [ ] Phase 6: Schema validation tests

**Notes:**
- Schema observation: move `bm` config to `session_info`
- Schema observation: delete `agent_info.config` entirely

## SECONDARY: Framework → [[projects/aops]]
██████░░░░░░░░░░░░░░ 7/22

- [x] reference-map skill
- [x] link-audit skill
- [x] Session analyzer v2.0
- [x] GEMINI.md
- [x] Merged analyze-session into session-analyzer
- [x] CSV export for Cosmograph
- [x] Markdown dashboard generator
- [ ] Live session dashboard
- [ ] Convince Gemini to read Claude skills
- [ ] teach claude about obsidian links
- [ ] get evidence out of heuristic document
- [ ] transcript improvements

## FILLER: Admin

- Email triage
- OSB items (secure device)
```

**Key points:**
- Tasks are `- [x]` or `- [ ]`
- Notes/observations go under `**Notes:**` as plain bullets
- Every checkbox item counts toward progress bar
- No separate "Session Details" section needed

## Regenerating Progress Bars

After updating the daily note, regenerate per-section progress bars:

```bash
cd $AOPS && uv run python -c "
from lib.session_analyzer import update_daily_note_dashboard
update_daily_note_dashboard()  # Uses today's date
"
```

This parses each priority section and inserts a progress bar showing completed/total tasks for that section only.

## Architecture

- **Data layer**: `lib/session_analyzer.py` (extraction, no LLM)
- **Parsing**: `lib/session_reader.py` (JSONL → structured turns)
- **Progress bars**: `lib/session_analyzer.py` (`update_daily_note_dashboard()`)
- **Analysis**: This skill (LLM-powered semantic understanding)
- **Storage**: bmem (optional, for significant findings)
