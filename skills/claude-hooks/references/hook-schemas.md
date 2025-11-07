# Claude Code Hook Input/Output Schemas

Complete technical reference for all hook event types, their input data structures, and expected output formats.

## Common Input Fields

All hooks receive these fields via stdin as JSON:

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "EventName"
}
```

## SessionStart Hook

**When it fires:** Session begins or resumes from saved state

**Input schema:**

```json
{
  "session_id": "2e1c62ed-9d20-4e7b-bfee-cccfa810f537",
  "transcript_path": "/home/user/.claude/projects/-home-user-project/session.jsonl",
  "cwd": "/home/user/project",
  "hook_event_name": "SessionStart",
  "source": "startup" // or "resume"
}
```

**Output schema:**

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Markdown text loaded into agent context"
  }
}
```

**Exit codes:**

- `0`: Success, output added to context
- `1`: Error (non-blocking), stderr shown to user
- `2`: Error (blocking), stderr fed to Claude

**Environment variables available:**

- `$CLAUDE_PROJECT_DIR` - Absolute path to project root
- `$CLAUDE_CODE_REMOTE` - Remote identifier if applicable
- `$CLAUDE_ENV_FILE` - Path to environment file

## PreToolUse Hook

**When it fires:** After Claude creates tool parameters, before tool execution

**Input schema:**

```json
{
  "session_id": "30a742a4-5b39-4d74-bb32-a1056fae20be",
  "transcript_path": "/home/user/.claude/projects/session.jsonl",
  "cwd": "/home/user/project",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  }
}
```

**Output schema:**

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow", // "allow", "deny", or "ask"
    "permissionDecisionReason": "Optional explanation"
  }
}
```

**Exit codes:**

- `0`: Allow (with optional decision)
- `1`: Warn (allow with warning message)
- `2`: Block (deny execution)

**Permission decisions:**

- `"allow"` - Tool executes normally
- `"deny"` - Tool blocked, reason shown to Claude
- `"ask"` - User prompted for approval

## PostToolUse Hook

**When it fires:** Immediately after tool completes execution

**Input schema:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "..."
  },
  "tool_response": {
    "success": true,
    "output": "File written successfully"
  }
}
```

**Output schema:**

```json
{
  "decision": "block", // Optional, omit to continue
  "additionalContext": "Post-processing information for Claude",
  "systemMessage": "Warning or info message"
}
```

**Exit codes:**

- `0`: Success, continue
- `1`: Non-blocking error
- `2`: Blocking error

## Stop Hook

**When it fires:** Main agent finishes responding to user

**Input schema:**

```json
{
  "session_id": "30a742a4-5b39-4d74-bb32-a1056fae20be",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/home/user/project",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**Output schema:**

```json
{
  "decision": "block", // Optional, omit to continue
  "reason": "Required if blocking - shown to Claude"
}
```

**Exit codes:**

- `0`: Allow stop
- `1`: Non-blocking warning
- `2`: Block stop (with reason)

**Note:** `stop_hook_active` is `true` if another stop hook is currently running (prevent recursion)

## SubagentStop Hook

**When it fires:** Subagent (Task tool invocation) finishes

**Input schema:** Same as Stop hook, but `hook_event_name` is `"SubagentStop"`

**Output schema:** Same as Stop hook

**Usage:** Validate subagent completion, enforce requirements before returning to parent agent

## UserPromptSubmit Hook

**When it fires:** User submits prompt, before Claude processes

**Input schema:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "User's input text"
}
```

**Output schema:**

```json
{
  "decision": "block", // Optional, omit to continue
  "additionalContext": "Context injected before prompt processing",
  "systemMessage": "Warning shown to user"
}
```

**Exit codes:**

- `0`: Continue processing
- `1`: Non-blocking warning
- `2`: Block prompt

## SessionEnd Hook

**When it fires:** Session terminates

**Input schema:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "SessionEnd",
  "reason": "user_exit" // or other termination reasons
}
```

**Output schema:** None (output ignored)

**Exit codes:** Ignored (session ends regardless)

**Usage:** Cleanup operations, logging, saving state

## PreCompact Hook

**When it fires:** Before context compaction (manual or automatic)

**Input schema:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "PreCompact",
  "compaction_reason": "manual" // or "automatic"
}
```

**Output schema:**

```json
{
  "decision": "block", // Optional, prevent compaction
  "systemMessage": "Warning about compaction"
}
```

## Notification Hook

**When it fires:** Claude sends permission request or idle notification

**Input schema:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "Notification",
  "notification_type": "permission_request", // or "idle"
  "details": {/* notification-specific data */}
}
```

**Output schema:**

```json
{
  "decision": "block", // Optional
  "systemMessage": "Response to notification"
}
```

## Common Patterns

### Allowing with context

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "additionalContext": "Extra information for Claude"
  }
}
```

### Blocking with explanation

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Inline Python is blocked. Use 'uv run python' instead."
  }
}
```

### Warning without blocking

Exit code `1` with stderr message - shown to user but execution continues

### Silent success

Exit code `0` with no stdout - hook passes without output

## Environment Variables

Available in all hooks:

- `$CLAUDE_PROJECT_DIR` - Absolute path to project root (where Claude Code started)
- `$HOME` - User home directory
- `$PATH` - System PATH
- Custom env vars from `settings.json` `env` block

SessionStart only:

- `$CLAUDE_CODE_REMOTE` - Remote identifier
- `$CLAUDE_ENV_FILE` - Path to environment file

## Debugging Hooks

**Enable debug mode:**

```bash
claude --debug
```

**Check hook execution logs:**

- Hooks write to stderr for debugging
- Exit codes and stdout visible in debug output
- Check for JSON parsing errors in hook output

**Common issues:**

- Relative paths failing → Use `$CLAUDE_PROJECT_DIR`
- Timeout (60s default) → Increase in hook config
- Silent failure → Check exit codes and stderr
- JSON parse errors → Validate output format
