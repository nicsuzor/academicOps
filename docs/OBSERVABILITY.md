# Observability

## Data Sources

| Source | Location | Contents | How to View |
|--------|----------|----------|-------------|
| **Claude Sessions** | `~/.claude/projects/<project>/*.jsonl` | Full transcripts (messages, tools, results) | `/transcript`, external viewers |
| **aOps Hook Logs** | `~/.claude/projects/<project>/<date>-<hash>-hooks.jsonl` | Hook execution metadata | Direct file read |
| **Tasks** | `$ACA_DATA/tasks/` | Task markdown files | Dashboard, `task_view.py` |

## Session Transcripts

**Primary source for understanding what happened in a session.**

Claude Code writes complete transcripts including:
- All user/assistant messages
- All tool calls and results
- Agent spawns and their transcripts (`agent-*.jsonl`)

### Viewing Options

**aOps transcript skill** (generates markdown):
```bash
# Via /transcript command
# Output: $ACA_DATA/sessions/claude/YYYYMMDD-<project>-<slug>-{full,abridged}.md
```

**External viewers** (browser-based):
```bash
PORT=3400 npx @kimuson/claude-code-viewer@latest
uvx claude-code-log@latest --open-browser
```

**Recommendation**: Use `/transcript` for archival. Use external viewers for quick browsing.

## Hook Logs

**Complements Claude transcripts** - captures information Claude Code doesn't record.

**Location**: `~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl`

### What Each Event Captures

**Common fields** (all events): `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`

| Event | Additional Fields | Why It Matters |
|-------|-------------------|----------------|
| **SessionStart** | `source` (startup/resume/clear/compact) | Session initialization, distinguishes fresh vs resumed |
| **UserPromptSubmit** | `prompt` (full user input) | Exact prompt text before any transformation |
| **PreToolUse** | `tool_name`, `tool_input`, `tool_use_id` | What tool + params about to execute |
| **PostToolUse** | `tool_name`, `tool_input`, **`tool_response`**, `tool_use_id` | **Full tool output** (may be truncated in Claude transcripts) |
| **SubAgentStop** | `stop_hook_active` | Subagent completion, whether hook chain active |
| **Stop** | `stop_hook_active` | Session end, whether hook chain active |

### Finding Injected Context

When hooks inject `additionalContext`, it's logged in the hook output. Look for:
- `additionalContext` field in SessionStart entries (AXIOMS, FRAMEWORK, CORE content)
- `additionalContext` field in UserPromptSubmit entries (skill routing suggestions)
- `systemMessage` field in PreToolUse entries (policy enforcement blocks)

**Example query** (find all context injections):
```bash
jq 'select(.additionalContext != null) | {hook_event, additionalContext}' *-hooks.jsonl
```

### Implementation

Logged via `hooks/unified_logger.py` → `hooks/hook_logger.py`

All input fields from Claude Code are captured verbatim (`**input_data` spread into log entry).

## Architecture

```
┌─────────────────────────────────────┐
│        CLAUDE CODE SESSION          │
│  User ←→ Claude ←→ Tools            │
└──────────────┬──────────────────────┘
               │
               ▼
    ~/.claude/projects/<project>/
    ├── *.jsonl (Claude transcripts)
    └── *-hooks.jsonl (aOps hooks)
               │
               ▼
    /transcript    External viewers
```

