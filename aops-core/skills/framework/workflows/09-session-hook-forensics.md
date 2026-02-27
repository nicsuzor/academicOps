---
title: Session Hook Forensics
type: automation
category: instruction
permalink: workflow-session-hook-forensics
description: Reconstruct session events from hooks logs to diagnose gate failures, state transitions, and hook crashes
---

# Workflow 9: Session Hook Forensics

**When**: Session behaved unexpectedly, gate blocked tools that should have been allowed, hooks crashed, or you need to understand the exact sequence of events.

**Key principle**: Hooks logs record **every hook event** with full context. Session transcripts show the conversation; hooks logs show the infrastructure behavior.

## Quick Start

```bash
# 1. Find recent sessions with hooks logs
fd -l --newer 10m jsonl ~/.claude/projects

# 2. Generate transcript from session file
cd $AOPS && uv run python scripts/transcript.py <session.jsonl>

# 3. Read the hooks log (last N entries)
tail -20 <session-hooks.jsonl> | jq -c '.'
```

## Step-by-Step Process

### 1. Locate the Files

Session files come in pairs:

- **Session file**: `<session-id>.jsonl` - The actual conversation
- **Hooks log**: `YYYYMMDD-HH-<short-id>-hooks.jsonl` - Every hook event

```bash
# Find sessions modified in last N minutes
fd -l --newer 5m jsonl ~/.claude/projects

# Find hooks log for a specific session ID
fd <session-id-prefix> ~/.claude/projects
```

### 2. Generate Transcript First

Raw JSONL is unreadable. Always generate a transcript:

```bash
cd $AOPS && uv run python scripts/transcript.py /path/to/session.jsonl
# Output:
# ✅ Full transcript: .../session-full.md
# ✅ Abridged transcript: .../session-abridged.md
```

The transcript shows **what the agent did**. Use it to understand the session flow.

### 3. Analyze Hooks Log for Infrastructure Behavior

The hooks log shows **what the framework did**. Key fields:

| Field                      | Purpose                                                               |
| -------------------------- | --------------------------------------------------------------------- |
| `hook_event`               | Event type: SessionStart, PreToolUse, PostToolUse, SubagentStop, Stop |
| `tool_name`                | Which tool triggered the hook                                         |
| `output.verdict`           | `allow` or `deny`                                                     |
| `output.context_injection` | Message injected into context                                         |
| `metadata.errors`          | Any hook crashes                                                      |
| `metadata.tracebacks`      | Full stack traces                                                     |

```bash
# Read last N hook events
tail -N <hooks.jsonl> | jq -c '.'

# Count events by type
jq -r '.hook_event' <hooks.jsonl> | sort | uniq -c

# Find all denied tool uses
jq 'select(.output.verdict == "deny")' <hooks.jsonl>

# Find hook errors
jq 'select(.metadata.errors != null)' <hooks.jsonl>
```

### 4. Reconstruct the Event Sequence

Focus on the **last 3-5 events** to understand what happened at session end:

```bash
# Get last 5 hook events with key fields
tail -5 <hooks.jsonl> | jq '{
  event: .hook_event,
  tool: .input.tool_name,
  verdict: .output.verdict,
  errors: .metadata.errors
}'
```

### 5. Diagnose Common Patterns

#### Pattern A: Gate Never Opened Despite Successful Hydration

**Symptom**: Hydrator completed with "HYDRATION RESULT" but subsequent tools blocked.

**Diagnosis**:

```bash
# Find PostToolUse for hydrator
jq 'select(.hook_event == "PostToolUse" and .input.tool_name == "Task")' <hooks.jsonl>

# Check for gate_update errors
jq 'select(.metadata.errors[]? | contains("gate_update"))' <hooks.jsonl>
```

**Root cause**: The `gate_update` hook crashed before calling `_open_gate()`.

**Example** (from real session):

```
errors: ["Gate 'gate_update' failed: 'HookContext' object has no attribute 'tool_output'"]
```

Fix: Check `gates.py` for attribute access on HookContext.

#### Pattern B: Recursive Subagent Loop

**Symptom**: Session times out with many SubagentStop events.

**Diagnosis**:

```bash
# Count subagent events
jq 'select(.hook_event == "SubagentStop")' <hooks.jsonl> | wc -l

# Check subagent IDs
jq 'select(.hook_event == "SubagentStop") | .input.agent_id' <hooks.jsonl>
```

**Root cause**: Subagent hitting gates → spawning another subagent → loop.

#### Pattern C: Tool Blocked with Missing Gates

**Symptom**: Tool denied with specific missing gates listed.

**Diagnosis**:

```bash
# Find denied tools with gate status
jq 'select(.output.verdict == "deny") | {
  tool: .input.tool_name,
  injection: .output.context_injection
}' <hooks.jsonl>
```

**Example output**:

```
Tool: Read (read_only)
Missing: hydration
```

**Root cause**: Gate never opened (see Pattern A) or gate re-closed unexpectedly.

### 6. Create a Bug Report

Once you identify the issue, document:

1. **Session ID**: Link to the specific session
2. **Event sequence**: The last N hook events that show the failure
3. **Root cause**: Which hook failed and why
4. **Fix location**: File:line where the bug lives

## Reference: Hook Event Types

| Event              | When Fired           | What to Look For                      |
| ------------------ | -------------------- | ------------------------------------- |
| `SessionStart`     | Session begins       | Gate initialization, env setup        |
| `UserPromptSubmit` | User sends message   | Gate resets, hydration triggers       |
| `PreToolUse`       | Before tool runs     | Gate checks, tool blocking            |
| `PostToolUse`      | After tool completes | Gate state updates, errors            |
| `SubagentStop`     | Subagent finishes    | Subagent success/failure              |
| `Stop`             | Session ending       | QA/handover gate checks (via `/dump`) |

## Reference: Gate Status Indicators

The `system_message` field shows gate status:

```
[📌✗ 💧✗ 🤝✓]
```

| Symbol | Gate      | Meaning               |
| ------ | --------- | --------------------- |
| 📌     | task      | Task binding status   |
| 💧     | hydration | Hydration gate status |
| ✓      | -         | Gate open (passed)    |
| ✗      | -         | Gate closed (blocked) |

## Example: Full Forensics Session

**Problem**: Session stuck after hydration - all read tools blocked.

**Investigation**:

```bash
# 1. Find the session
fd -l --newer 3m jsonl ~/.claude/projects/-home-nic-src-academicOps
# Found: 167b5f86-...-hooks.jsonl

# 2. Generate transcript
uv run python scripts/transcript.py /path/to/167b5f86.jsonl

# 3. Read last 15 hook events
tail -15 /path/to/hooks.jsonl | jq '{
  n: input_line_number,
  event: .hook_event,
  tool: .input.tool_name,
  verdict: .output.verdict,
  errors: .metadata.errors
}'
```

**Findings**:

| #  | Event       | Tool            | Verdict  | Issue                 |
| -- | ----------- | --------------- | -------- | --------------------- |
| 8  | PostToolUse | Task (hydrator) | allow    | `gate_update` crashed |
| 9  | PreToolUse  | Glob            | **deny** | hydration ✗           |
| 10 | PreToolUse  | Read            | **deny** | hydration ✗           |
| 11 | PreToolUse  | Read            | **deny** | hydration ✗           |

**Root cause**: Line 8 shows the hydrator completed but `gate_update` failed:

```
AttributeError: 'HookContext' object has no attribute 'tool_output'
```

The gate never opened because the hook crashed before calling `_open_gate("hydration")`.

**Fix**: In `gates.py:119`, change `ctx.tool_output` to `ctx.raw_input.get("tool_response")`.
