---
name: session-analyzer
description: Analyze Claude Code session logs to extract semantic meaning - accomplishments, decisions, topics, blockers.
allowed-tools: Read,Bash,Write,Edit,mcp__bmem__write_note,mcp__bmem__edit_note,mcp__bmem__search_notes
version: 1.2.0
permalink: skills-session-analyzer
---

# Session Analyzer Skill

Analyze Claude Code session logs to extract semantic meaning using LLM understanding (not keyword matching). Produces curated daily summaries grouped by project.

## When to Use

- "What did I accomplish today?"
- "Summarize this session"
- "What decisions were made?"
- "What's been happening in my sessions?"
- `/session-analyzer` command

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
5. **Save to daily note**

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

**Format**: `20251218-daily.md` (strict naming)

### Daily Note Philosophy

**Curate, don't list.** The daily note is for things worth remembering - not an undifferentiated log. Use discretion:

- **Include**: Significant accomplishments, important decisions, blockers, things left undone
- **Omit**: Routine commits, trivial file edits, mechanical operations
- **Focus on**: What would the user need to know if looking back in a week/month?

### Organization: By Project

Group work by **project** using `## project-name` headings. Combine multiple sessions working on the same project. Don't list each session separately.

### Rich Linking (MANDATORY)

Before writing daily note, search bmem for link targets:

```python
# Find related tasks
mcp__bmem__search_notes(query="task topic", project="main")

# Find project notes
mcp__bmem__search_notes(query="projects/name", project="main")
```

Use wikilinks to connect to the knowledge graph:
- **Tasks**: `[[tasks/inbox/FILENAME]]`
- **Projects**: `[[projects/PROJECT-NAME]]`
- **Decisions**: `[[projects/aops/decisions/TITLE]]`
- **Contacts**: `[[contacts/NAME]]`

### Daily Note Structure

```markdown
---
title: Daily Summary - YYYY-MM-DD
type: session_log
permalink: sessions-YYYYMMDD-daily
tags: [daily, sessions]
---

## In Progress
<!-- Active work - supports "what's happening / resume specific task" -->
- **[[projects/PROJECT]]**: Current focus → next: immediate next step

## Ready to Start
<!-- Priority queue - supports "what should I pick up" -->
1. Next priority item
2. Second priority

---

## project-name
- [outcome] What was completed
- [decision] Choice made and why
- [blocker] What's stuck
- [ ] Incomplete task
- [x] Completed task

---
## Session Log
<!-- Reserved for future machine-readable data -->
```

### Item Format

Use bmem observation categories for bullet points:
- `[outcome]` - What was completed
- `[decision]` - Choice made and rationale
- `[blocker]` - What's stuck
- `[insight]` - Key realization
- `[problem]` - Issue identified

Use task checkbox format for tasks:
- `- [ ] Incomplete task`
- `- [x] Completed task`

## Architecture

- **Data layer**: `lib/session_analyzer.py` (extraction, no LLM)
- **Parsing**: `lib/session_reader.py` (JSONL → structured turns)
- **Analysis**: This skill (LLM-powered semantic understanding)
- **Storage**: bmem (optional, for significant findings)
