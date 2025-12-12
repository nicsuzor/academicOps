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

**NOT for understanding sessions** - use Claude transcripts for that.

Hook logs capture execution metadata only:
- SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, SubAgentStop, Stop events
- Logged via `hooks/unified_logger.py` → `hooks/hook_logger.py`

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

## See Also

- **`docs/JIT-INJECTION.md`** - Hook details and test coverage
- **`docs/HOOKS.md`** - Hook architecture overview
