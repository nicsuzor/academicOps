---
name: analyze-sessions
description: Analyze Claude Code sessions and produce curated daily summary grouped by project
allowed-tools: Skill,Read,Bash,Write,Edit,mcp__bmem__write_note,mcp__bmem__edit_note,mcp__bmem__search_notes
permalink: commands/analyze-sessions
---

# /analyze-sessions

Analyze Claude Code sessions and produce a curated daily summary.

## Arguments

- `$ARGUMENTS` - Optional: date (YYYYMMDD) or "today" (default)

## Invocation

```
Skill(skill="session-analyzer")
```

Pass `$ARGUMENTS` to the skill for date filtering.
