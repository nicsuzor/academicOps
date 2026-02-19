---
name: framework-refresh
category: instruction
description: Regenerate framework indices, task graphs, and dashboard artifacts.
allowed-tools: Read,Bash,Grep,Write,Edit,Skill
version: 1.0.0
permalink: skills-framework-refresh
---

# Framework Refresh Skill

Regenerate all framework indices and visualizations to ensure the dashboard and memory server are up to date.

## When to Use

- After making significant changes to tasks or documentation
- When the Overwhelm Dashboard shows stale data
- Before starting a new major project phase
- As part of a scheduled maintenance routine

## Workflow

### 1. Run Framework Refresh Script

The primary method is to run the unified refresh script:

```bash
uv run python $AOPS/aops-core/scripts/framework_refresh.py
```

This script handles:
- Core task index regeneration (via `fast-indexer`)
- Knowledge graph generation
- Dashboard task map rendering (SVG)
- Memory server synchronization
- Freshness tracking

### 2. Manual Verification

After running the script, verify:
- `${ACA_DATA}/tasks/index.json` is updated
- `${ACA_DATA}/outputs/task-map.svg` exists and is recent
- Memory server queries return new content

## Success Criteria

- `index.json` is updated with recent changes
- `task-map.svg` is regenerated and visible in the dashboard
- Memory server returns results including new content
- No errors during index generation or rendering
