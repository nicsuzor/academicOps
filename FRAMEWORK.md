# ⚠️ STOP - READ BEFORE ANY FILE OPERATIONS ⚠️

**Before using Read, Glob, Grep, or Write tools**: Check this path table FIRST.
**If you get "Error reading file"**: You guessed wrong. Return here, use correct path.
**DO NOT fabricate paths** like `~/.config/aops/` - they don't exist.

| Variable | Purpose |
|----------|---------|
| `$AOPS` | Framework source (SSoT for all framework files) |
| `$ACA_DATA` | User data (tasks, sessions, knowledge base) |
| `~/.claude/` | Runtime directory (symlinks → `$AOPS`, DO NOT edit here) |

**To edit framework files**: Always edit in `$AOPS/`, never in `~/.claude/` symlinks.

| Component | Edit Location | Symlinked From |
|-----------|---------------|----------------|
| Commands | `$AOPS/commands/` | `~/.claude/commands/` |
| Skills | `$AOPS/skills/` | `~/.claude/skills/` |
| Hooks | `$AOPS/hooks/` | `~/.claude/hooks/` |
| Agents | `$AOPS/agents/` | `~/.claude/agents/` |

## bmem

**Always use `project="main"`** with all `mcp__bmem__*` tools.
