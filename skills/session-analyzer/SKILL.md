---
name: session-analyzer
description: Analyze Claude Code session logs to extract semantic meaning - accomplishments, decisions, topics, blockers.
allowed-tools: Read,Bash
version: 1.0.0
permalink: skills-session-analyzer
---

# Session Analyzer Skill

Analyze Claude Code session logs to extract semantic meaning using LLM understanding (not keyword matching).

## When to Use

- "What did I accomplish today?"
- "Summarize this session"
- "What decisions were made?"
- "What's been happening in my sessions?"

## Process

1. **Load session data** using `lib/session_analyzer.py`
2. **Review prompts and outcomes** presented in context
3. **Extract semantic meaning**:
   - Accomplishments (what got done)
   - Decisions (choices made)
   - Topics (what areas were worked on)
   - Blockers (what's stuck)
   - Next steps (what's pending)

## Usage

```bash
# Load session data for analysis
cd $AOPS && uv run python -c "
from lib.session_analyzer import SessionAnalyzer, get_recent_sessions

# Most recent session
analyzer = SessionAnalyzer()
path = analyzer.find_session()
if path:
    data = analyzer.extract_session_data(path)
    print(analyzer.format_for_analysis(data))
"
```

## Output Format

After analyzing the session context, provide structured output:

```yaml
session: <id>
project: <name>
duration: <minutes>

accomplishments:
  - "Description of what was completed"
  - "Another completed item"

decisions:
  - "Choice that was made and why"

topics:
  - topic1
  - topic2

blockers:
  - "What's stuck or needs attention"

next_steps:
  - "What should happen next"
```

## Finding Sessions

```bash
# List recent sessions
cd $AOPS && uv run python -c "
from lib.session_reader import find_sessions
for s in find_sessions()[:5]:
    print(f'{s.session_id[:8]} - {s.project_display} - {s.last_modified}')"

# Specific project
cd $AOPS && uv run python -c "
from lib.session_reader import find_sessions
for s in find_sessions(project='writing')[:5]:
    print(f'{s.session_id[:8]}')"
```

## Analysis Guidelines

When analyzing session data:

1. **Read each prompt carefully** - understand intent, not just keywords
2. **Track the arc** - how did the session progress?
3. **Identify outcomes** - what changed as a result?
4. **Note decisions** - what choices were made and why?
5. **Find blockers** - what didn't get resolved?

## Integration with bmem

After analysis, consider documenting significant findings:

```python
# If session contained important decisions or patterns
mcp__bmem__write_note(
    title="Session Analysis: <topic>",
    folder="sessions",
    content="...",
    project="main"
)
```

## Architecture

- **Data layer**: `lib/session_analyzer.py` (extraction, no LLM)
- **Parsing**: `lib/session_reader.py` (JSONL → structured turns)
- **Analysis**: This skill (LLM-powered semantic understanding)
- **Storage**: bmem (optional, for significant findings)
