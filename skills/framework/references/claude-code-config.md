---
title: Claude Code Configuration Reference
type: reference
category: ref
permalink: ref-claude-code-config
description: Technical reference for Claude Code configuration file locations, behavior, and best practices
---

# Claude Code Configuration Reference

Technical reference for Claude Code configuration file locations and behavior.

**Official Documentation**: [Claude Code Documentation](https://code.claude.com/docs/en/claude_code_docs_map.md)

## Configuration File Locations

### User-Scoped Configuration

| File | Purpose | Managed By |
|------|---------|------------|
| `~/.claude.json` | App state + user MCP servers | Claude Code (auto-managed) |
| `~/.claude/settings.json` | Permissions, hooks, status line | User (symlinked to aOps) |
| `~/.claude/skills/` | User skills | User (symlinked to aOps) |
| `~/.claude/commands/` | User slash commands | User (symlinked to aOps) |
| `~/.claude/agents/` | User custom agents | User (symlinked to aOps) |

### Project-Scoped Configuration

| File | Purpose | Managed By |
|------|---------|------------|
| `.mcp.json` | Project MCP servers (team-shared) | Version control |
| `.claude/settings.json` | Project permissions | Version control |
| `.claude/settings.local.json` | Local project overrides | User (gitignored) |
| `CLAUDE.md` | Project context | Version control |

## MCP Server Configuration

**Critical**: User-scoped MCP servers are stored in `~/.claude.json` under `mcpServers` key, NOT in `~/.mcp.json`.

### Configuration Precedence (Highest to Lowest)

1. `~/.claude.json` project overrides: `projects["/path"].mcpServers`
2. `~/.claude.json` global: `mcpServers`
3. `.mcp.json` in project directory (project-scoped)

### Our Approach

- **Authoritative source**: `$AOPS/config/claude/mcp.json`
- **Deployed to**: `~/.claude.json` mcpServers (merged via `setup.sh`)
- **Sync command**: `$AOPS/setup.sh` (run after config changes)

### Common Issues

**"No MCP servers configured" despite config existing**:
- Check `~/.claude.json` has `mcpServers` key (not `~/.mcp.json`)
- Run `$AOPS/setup.sh` to sync from authoritative source
- Verify with `claude mcp list`

**Symlinks not working for MCP config**:
- Claude Code doesn't read `~/.mcp.json` for user servers
- Must merge into `~/.claude.json` directly

## Settings vs MCP Files

| Scope | Settings | MCP Servers |
|-------|----------|-------------|
| User | `~/.claude/settings.json` | `~/.claude.json` mcpServers |
| Project (shared) | `.claude/settings.json` | `.mcp.json` |
| Project (local) | `.claude/settings.local.json` | N/A |

## Permissions Configuration

### Syntax Rules

**Tool Permissions** (Read, Write, Edit, etc.):
- Glob patterns: `Write(**/.claude/**)`, `Edit(/data/tasks/**)`
- Path patterns work in tool names

**Bash Command Permissions**:
- ✅ Prefix matching: `Bash(npm run:*)` - allows any command starting with "npm run"
- ✅ Exact match: `Bash(npm install express)` - allows only that exact command
- ✅ Global: `Bash` - allows all bash commands
- ❌ Wildcards in middle: `Bash(cp * **/.claude/**)` - NOT SUPPORTED
- ❌ Wildcards in middle: `Bash(echo * > **/.claude/**)` - NOT SUPPORTED

**Common Patterns**:
```json
{
  "permissions": {
    "allow": [
      "Read",
      "Bash(uv run python:*)",
      "Bash(git add:*)"
    ],
    "deny": [
      "Write(/data/tasks/**)",
      "Edit(**/.claude/**)",
      "Bash(rm:*/.claude/*)",
      "Bash(mv:*/.claude/*)",
      "Bash(cp:*/.claude/*)"
    ]
  }
}
```

### Hooks Configuration

**For complete hooks documentation**, see [[hooks_guide]].

**Related references**: [[testing-with-live-data]], [[script-design-guide]]


### Status Line Configuration

**Custom Status Line**:
```json
{
  "statusLine": {
    "type": "command",
    "command": "host=$(hostname -s); repo=$(basename \"$(git rev-parse --show-toplevel 2>/dev/null)\"); branch=$(git symbolic-ref --short HEAD 2>/dev/null); printf '%s | %s | %s' \"$host\" \"$repo\" \"$branch\""
  }
}
```

**Output**: Displays in Claude Code interface (e.g., `myhost | writing | main`)

### Always Thinking Mode

```json
{
  "alwaysThinkingEnabled": false
}
```

Set to `true` to enable extended thinking mode by default.

## Verified Behavior (Claude Code v2.0.50)

- `claude mcp add --scope user` → writes to `~/.claude.json` mcpServers
- `claude mcp add --scope project` → writes to `.mcp.json`
- `claude mcp list` → reads from `~/.claude.json` + `.mcp.json`
- Settings symlinks work (`~/.claude/settings.json` → aOps)
- MCP config symlinks do NOT work (`~/.mcp.json` ignored for user scope)
- Bash permission wildcards only work with prefix matching (`:*` syntax)
- Hooks can use environment variables in commands (`$AOPS`, etc.)
- Hook timeouts in milliseconds (default: 2000ms recommended)

## Runtime Behavior

### Subagent Isolation

**Observed 2025-12-25**: Subagents invoked via the Task tool have isolated state.

| State | Shared with Parent? |
|-------|---------------------|
| TodoWrite (todo list) | ❌ No - subagent todos don't persist to parent session |
| File operations | ✅ Yes - verified bidirectional (parent↔subagent reads/writes) |
| Memory server | ✅ Yes - mcp__memory__* calls persist globally |

**Practical implication**: If you need todos visible in the main session, the main agent must create them directly. Cannot delegate todo creation to subagents.
