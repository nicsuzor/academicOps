---
name: transcript
description: Generate markdown transcript of a Claude Code session
permalink: commands/transcript
---

Generate a readable markdown transcript from a Claude Code session JSONL file.

# Transcript Generator

Converts Claude Code session logs to markdown transcripts with chronologically woven hook context.

**What it does**:

1. Finds session JSONL file (defaults to current session)
2. Loads hook context from `-hooks.jsonl` files
3. Generates markdown with conversation turns and hook execution timeline
4. Shows ALL hooks (even without additionalContext) with exit codes
5. Outputs to `$ACA_DATA/sessions/claude/YYYYMMDD-<session-slug>.md`
6. Opens the generated transcript file with `xdg-open` for immediate viewing

**Usage**:

- `/transcript` - Generate transcript for current session
- `/transcript session-id` - Generate for specific session ID
- `/transcript yesterday` - Search for yesterday's sessions
- `/transcript automod` - Search sessions in automod project

**Examples**:

```
/transcript
/transcript d44ee140
/transcript yesterday
/transcript automod
```

**Output file**:

- Location: `$ACA_DATA/sessions/claude/`
- Filename format: `YYYYMMDD-<session-slug>.md` (e.g., `20251130-fix-auth-bug.md`)
- Session slug: Derive from main topic/task (lowercase, hyphens, max 50 chars)

**Required frontmatter** (obsidian/bmem compatible):

```yaml
---
title: "Session: <descriptive title>"
type: session
tags:
  - session
  - claude-code
  - <project-tag>
date: YYYY-MM-DD
session_id: <full-session-id>
project: <project-name>
files_modified:
  - path/to/file1.py
  - path/to/file2.md
---
```

Frontmatter requirements:
- `title`: Descriptive, starts with "Session: "
- `type`: Always "session"
- `tags`: Minimum: session, claude-code. Add project-specific tags.
- `date`: Session date in YYYY-MM-DD format
- `session_id`: Full Claude session ID from JSONL
- `project`: Repository/project name
- `files_modified`: List of files edited during session

**Body format**:

```markdown
# Session: <descriptive title>

## Summary

<1-3 sentence summary of what was accomplished>

## Context

- **Project**: <project-name>
- **Session ID**: `<session-id>`
- **Duration**: <approximate duration>
- **Files Modified**: <count>

## Transcript

### User (HH:MM)
<user message>

### Assistant (HH:MM)
<assistant response>

### Tool: <ToolName> ✓
<tool result summary>

### Hook: <EventName> ✓
<hook context if present>

## Files Modified

- `path/to/file1.py` - <brief change description>
- `path/to/file2.md` - <brief change description>
```

**Implementation notes**:

- Session files: `~/.claude/projects/*/[uuid].jsonl`
- Hook logs: `~/.cache/aops/sessions/*-hooks.jsonl`
- Ensure `$ACA_DATA/sessions/claude/` directory exists before writing
- Use `xdg-open` to open result after generation

**Finding session files**:

```bash
# Find most recent session in current project
ls -lt ~/.claude/projects/$(basename $(pwd) | sed 's/^/-/')/*.jsonl | grep -v agent | head -1

# List all recent sessions
ls -lt ~/.claude/projects/*/[0-9a-f]*.jsonl | grep -v agent | head -10
```
