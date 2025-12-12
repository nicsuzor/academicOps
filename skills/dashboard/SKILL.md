# Cognitive Load Dashboard

Single Streamlit dashboard for task visibility and session activity monitoring.

## Overview

Live web dashboard displaying high-priority tasks and Claude Code session activity across all projects. Designed for desktop monitoring and mobile/tablet access when away from desk.

**Target reliability**: 100% (vs task_view.py ~50% failure rate)

## Problems Solved

1. **Terminal indistinguishability** - Tasks buried in terminal history
2. **task_view.py unreliability** - ~50% failure rate makes it unusable
3. **No activity log** - Can't see what happened while away
4. **Static visualization** - Excalidraw dashboards don't auto-update
5. **Away-from-desk blindness** - No mobile/tablet access to task state

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

### Focus Panel (P0/P1 Tasks) ✅
Displays up to 5 highest-priority tasks with:
- Priority badge (🔴 P0, 🟡 P1, 🔵 P2, ⚪ P3)
- Task title
- Project classification
- Auto-refresh every 10s

### Activity Log ✅
Shows recent activity from ALL Claude Code sessions:
- User prompts (with preview)
- Significant tool operations (Edit, Write, Task, Bash)
- Session identification and color-coding
- No time limit - can see activity from any session

### Active Sessions ✅
Overview of all discovered sessions grouped by project, each showing:
- First user prompt (what started the session)
- Most recent user prompt (current state)
- Most recent bmem documentation write (if any)
- Time since last activity

## Architecture

Uses unified `lib/session_reader.py` module that reads:
- Claude session JSONL (`*.jsonl`)
- Agent transcripts (`agent-*.jsonl`)
- Hook logs (`*-hooks.jsonl`)

Same parser used by `/transcript` skill for markdown export.

## Technical Notes

- Uses `lib.session_reader.SessionProcessor` for parsing all session data
- Uses `lib.session_reader.find_sessions()` for session discovery
- Uses `skills.tasks.task_loader.load_focus_tasks()` for task data
- Auto-refresh every 10 seconds
- Error handling prevents crashes on parse failures
- Responsive layout works on mobile devices
