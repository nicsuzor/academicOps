# Session Hook Forensics Detailed Procedures

Detailed procedures, patterns, and examples for reconstructing session events from hooks logs.

## Step-by-Step Process

### 1. Locate the Files

Session files come in pairs:

- **Session file**: `<session-id>.jsonl` (Claude) or `<session-id>.json` (Gemini) - The actual conversation.
- **Hooks log**: `YYYYMMDD-HH-<short-id>-hooks.jsonl` - Every hook event.

Use `fd` or `ls` to find recent sessions in `~/.claude/projects` or `~/.gemini/tmp`.

### 2. Generate Transcript First

Raw JSONL/JSON is unreadable. Always generate a transcript:

```bash
cd $AOPS && uv run python scripts/transcript.py /path/to/session.jsonl
```

The transcript shows **what the agent did**. Use it to understand the session flow.

### 3. Analyze Hooks Log for Infrastructure Behavior

The hooks log shows **what the framework did**. Use `jq` to filter events:

- **Denied tool uses**: `jq 'select(.output.verdict == "deny")' <hooks.jsonl>`
- **Hook errors**: `jq 'select(.metadata.errors != null)' <hooks.jsonl>`
- **Last 5 events**: `tail -5 <hooks.jsonl> | jq '{event: .hook_event, tool: .input.tool_name, verdict: .output.verdict, errors: .metadata.errors}'`

### 4. Diagnose Common Patterns

- **Pattern A: Gate Never Opened**: Hydrator completed but subsequent tools blocked. Check for `gate_update` crashes in `PostToolUse` for the hydrator.
- **Pattern B: Recursive Subagent Loop**: Session times out with many `SubagentStop` events. Check `agent_id` for recursive spawning.
- **Pattern C: Tool Blocked with Missing Gates**: Tool denied with specific missing gates listed in `context_injection`.

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

The `system_message` field shows gate status (e.g., `[📌✗ 💧✗ 🤝✓]`).

- 📌: Task binding status
- 💧: Hydration gate status
- ✓: Gate open (passed)
- ✗: Gate closed (blocked)

## Example: Full Forensics Session

1. **Find the session**: `167b5f86-...-hooks.jsonl`.
2. **Generate transcript**: `uv run python scripts/transcript.py /path/to/167b5f86.jsonl`.
3. **Read last hook events**: Identify that `PostToolUse` for `Task` (hydrator) allowed the tool but `gate_update` crashed with an `AttributeError`.
4. **Root cause**: The gate never opened because the hook crashed before calling `_open_gate("hydration")`.
5. **Fix**: Update `gates.py` to use the correct attribute for `tool_output`.
