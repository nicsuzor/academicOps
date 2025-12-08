# Framework Paths (DO NOT GUESS)

| Variable | Resolves To | Purpose |
|----------|-------------|---------|
| `$AOPS` | `/home/nic/src/aOps` | Framework source (SSoT for all framework files) |
| `$ACA_DATA` | `/home/nic/writing` | User data (tasks, sessions, knowledge base) |
| `~/.claude/` | symlinks → `$AOPS` | Runtime directory (DO NOT edit here) |

**To edit framework files**: Always edit in `$AOPS/`, never in `~/.claude/` symlinks.

| Component | Edit Location | Symlinked From |
|-----------|---------------|----------------|
| Commands | `$AOPS/commands/` | `~/.claude/commands/` |
| Skills | `$AOPS/skills/` | `~/.claude/skills/` |
| Hooks | `$AOPS/hooks/` | `~/.claude/hooks/` |
| Agents | `$AOPS/agents/` | `~/.claude/agents/` |

## bmem

**Always use `project="main"`** with all `mcp__bmem__*` tools.
