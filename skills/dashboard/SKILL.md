---
name: dashboard
description: Cognitive Load Dashboard - Live Streamlit dashboard for task visibility and session activity monitoring.
allowed-tools: Read,Bash,Skill
version: 1.1.0
permalink: skills-dashboard-skill
---

# Cognitive Load Dashboard

Single Streamlit dashboard for task visibility and session activity monitoring.

## Overview

Live web dashboard displaying high-priority tasks and Claude Code session activity across all projects. Designed for desktop monitoring and mobile/tablet access when away from desk.

## Problems Solved

1. **Terminal indistinguishability** - Tasks buried in terminal history
2. **No activity log** - Can't see what happened while away
3. **Static visualization** - Excalidraw dashboards don't auto-update
4. **Away-from-desk blindness** - No mobile/tablet access to task state
5. **Cross-machine blindness** - No view of activity on other machines

## When to Use

- "Check task priorities"
- "What's urgent?"
- "Show me focus tasks"
- "What happened today?"
- "What sessions are active?"

## Running

```bash
cd $AOPS && uv run streamlit run skills/dashboard/dashboard.py
```

## Access

- **Desktop**: http://localhost:8501
- **Tablet/Phone**: http://<desktop-ip>:8501

## Components

### NOW Panel
Primary focus from daily notes. Shows current task, next action, and progress bar.

### Blockers Panel
Items marked as blockers in daily notes. Red-themed for visibility.

### Done Today Panel
Completed tasks and outcomes from daily notes.

### Cross-Machine Activity Panel
Recent prompts from all machines via Cloudflare R2. Grouped by hostname.

**Requirements**: Set `PROMPT_LOG_API_KEY` environment variable.

### Project Cards
Per-project aggregated view showing:
- Accomplishments (from daily notes)
- Priority tasks (P0/P1)
- Memory notes (from sessions)
- Git commits (last 24h)

Color-coded by project (matches Peacock theme).

## Architecture

### Data Sources

| Source | Implementation |
|--------|----------------|
| Task files | `skills.tasks.task_loader.load_focus_tasks()` |
| Session JSONLs | `lib.session_reader.SessionProcessor` |
| Daily notes | `lib.session_analyzer.SessionAnalyzer.parse_daily_log()` |
| Cross-machine prompts | `fetch_cross_machine_prompts()` via Cloudflare R2 |
| Git activity | `get_project_git_activity()` subprocess |

### Session Discovery

Uses `lib/session_reader.py` module that reads:
- Claude session JSONL (`*.jsonl`)
- Agent transcripts (`agent-*.jsonl`)
- Hook logs (`*-hooks.jsonl`)

Same parser used by `/transcript` skill for markdown export.

## Technical Notes

- Auto-refresh every 10 seconds
- Error handling prevents crashes on parse failures
- Responsive layout works on mobile devices

## Spec

See [[Cognitive Load Dashboard Spec]] for acceptance criteria and user story.
