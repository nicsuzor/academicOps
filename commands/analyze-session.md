---
name: analyze-session
description: Analyze a Claude Code session to extract accomplishments, decisions, and topics
allowed-tools: Read,Bash,Skill
---

# /analyze-session

Analyze a Claude Code session using the session-analyzer skill.

## Arguments

- `$ARGUMENTS` - Optional session ID (partial match) or "today" for all today's sessions

## Process

1. Invoke the session-analyzer skill
2. Load and format session data
3. Provide semantic analysis of what happened

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
