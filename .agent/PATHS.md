---
name: agent-paths
title: Agent Paths (Generated)
category: reference
type: reference
description: Resolved absolute paths for this framework instance (generated from paths.py)
audience: agents
generated: 2026-01-28T06:34:14.081874+00:00
permalink: agent-paths
tags:
  - framework
  - paths
  - generated
---

# Agent Paths

**⚠️ GENERATED FILE - DO NOT EDIT MANUALLY**

Generated: 2026-01-28 06:34:14 UTC
Source: `aops-core/lib/paths.py`

This file provides resolved absolute paths for agent use during sessions.
All paths are expanded to absolute values at generation time.

## Resolved Paths

These are the concrete absolute paths for this framework instance:

| Path Variable | Resolved Path |
|--------------|---------------|
| $AOPS        | /home/nic/src/academicOps   |
| $ACA_DATA    | /home/nic/writing/data   |

## Framework Directories

Framework component directories within $AOPS:

| Directory | Absolute Path |
|-----------|---------------|
| Skills    | /home/nic/src/academicOps/aops-core/skills  |
| Hooks     | /home/nic/src/academicOps/aops-core/hooks   |
| Commands  | /home/nic/src/academicOps/aops-core/commands |
| Tests     | /home/nic/src/academicOps/tests   |
| Config    | /home/nic/src/academicOps/config  |
| Workflows | /home/nic/src/academicOps/workflows |

## Data Directories

User data directories within $ACA_DATA:

| Directory | Absolute Path |
|-----------|---------------|
| Sessions  | /home/nic/writing/sessions |
| Projects  | /home/nic/writing/data/projects |
| Data Logs | /home/nic/writing/data/logs     |
| Context   | /home/nic/writing/data/context  |
| Goals     | /home/nic/writing/data/goals    |

## Hook Logs (Not in $ACA_DATA)

Hook logs are stored alongside session transcripts for correlation:

| Client  | Hook Log Path |
|---------|---------------|
| Claude  | ~/.claude/projects/<project>/<date>-<hash>-hooks.jsonl |
| Gemini  | ~/.gemini/tmp/<hash>/logs/<date>-<hash>-hooks.jsonl |

---

**Generation Command**: `python3 aops-core/scripts/generate_framework_paths.py`

Run this script after changing $AOPS or $ACA_DATA environment variables,
or after modifying the framework directory structure.
