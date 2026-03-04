---
title: Session Hook Forensics
type: automation
category: instruction
permalink: workflow-session-hook-forensics
description: Reconstruct session events from hooks logs to diagnose gate failures, state transitions, and hook crashes
---

# Workflow 9: Session Hook Forensics

**When**: Session behaved unexpectedly, gate blocked tools, hooks crashed, or exact sequence of events is needed.

**Key principle**: Hooks logs record **every hook event** with full context. Session transcripts show the conversation; hooks logs show the infrastructure behavior.

**Detailed procedures and examples**: See **[[forensics-details]]**.

## Quick Start

```bash
# 1. Find recent sessions with hooks logs
fd -l --newer 10m jsonl ~/.claude/projects

# 2. Generate transcript from session file
cd $AOPS && uv run python scripts/transcript.py <session.jsonl>

# 3. Read the hooks log (last N entries)
tail -20 <session-hooks.jsonl> | jq -c '.'
```

## Steps

1. **Locate the Files**: Identify the session file and its corresponding hooks log.
2. **Generate Transcript First**: Always use `transcript.py` on the session file for a readable log.
3. **Analyze Hooks Log**: Filter for denied tool uses, hook errors, and event sequences using `jq`.
4. **Reconstruct Event Sequence**: Focus on the last 3-5 events to identify failures at session end.
5. **Diagnose Patterns**: Identify common issues like crashed gates, recursive loops, or missing gate requirements.
6. **Create Bug Report**: Document the session ID, event sequence, root cause, and fix location.

## Common Indicators

- **`PostToolUse` crashes**: Gate updates failing after a tool completes.
- **`verdict == "deny"`**: Explicitly blocked tool uses.
- **Gate status markers**: `[📌✗ 💧✗ 🤝✓]` indicating specific gate states.

**ALWAYS generate transcript first** - raw JSONL/JSON is difficult to interpret.
