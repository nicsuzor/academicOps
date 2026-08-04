# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), or Antigravity
- Docker, only if you want polecat's containerised workers

## From the release channel

```bash
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install ida@academicOps
claude plugin install pkb@academicOps --config pkb_mcp_url=<your PKB MCP endpoint>
```

`rbg`, `tools`, `ts`, and `aops-debug` install the same way. `--config` is
valid only against the plugin that declares the key; `pkb_mcp_url` belongs to
`pkb` alone.

Nothing has a default. Set the environment variables each plugin needs before
first use — the full list is in [`README.md`](README.md#configure), and each
plugin's own `plugins/<dir>/README.md` documents its complete surface.

## From source

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync
make install-dev
```

`make install-dev` builds `dist/`, registers it as a local marketplace named
`aops`, installs every plugin from it into Claude Code (and Antigravity when
`agy` is on `PATH`), merges the axioms into `~/.claude/settings.json`, and
activates pre-commit.

`make uninstall-dev` reverses it and restores the release channel.

## Polecat

Polecat is the containerised worker runner, shipped inside the `ida` plugin. It
needs Docker, a `polecat.yaml` project registry, and the environment listed under
[Polecat containers](README.md#polecat-containers-aops).

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
