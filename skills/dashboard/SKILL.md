---
name: dashboard
description: Cognitive Load Dashboard - Live Streamlit dashboard for task visibility and session activity monitoring.
allowed-tools: Read,Bash,Skill
version: 1.2.0
permalink: skills-dashboard-skill
---

# Cognitive Load Dashboard

Single Streamlit dashboard answering three questions: What to do? What doing? What done?

## Overview

Live web dashboard displaying high-priority tasks and Claude Code session activity across all projects. Designed for desktop monitoring and mobile/tablet access when away from desk.

## Running

```bash
cd $AOPS && uv run streamlit run skills/dashboard/dashboard.py
```

## Access

- **Desktop**: http://localhost:8501
- **Tablet/Phone**: http://<desktop-ip>:8501

## Components

Each piece of information appears **exactly once** in the most appropriate location.

### Three-Question Layout (Primary View)
Answers the core cognitive questions at a glance:
- **WHAT SHOULD I DO?** - Primary focus + P0/P1 priority tasks
- **WHAT AM I DOING?** - Session summaries from synthesis.json
- **WHAT DID I DO TODAY?** - Accomplishments grouped by project

### Focus Synthesis Panel
LLM-generated insights from session-insights skill (synthesis.json):
- **Today's Story** - Narrative of the day's work
- **Next Action** - Recommended next task with reasoning
- **Alignment** - On track / blocked / drifted status
- **Session Insights** - Skill compliance, corrections, failures, context gaps

### Blockers Panel
Items marked as blockers in daily notes. Red-themed for visibility.

### Project Cards
Per-project detailed view showing:
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
