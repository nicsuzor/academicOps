# Cognitive Load Dashboard

Single Streamlit dashboard for task visibility and cognitive load monitoring.

## Overview

Live web dashboard displaying high-priority tasks and activity status. Designed for desktop monitoring and mobile/tablet access when away from desk.

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
- "What happened today?" (Phase 2)

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
- Auto-refresh every 30s

### Activity Log (Phase 2) 🚧
Planned: Show recent task state changes, completions, and priority updates.

### Task Summary 🚧
Planned: Aggregate metrics (task counts, priority distribution, completion rate).

## Current Status

**Phase 1**: Complete
- Focus Panel implemented and working
- Connects to task system via task_loader
- Auto-refresh mechanism active
- Error handling for failed loads

**Phase 2**: Pending
- Activity log implementation
- Task summary metrics
- Enhanced filtering/sorting

## Technical Notes

- Uses `skills.tasks.task_loader.load_focus_tasks()` to access task data
- Streamlit auto-refresh (30s) ensures dashboard stays current
- Error handling prevents crashes on task load failures
- Responsive layout works on mobile devices
