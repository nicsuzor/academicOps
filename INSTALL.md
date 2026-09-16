# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), or Antigravity
- Docker, only if you want polecat's containerised workers

## Knowledge Base (services MCP server)

The `services` MCP server connects your agent to the Personal Knowledge Base (PKB) and is installed at user level on every surface, never shipped inside a plugin:

- **Local (Claude Code CLI / Desktop):**
  ```bash
  claude mcp add --scope user services <PKB_MCP_URL>
  ```
  Must use `--scope user` (`--scope local` was observed to register nothing into global project configs).
- **Cloud / Cowork:**
  Add the claude.ai account connector named `services` pointing to your PKB MCP URL.
- **Antigravity (`agy`):**
  Configure the `services` server in `~/.gemini/config/mcp_config.json`:
  ```json
  {
    "mcpServers": {
      "services": {
        "serverUrl": "<PKB_MCP_URL>"
      }
    }
  }
  ```

## From the release channel

```bash
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install pkb@academicOps
claude plugin install aops@academicOps
```

`orchestrate`, `rbg`, `tools`, `ts`, and `aops-debug` install the same way as
`aops`, with no `--config`.

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
