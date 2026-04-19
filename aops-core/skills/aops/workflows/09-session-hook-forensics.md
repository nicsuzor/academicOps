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

**Detailed procedures, schemas, and diagnostic commands**: See **[[forensics-details]]**.

## Quick Start

```bash
# 1. Find the hooks log for a session
ls $AOPS_SESSIONS/hooks/*<session-short-hash>*

# 2. Quick summary: how many ops, any denies?
grep -c '"hook_event":"PostToolUse"' <hooks.jsonl>
grep '"verdict":"deny"' <hooks.jsonl> | wc -l

# 3. Generate transcript (for the conversation side)
cd $AOPS && uv run python scripts/transcript.py <session.jsonl>

# 4. Check gate verdicts (raw JSONL — transcripts don't show these yet)
grep '"hook_event":"Stop"' <hooks.jsonl> | python3 -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l); o = d.get('output', {})
    print(f'{d.get(\"logged_at\",\"?\")[:19]} verdict={o.get(\"verdict\")} msg={str(o.get(\"system_message\",\"\"))[:80]}')
"
```

## Steps

1. **Locate the Files**
   - Hook JSONL: `$AOPS_SESSIONS/hooks/<YYYYMMDD>-<session-short-hash>-hooks.jsonl`
   - Session state: `$AOPS_SESSION_STATE_DIR/<YYYYMMDD>-<HH>-<session-short-hash>.json`
   - Transcript: `$POLECAT_HOME/sessions/transcripts/*<session-short-hash>*-full.md`
   - See [[forensics-details]] for full path conventions and cross-reference guide.

2. **Generate Transcript First**
   Always use `transcript.py` on the CC session JSONL for a readable conversation log. Transcripts include hook verdicts and system_messages (merged by `transcript_parser.py:_map_hook_jsonl_to_entry_data`). For exact raw values or when transcript rendering is truncated, use raw hook JSONL directly.

3. **Check Gate Behavior**
   - **Enforcer/RBG gate**: Grep for `SubagentStart`/`SubagentStop` with `enforcer` or `rbg` subagent type. Each pair = one compliance check. See [[forensics-details]] for commands.
   - **Stop/Handover gate**: Grep for `"hook_event":"Stop"` and check `output.verdict`. Look for the 4-deny-then-auto-approve pattern.
   - **PreToolUse blocks**: Grep for `"verdict":"deny"` to find any tool calls that were rejected.

4. **Reconstruct Event Sequence**
   Focus on the last 10-20 events to identify failures at session end. Key question: did the session complete its work, commit, invoke `/dump`, or get blocked?

5. **Identify the Pattern**
   Common patterns (see [[forensics-details]] for details):
   - Enforcer dispatching repeatedly in long sessions (normal)
   - 4 Stop denies then auto-approve (agent ignoring or unable to comply)
   - Zero Gemini hook JSONL (open question as of 2026-04-09)
   - Operations count ≠ turn count (50 ops ≈ 11 turns)

6. **File Bug Report or Learning**
   Document: session ID, event sequence, root cause, fix location. Use `/learn` for systemic issues.

## Known Issues

- **Missing client_type**: Hook JSONL shows `model=unknown` for all polecat sessions. Distinguish Claude vs Gemini by session ID format only (`gemini-*` prefix for Gemini).

## Common Indicators

- **`PostToolUse` crashes**: Gate updates failing after a tool completes.
- **`verdict == "deny"`**: Explicitly blocked tool uses or session stops.
- **Gate status markers**: `◇` (enforcer countdown), `💧` (hydration), `≡` (gate status).
- **`SubagentStart`/`SubagentStop` with enforcer/rbg**: Compliance gate check cycle.
- **4 consecutive Stop denies**: Safety override pattern — investigate what happened between denies.

**ALWAYS generate transcript first** — raw JSONL is difficult to interpret for the conversation side. But for hook/gate behavior, read the hook JSONL directly.
