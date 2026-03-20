---
name: recap
type: skill
category: analysis
description: Reconstruct plain-English narrative of recent work from session summaries
triggers:
  - "what was i working on"
  - "what have i been doing"
  - "recap my sessions"
  - "where did i get distracted"
  - "work narrative"
  - "session recap"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
  - analysis
allowed-tools: Bash,Read,Glob,Grep
version: 1.0.0
tags:
  - analysis
  - sessions
  - narrative
permalink: skills-recap
---

# Recap Skill

> **Taxonomy note**: This skill provides analysis (HOW) for reconstructing narrative context from session summaries. See [[TAXONOMY.md]] for the skill/workflow distinction.

Reads session summary files to reconstruct a plain-English narrative of what the user was working on, where attention shifted, and what got derailed.

## Overview

This skill analyzes the JSON session summaries in `$AOPS_SESSIONS/summaries/` to produce:

- A chronological narrative of work across sessions
- Detection of context switches and topic drift
- Identification of unfinished threads and distractions
- Summary of what actually got accomplished vs attempted

## Usage

```bash
/recap              # Last 3 days (default)
/recap 7            # Last 7 days
/recap today        # Today only
/recap yesterday    # Yesterday only
```

## Workflow

### Step 1: Collect Session Summaries

```python
import json, os, glob
from datetime import datetime, timedelta, timezone

# Parse arguments
days = 3  # default, or parse from args
summaries_dir = os.path.join(os.environ.get('AOPS_SESSIONS', os.path.expanduser('~/.polecat/sessions')), 'summaries')

# Calculate date range
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=days)

# Find all summary files in range
all_files = sorted(glob.glob(os.path.join(summaries_dir, '*.json')))

sessions = []
for f in all_files:
    basename = os.path.basename(f)

    # Skip auto-commit sessions — they're noise
    if 'commit-changed' in basename or basename.startswith('sessions-'):
        continue

    with open(f) as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            continue

    # Parse date from the JSON data
    date_str = data.get('date', '')
    if not date_str:
        continue

    try:
        # Handle ISO format with timezone
        session_date = datetime.fromisoformat(date_str)
        if session_date.tzinfo is None:
            session_date = session_date.replace(tzinfo=timezone.utc)
        if session_date.astimezone(timezone.utc) < start_date:
            continue
    except (ValueError, TypeError):
        continue

    # Extract user prompts from timeline events
    prompts = []
    for event in data.get('timeline_events', []):
        if event.get('type') == 'user_prompt':
            prompts.append(event.get('description', ''))

    sessions.append({
        'file': basename,
        'session_id': data.get('session_id', ''),
        'date': date_str,
        'project': data.get('project', 'unknown'),
        'summary': data.get('summary'),
        'outcome': data.get('outcome'),
        'accomplishments': data.get('accomplishments', []),
        'friction_points': data.get('friction_points', []),
        'proposed_changes': data.get('proposed_changes', []),
        'prompts': prompts,
        'duration_min': data.get('token_metrics', {}).get('efficiency', {}).get('session_duration_minutes', 0),
        'tokens_out': data.get('token_metrics', {}).get('totals', {}).get('output_tokens', 0),
    })

# Sort chronologically
sessions.sort(key=lambda s: s['date'])
```

### Step 2: Build the Narrative

Group sessions by date (calendar day), then within each day by project. For each session, note:

1. **What was the user trying to do?** (from `prompts` and `summary`)
2. **Did they finish?** (from `outcome` and `accomplishments`)
3. **Where did attention shift?** (project changes, topic changes mid-session)
4. **What friction occurred?** (from `friction_points`)

### Step 3: Detect Context Switches and Distractions

A **context switch** is when the project changes between consecutive sessions, or when the user's prompts within a session shift topic significantly.

A **distraction** is a context switch to a short session (< 5 min or < 500 output tokens) that doesn't produce accomplishments — it suggests the user poked at something and then came back.

A **rabbit hole** is a long session (> 30 min) that started as one thing but the prompts show it evolved into something different.

An **unfinished thread** is a session where the user asked about something but the outcome is null or the accomplishments are empty, and there's no follow-up session on the same topic.

### Step 4: Generate Output

Present the narrative as a readable story, organized by day. Use this structure:

```markdown
## [Day, Date]

### Morning / Afternoon / Evening (based on timestamps)

**[Project]**: [What was being worked on, in plain English]

- [Key prompts paraphrased]
- [Outcome: what was accomplished or left unfinished]

→ _Context switch_: [why this looks like a switch — different project, different topic]

### Distraction detector

- [Short sessions that didn't produce results]
- [Topic jumps that suggest the user got pulled away]

### Threads left hanging

- [Topics started but not completed, with no follow-up]
```

### Step 5: Provide a Summary

At the end, include:

```markdown
## Overall

**Main threads**: [The 2-3 primary things the user was actually trying to accomplish]

**Biggest distractions**: [What pulled attention away most often]

**Completion rate**: [X of Y substantive sessions produced concrete outcomes]

**Suggestion**: [Based on the pattern, what should the user focus on next]
```

## Filtering Rules

- **Skip** sessions whose filename starts with `sessions-` (auto-commit bots)
- **Skip** sessions with `commit-changed` in the filename
- **Skip** polecat worker sessions (project field matches a short hex hash, e.g. `^[a-f0-9]{7,8}$`)
- **Include** sessions even if summary is null — use prompts to infer intent
- **Highlight** sessions where summary exists and is substantive

## Handling Missing Data

Many sessions have `null` summaries (insights not generated). For these:

1. Use `timeline_events[].description` (user prompts) to infer what was happening
2. Use `project` to group by workstream
3. Use `token_metrics.efficiency.session_duration_minutes` to gauge depth of engagement
4. If a session has no prompts AND no summary, skip it silently

## Tips

- Sessions on the `aops` project are framework development work
- Sessions on `diffie`, `galileo`, `brain`, `mem` etc. are research/content projects
- Very short sessions (< 1 min) with few tokens are usually quick checks or tests
- Sessions with `/aops-core:strategy` or `/daily` prompts are planning/reflection, not production work
- Multiple sessions on the same project in sequence suggest focused work; interleaved projects suggest multitasking

## See Also

- `/session-insights` - Generate detailed insights for individual sessions
- `/daily` - Daily briefing and planning
- `/path` - Narrative path reconstruction from session transcripts
