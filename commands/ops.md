---
description: academicOps framework help and commands
permalink: aops/commands/ops
---

@reference $ACADEMICOPS/docs/QUICK_REFERENCE.md

---

## Diagnostics

Report the following diagnostic information:

### Available Resources

**Skills**: List all available skills from the Skill tool

**Commands**: List all available slash commands from the SlashCommand tool

**Subagents**: List available subagent types from the Task tool

### Folder Configuration

**Working Directory**: `$PWD`

**Project Folder**: Current directory (`$PWD`)

**Framework Folder (ACADEMICOPS)**: `$ACADEMICOPS` (report "Not configured" if empty)

**Personal Folder (ACADEMICOPS_PERSONAL)**: `$ACADEMICOPS_PERSONAL` (report "Not configured" if empty)

**Agent Symlink**: Report target if `.claude/agents` exists and is a symlink