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
5. Outputs to `~/writing/session-{short-id}-transcript.md`
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

**Output format**:

- Session metadata (ID, created, files modified)
- Chronologically ordered conversation turns
- Hook executions woven inline: `### Hook: EventName ✓`
- Tool uses with results
- Timestamps and durations

**Implementation**:

- Tool location: `~/src/claude-transcript/claude_transcript.py`
- Session files: `~/.claude/projects/*/[uuid].jsonl`
- Hook logs: `~/.cache/aops/sessions/*-hooks.jsonl`
- Invocation: `uv run python ~/src/claude-transcript/claude_transcript.py [session-file] -o ~/writing/session-{id}-transcript.md`
- Opens result with `xdg-open` after generation

**Finding session files**:

```bash
# Find most recent session in current project
ls -lt ~/.claude/projects/$(basename $(pwd) | sed 's/^/-/')/*.jsonl | grep -v agent | head -1

# List all recent sessions
ls -lt ~/.claude/projects/*/[0-9a-f]*.jsonl | grep -v agent | head -10
```
