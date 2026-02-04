---
name: framework-paths
title: Framework Paths (Plugin Architecture)
category: reference
type: reference
description: Path conventions for plugin-only architecture
audience: agents
permalink: framework-paths
tags:
  - framework
  - paths
  - plugin
---

# Framework Paths

## Plugin Architecture

In the plugin-only architecture, the framework consists of plugins managed by Claude/Gemini.
Paths are resolved relative to the plugin root, not a monorepo location.

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `$CLAUDE_PLUGIN_ROOT` | Root of the aops-core plugin (set by Claude) | Yes (for Claude) |
| `$ACA_DATA` | User data directory | Yes |

**Note**: `$AOPS` is no longer used. Use `$CLAUDE_PLUGIN_ROOT` for plugin-relative paths.

## Plugin Directories

Relative to `$CLAUDE_PLUGIN_ROOT` (aops-core plugin):

| Directory | Relative Path |
|-----------|---------------|
| Skills    | `skills/` |
| Commands  | `commands/` |
| Hooks     | `hooks/` |
| Agents    | `agents/` |
| Workflows | `workflows/` |
| Indices   | `indices/` |
| Lib       | `lib/` |

## Data Directories

Relative to `$ACA_DATA`:

| Directory | Relative Path |
|-----------|---------------|
| Daily     | `daily/` |
| Projects  | `projects/` |
| Tasks     | `tasks/` |
| Logs      | `logs/` |
| Context   | `context/` |
| Goals     | `goals/` |
| HDR       | `hdr/` |

## Sessions Directory

Sessions are stored at `$ACA_DATA/../sessions/` (sibling of data directory).

## Path Resolution in Code

For Python code within the plugin, use relative paths from `__file__`:

```python
from pathlib import Path

# Get plugin root from this file's location
PLUGIN_ROOT = Path(__file__).resolve().parent.parent  # Adjust .parent count as needed

# Access plugin resources
skills_dir = PLUGIN_ROOT / "skills"
hooks_dir = PLUGIN_ROOT / "hooks"
```

For data access, use the environment variable:

```python
import os
from pathlib import Path

data_root = Path(os.environ["ACA_DATA"])
daily_dir = data_root / "daily"
```
