---
name: analyze-session
description: Analyze Claude Code sessions and produce curated daily summary grouped by project
allowed-tools: Read,Bash,Skill,Write,Edit,mcp__bmem__write_note,mcp__bmem__edit_note,mcp__bmem__search_notes
---

# /analyze-session

Analyze Claude Code sessions and produce a **curated daily summary** grouped by project.

## Arguments

- `$ARGUMENTS` - Optional: session ID, date (YYYYMMDD), or "today"

## Process

1. Invoke session-analyzer skill for guidance
2. Load session data for the target date
3. **Curate**: Focus on significant items, not everything
4. **Group by project**: Combine sessions working on same project
5. **Add rich links**: Search bmem to link tasks, decisions, contacts
6. **Save to daily note**

```
Skill(skill="session-analyzer")
```

Then load session data:

```bash
cd $AOPS && uv run python -c "
from lib.session_reader import find_sessions
from lib.session_analyzer import SessionAnalyzer
from datetime import datetime, timezone, timedelta

# Parse arguments for date
args = '$ARGUMENTS'.strip()
if args.isdigit() and len(args) == 8:
    # Date format YYYYMMDD
    target = datetime(int(args[:4]), int(args[4:6]), int(args[6:8]), tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
else:
    # Default to today
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

**Curate, don't list.** Ask: "Would the user care about this in a week?"

- **Include**: Significant accomplishments, important decisions, blockers, incomplete work
- **Omit**: Routine commits, trivial edits, mechanical operations
- **Group**: Combine all sessions for same project into one section

## Rich Linking (MANDATORY)

Before writing daily note, search bmem for link targets:

```python
# Find related tasks
mcp__bmem__search_notes(query="wikijuris video", project="main")

# Find project notes
mcp__bmem__search_notes(query="projects/omcp", project="main")
```

Use wikilinks: `[[tasks/inbox/FILENAME]]`, `[[projects/NAME]]`, `[[contacts/NAME]]`

## Daily Note Format

**File**: `$ACA_DATA/sessions/YYYYMMDD-daily.md`

```markdown
---
title: Daily Summary - YYYY-MM-DD
type: session_log
permalink: sessions-YYYYMMDD-daily
tags: [daily, sessions]
created: YYYY-MM-DDTHH:MM:SSZ
---

## Summary

2-3 sentences: What was the focus today? Major outcomes?

## By Project

### [[projects/project-name]]

**Accomplished:**
- Significant item ([[link-to-task]] if exists)
- Another significant item

**Decisions:**
- Choice made and why

**Left undone:**
- What's pending ([[link-to-task]])

### [[projects/another-project]]

...

## Blockers

Cross-project issues requiring attention.
```
