---
name: analyze-session
description: Analyze a Claude Code session to extract accomplishments, decisions, and topics
allowed-tools: Read,Bash,Skill,Write,Edit,mcp__bmem__write_note,mcp__bmem__edit_note
---

# /analyze-session

Analyze a Claude Code session using the session-analyzer skill.

## Arguments

- `$ARGUMENTS` - Optional session ID (partial match) or "today" for all today's sessions

## Process

1. Invoke the session-analyzer skill
2. Load and format session data
3. Provide semantic analysis of what happened
4. **Save analysis to daily note** at `$ACA_DATA/sessions/YYYYMMDD-daily.md`

```
Skill(skill="session-analyzer")
```

Then run:

```bash
cd $AOPS && uv run python -c "
from lib.session_analyzer import SessionAnalyzer, get_recent_sessions

analyzer = SessionAnalyzer()

# Check for arguments
args = '$ARGUMENTS'.strip()

if args == 'today':
    # Analyze today's sessions
    sessions = get_recent_sessions(hours=24)
    for data in sessions[:5]:
        print(analyzer.format_for_analysis(data))
        print('---')
elif args:
    # Find specific session
    path = analyzer.find_session(session_id=args)
    if path:
        data = analyzer.extract_session_data(path)
        print(analyzer.format_for_analysis(data))
    else:
        print(f'Session not found: {args}')
else:
    # Most recent session
    path = analyzer.find_session()
    if path:
        data = analyzer.extract_session_data(path)
        print(analyzer.format_for_analysis(data))
    else:
        print('No sessions found')
"
```

After viewing the session data, analyze it semantically and provide:

1. **Accomplishments** - What got done?
2. **Decisions** - What choices were made?
3. **Topics** - What areas were worked on?
4. **Blockers** - What's stuck?
5. **Next steps** - What should happen next?

## Save to Daily Note (MANDATORY)

After completing analysis, save results to the daily note:

**File**: `$ACA_DATA/sessions/YYYYMMDD-daily.md` (e.g., `20251218-daily.md`)

### If file doesn't exist, create it:

```markdown
---
title: Daily Session Summary - YYYY-MM-DD
type: session_log
permalink: sessions-YYYYMMDD-daily
tags:
  - daily
  - sessions
created: YYYY-MM-DDTHH:MM:SSZ
updated: YYYY-MM-DDTHH:MM:SSZ
---

## Sessions

[session analysis here]
```

### If file exists, append the session analysis

Use Edit tool to append after `## Sessions` section, or use `mcp__bmem__edit_note` with operation `append`.

### Session Entry Format

```markdown
### Session: <id> (<project>, <duration>min)

**Accomplishments:**
- Item 1
- Item 2

**Decisions:**
- Decision 1

**Topics:** topic1, topic2

**Blockers:** (if any)

---
```
