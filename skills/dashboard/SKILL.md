---
name: dashboard
category: instruction
description: Cognitive Load Dashboard - Live Streamlit dashboard for task visibility and session activity monitoring.
allowed-tools: Read,Bash,Skill
version: 2.0.0
permalink: skills-dashboard-skill
---

# Cognitive Load Dashboard

Unified Focus Dashboard - glance and know exactly what's going on.

## Overview

Single-page dashboard combining synthesis insights with project tasks. Opens directly to Focus Synthesis panel. No redundant sections - each piece of information appears exactly once.

## Running

```bash
cd $AOPS && uv run streamlit run skills/dashboard/dashboard.py
```

## Access

- **Desktop**: http://localhost:8501
- **Tablet/Phone**: http://<desktop-ip>:8501

## Layout

### Focus Synthesis Panel (Top)
Pre-computed insights from synthesis.json:
- **Today's Story** - Narrative bullets of the day's work
- **Status Cards** - Done count, alignment status, blocked items
- **Session Insights** - Skill compliance, corrections, context gaps

### Project Cards (Integrated Grid)
Per-project cards with unified styling:
- **Priority Tasks** - P0 (red), P1 (orange), P2 (purple) badges
- **Accomplishments** - Compact green checkmarks
- Sorted by task count (projects with work first)
- Color-coded headers by project (Peacock theme)

## Architecture

### Data Sources

| Source | Implementation |
|--------|----------------|
| Task files | `skills.tasks.task_loader.load_focus_tasks()` |
| Session JSONLs | `lib.session_reader.SessionProcessor` |
| Daily notes | `lib.session_analyzer.SessionAnalyzer.parse_daily_log()` |
| Cross-machine prompts | `fetch_cross_machine_prompts()` via Cloudflare R2 |
| Git activity | `get_project_git_activity()` subprocess |
| Session Insights | Pre-mined from `$ACA_DATA/dashboard/synthesis.json` (created by session-insights skill, not via Claude API) |

### Session Discovery

Uses `lib/session_reader.py` module that reads:
- Claude session JSONL (`*.jsonl`)
- Agent transcripts (`agent-*.jsonl`)
- Hook logs (`*-hooks.jsonl`)

Same parser used by `/transcript` skill for markdown export.

### Dashboard Synthesis (No Claude API)

**CRITICAL**: Dashboard does NOT call Claude API. It loads pre-computed data from `$ACA_DATA/dashboard/synthesis.json`, created offline by session-insights skill via Gemini mining. This keeps dashboard fast and reduces API dependencies.

Dashboard sources for Session Insights Panel:
- synthesis.json structure (skill compliance, corrections, failures, successes)
- Top context gaps extracted from failure analysis
- Metrics aggregated per-session then rolled up to daily view

If synthesis.json is missing or stale: Dashboard will show a warning prompting you to run session-insights skill.
