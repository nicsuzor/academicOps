---
name: framework-paths
title: Framework Paths (Generated)
category: reference
type: reference
description: Resolved absolute paths for this framework instance (generated from paths.py)
audience: agents
generated: 2026-01-24T01:47:41.796000+00:00
permalink: framework-paths
tags:
  - framework
  - paths
  - generated
---

# Framework Paths

**⚠️ GENERATED FILE - DO NOT EDIT MANUALLY**

Generated: 2026-01-24 01:47:41 UTC
Source: `aops-core/lib/paths.py`

This file provides resolved absolute paths for agent use during sessions.
All paths are expanded to absolute values at generation time.

## Resolved Paths

These are the concrete absolute paths for this framework instance:

| Path Variable | Resolved Path |
|--------------|---------------|
| $AOPS        | /home/nic/writing/aops   |
| $ACA_DATA    | /home/nic/writing/data   |

## Framework Directories

Framework component directories within $AOPS:

| Directory | Absolute Path |
|-----------|---------------|
| Specs     | /home/nic/writing/aops/specs   |
| Workflows | /home/nic/writing/aops/aops-core/workflows |
| Skills    | /home/nic/writing/aops/aops-core/skills  |
| Hooks     | /home/nic/writing/aops/aops-core/hooks   |
| Commands  | /home/nic/writing/aops/aops-core/commands |
| Agents    | /home/nic/writing/aops/aops-core/agents  |
| Tests     | /home/nic/writing/aops/tests   |
| Config    | /home/nic/writing/aops/config  |

## Data Directories

User data directories within $ACA_DATA:

| Directory | Absolute Path |
|-----------|---------------|
| Sessions  | /home/nic/writing/sessions |
| Projects  | /home/nic/writing/data/projects |
| Logs      | /home/nic/writing/data/logs     |
| Context   | /home/nic/writing/data/context  |
| Goals     | /home/nic/writing/data/goals    |

---

**Generation Command**: `python3 aops-core/scripts/generate_framework_paths.py`

Run this script after changing $AOPS or $ACA_DATA environment variables,
or after modifying the framework directory structure.
