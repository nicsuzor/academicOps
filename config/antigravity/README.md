---
name: antigravity-parity
title: Antigravity Parity
type: reference
description: Antigravity IDE support status and setup.
tags: [antigravity, ide, compatibility]
---

# Antigravity Parity

Antigravity IDE support for academicOps framework.

## Setup

```bash
./setup.sh  # Handles Antigravity automatically
```

## What Works

| Feature          | Status  | Notes                                    |
| ---------------- | ------- | ---------------------------------------- |
| MCP servers      | Works   | Auto-converted from Claude mcp.json      |
| Skills           | Works   | Linked as global workflows               |
| Rules            | Works   | axioms.md, heuristics.md, core.md linked |
| Task tracking    | Works   | bd CLI available                         |

## Known Gaps

| Feature               | Reason                  | Workaround               |
| --------------------- | ----------------------- | ------------------------ |
| Hooks                 | Not supported           | Manual hydration         |
| Task() subagents      | Not supported           | Single-agent execution   |
| Automatic hydration   | No UserPromptSubmit     | Read hydrator manually   |

## Directory Structure

```
~/.gemini/antigravity/
  mcp_config.json           # Generated from Claude MCP config
  global_workflows/         # Symlinks to skill SKILL.md files

<repo>/.agent/
  rules/                    # Project-level rules
    axioms.md              # Symlink -> AXIOMS.md
    heuristics.md          # Symlink -> HEURISTICS.md
    core.md                # Symlink -> config/antigravity/rules/core.md

$AOPS/config/antigravity/
  README.md                 # This file
  rules/
    core.md                # Hydrator + bd workflow instructions
```

## Manual Hydration

Since Antigravity lacks hooks, manually invoke hydration:

```
Read $AOPS/aops-core/agents/prompt-hydrator.md
```

Then follow the hydrator workflow for complex tasks.
