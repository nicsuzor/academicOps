# Claude Code Configuration Reference

Technical reference for Claude Code configuration file locations and behavior.

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

## Verified Behavior (Claude Code v2.0.50)

- `claude mcp add --scope user` → writes to `~/.claude.json` mcpServers
- `claude mcp add --scope project` → writes to `.mcp.json`
- `claude mcp list` → reads from `~/.claude.json` + `.mcp.json`
- Settings symlinks work (`~/.claude/settings.json` → aOps)
- MCP config symlinks do NOT work (`~/.mcp.json` ignored for user scope)
