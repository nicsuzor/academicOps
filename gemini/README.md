---
name: gemini-parity
title: Gemini CLI Parity
type: reference
description: Gemini CLI support status, gaps, and workarounds.
permalink: gemini-parity
tags: [gemini, cli, compatibility]
---

# Gemini CLI Parity

Gemini CLI support for academicOps framework. Uses symlinks where possible.

## Setup

```bash
./setup-gemini.sh
```

## What Works

| Feature | Status | Notes |
|---------|--------|-------|
| Hooks | Works | Event names mapped via router |
| Commands | Works | Converted to TOML at setup |
| MCP servers | Partial | memory + context7 configured |
| Skills | Manual | Use `Read skills/X/SKILL.md` |
| GEMINI.md | Works | Symlinked from project root |

## Known Gaps

### Critical (Won't Work)

| Feature | Reason | Workaround |
|---------|--------|------------|
| `Task()` subagents | Not implemented ([#3132](https://github.com/google-gemini/gemini-cli/issues/3132)) | Manual multi-turn |
| `Skill()` tool | Claude-specific | Read SKILL.md directly |
| SubagentStop event | No equivalent | N/A |
| Per-agent permissions | Not supported | Global permissions only |
| Persistent permissions | Session-only | Re-approve each session |

### Commands with Degraded Functionality

These commands work but lose subagent delegation:

- `/do` - Runs single-agent (no parallel subagents)
- `/meta` - No critic review
- `/parallel-batch` - Sequential only
- `/qa` - No subagent verification

## Event Mapping

| Claude Code | Gemini CLI |
|-------------|------------|
| SessionStart | SessionStart |
| PreToolUse | BeforeTool |
| PostToolUse | AfterTool |
| UserPromptSubmit | BeforeAgent |
| Stop | AfterAgent |
| SubagentStop | (none) |

## Directory Structure

```
~/.gemini/
  GEMINI.md         # Symlink → $AOPS/GEMINI.md
  settings.json     # Merged with hooks + MCP
  commands/         # Symlink → $AOPS/gemini/commands/
  hooks/            # Symlink → $AOPS/gemini/hooks/

$AOPS/gemini/
  README.md         # This file
  hooks/router.py   # Event translation wrapper
  commands/         # Generated TOML files
  config/           # Settings template
```

## Using Skills in Gemini

Instead of `Skill(skill="framework")`, read the skill file directly:

```
Read /home/nic/src/academicOps/skills/framework/SKILL.md
```

The GEMINI.md file includes a skill activation table for common tasks.

## Troubleshooting

### Hooks not firing

1. Check `~/.gemini/settings.json` has `hooks` section
2. Verify symlink: `ls -la ~/.gemini/hooks/`
3. Check router permissions: `chmod +x $AOPS/gemini/hooks/router.py`

### MCP servers not connecting

1. Verify settings: `cat ~/.gemini/settings.json | jq .mcpServers`
2. Check network: memory server requires Tailscale

### Commands not appearing

1. Re-run setup: `./setup-gemini.sh`
2. Check symlink: `ls -la ~/.gemini/commands/`
