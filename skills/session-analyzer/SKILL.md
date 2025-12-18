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

## Daily Note Output

Session analysis is saved to a daily note at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**Format**: `20251218-daily.md` (strict naming)

The daily note accumulates all session analyses for that day, enabling:
- End-of-day review of accomplishments
- Dashboard integration for progress tracking
- Historical record of work patterns

### Daily Note Structure

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

### Session: <id> (<project>, <duration>)

**Accomplishments:**
- Item 1
- Item 2

**Decisions:**
- Decision 1

**Topics:** topic1, topic2

**Blockers:** (if any)

---
```

## Architecture

- **Data layer**: `lib/session_analyzer.py` (extraction, no LLM)
- **Parsing**: `lib/session_reader.py` (JSONL → structured turns)
- **Analysis**: This skill (LLM-powered semantic understanding)
- **Storage**: bmem (optional, for significant findings)
