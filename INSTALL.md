# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), or Antigravity
- Docker, only if you want containerised worker sandboxes (`sbx` / `pc`)

## From the release channel

```bash
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install aops@academicOps
export PKB_MCP_URL=<your PKB MCP endpoint>
```

`orchestrate`, `rbg`, `tools`, `ts`, and `aops-debug` install the same way.
`PKB_MCP_URL` is an environment variable, read by whichever plugin needs it --
no manifest declares a `userConfig` key for it or for anything else.

Nothing has a default. Set the environment variables each plugin needs before
first use -- the full list is in [`README.md`](README.md#configure), and each
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

## Docker Sandboxes (`sbx` / `pc`)

Isolated worker sandboxes run via Docker Sandboxes (`sbx`) using kits defined under `lib/kits/` (`lib/kits/claude`, `lib/kits/agy`, and `lib/kits/aops`). The `pc` / `polecat.sh` wrapper script (`scripts/polecat.sh`, symlinked to `~/.local/bin/pc`) handles environment forwarding and kit assembly across repositories. See `specs/dispatch/dispatch-system.md`.

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
