# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), or Antigravity
- Docker, only if you want polecat's containerised workers

## From the release channel

```bash
# 1. Register the services MCP server at user level:
claude mcp add --transport http --scope user services <your PKB MCP endpoint>

# 2. Install plugins from the marketplace:
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install pkb@academicOps
claude plugin install aops@academicOps
```

The `services` MCP server is installed at user level across all surfaces, never shipped inside a plugin:

- **Local Claude Code**: `claude mcp add --transport http --scope user services <PKB_MCP_URL>`. Must use `--scope user`; `--scope local` was observed to register nothing. Note: on local machines, `~/dotfiles/scripts/sync-mcp-servers.sh` is the appropriate home to synchronize user-scoped MCP registrations.
- **Claude Code Cloud / Cowork**: The claude.ai account connector named `services`.
- **Antigravity (agy)**: Configured in user-level MCP settings (`~/.gemini/antigravity-cli/settings.json` or `~/.gemini/antigravity-cli/mcp/services.json`).

Plugins install with no `--config`: `orchestrate`, `rbg`, `tools`, `ts`, and `aops-debug` install the same way as `pkb` and `aops`.

Nothing else has a default. Set the environment variables each plugin needs
before first use -- the full list is in [`README.md`](README.md#configure),
and each plugin's own `plugins/<dir>/README.md` documents its complete
surface.

## From source

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync
make install-dev
```

`make install-dev` builds `dist/`, registers it as a local marketplace named
`aops`, installs every plugin from it into Claude Code (and Antigravity when
`agy` is on `PATH`), and activates pre-commit.

`make uninstall-dev` reverses it and restores the release channel.

## Polecat

Polecat is the containerised worker runner, shipped inside the `ida` plugin. It
needs Docker, a `polecat.yaml` project registry, and the environment listed under
[Polecat containers](README.md#polecat-containers-aops).

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
