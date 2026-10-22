# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), or Antigravity
- Node.js and `@argdown/cli` (`npm install -g @argdown/cli`) for Argdown argument gating
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

- **Local Claude Code**: `claude mcp add --transport http --scope user services <PKB_MCP_URL>`. Must use `--scope user`; `--scope local` was observed to register nothing.
- **Claude Code Cloud / Cowork**: The claude.ai account connector named `services`.
- **Antigravity (agy)**: Configured in user-level MCP settings (`~/.gemini/antigravity-cli/settings.json` or `~/.gemini/antigravity-cli/mcp/services.json`).

Plugins install with no `--config`: `orchestrate`, `rbg`, `tools`, `ts`, and `aops-debug` install the same way as `pkb` and `aops`.

Nothing else has a default. Set the environment variables each plugin needs
before first use -- the full list is in [`README.md`](README.md#configure),
and each plugin's own `plugins/<dir>/README.md` documents its complete
surface.

## Prompt hydration credentials

The `ida` plugin's `UserPromptSubmit` hook searches the PKB at `PKB_MCP_URL`
with every prompt. The hook is a separate process: it cannot use the OAuth
token the client holds for its own `services` connection, so it needs its own
credential in the environment the client is launched from (the container or
launchd environment, not the agent's shell). Set one of:

- `PKB_MCP_HEADERS` -- a JSON object of HTTP headers, e.g.
  `{"Authorization": "Bearer <token>"}`
- `WORKER_MCP_TOKEN_ID` and `WORKER_MCP_TOKEN_SECRET` -- a Cloudflare Access
  service token without polecat dispatch access, the default
- `DISPATCHER_MCP_TOKEN_ID` and `DISPATCHER_MCP_TOKEN_SECRET` -- the
  dispatcher's Cloudflare Access service token, used only when the worker pair
  is absent

**Check it is working.** A grounded turn carries
`<academicOps PKB search results>` in its hook context. A failing one carries
`aops hooks: handler 'search_the_pkb' failed with ...`. The MCP client reports
an HTTP 401 as `MCPError(-32603, 'Server returned an error response')`; seen
on every prompt, that means the hook has no valid credential.

**Find the cause.** From where the client runs, send the MCP `initialize`
request with the headers the hook would send (add `-H` for each), and read the
status:

```bash
curl -sS -D - -o /dev/null -X POST "$PKB_MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

| Status | Meaning | Fix |
| - | - | - |
| `401` with `WWW-Authenticate: Bearer ... error="invalid_token"` | No credential reached the endpoint, or it has expired | Set one of the variables above in the client's launch environment |
| `403` | Credential sent but not authorised | Grant it access at the gateway |
| `200` | Endpoint and credential are good | The fault is in the hook or PKB server; read the logged exception |
| no response | Endpoint unreachable | Check `PKB_MCP_URL` and network reach |

To confirm the PKB itself is up, call `pkb_search` through the client's own
`services` connection; it authenticates separately from the hook.

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

The polecat container image and launcher are maintained outside this repository and supplied by the installer, together with any Docker MCP server registered behind the `services` portal.

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
