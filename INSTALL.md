# Install academicOps

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), Antigravity (`agy`), or OpenClaw
- Node.js and `@argdown/cli` (`npm install -g @argdown/cli`) for Argdown argument gating
- Docker, only if you want polecat's containerised workers

## From the release channel

```bash
# 1. Register the services MCP server at user level:
claude mcp add --transport http --scope user services <your PKB MCP endpoint>

# 2. Install plugins from the marketplace:
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install ida@academicOps
claude plugin install james@academicOps
claude plugin install tools@academicOps
```

The `services` MCP server is installed at user level across all surfaces, never shipped inside a plugin:

- **Local Claude Code**: `claude mcp add --transport http --scope user services <PKB_MCP_URL>`. Must use `--scope user`; `--scope local` was observed to register nothing.
- **Claude Code Cloud / Cowork**: The claude.ai account connector named `services`.
- **Antigravity (agy)**: Configured in user-level MCP settings (`~/.gemini/antigravity-cli/settings.json` or `~/.gemini/antigravity-cli/mcp/services.json`).
- **OpenClaw**: Install the OpenClaw plugin bundles (`ida-openclaw`, `james-openclaw`, `tools-openclaw`, `ida-telegram-openclaw`, `aops-debug-openclaw`) from the `dist/openclaw/` directory-marketplace channel (or the `openclaw` release bundles) and configure `services` in your OpenClaw MCP settings.

Plugins install with no `--config`: `ida-telegram` and `aops-debug` install the same way as `ida`, `james` and `tools`.

Nothing else has a default. Set the environment variables each plugin needs
before first use -- the telemetry variables are in [`README.md`](README.md#telemetry--otel-tracing-architecture),
and each plugin's own `plugins/<dir>/README.md` documents its complete
surface.

## Prompt hydration credentials

The `ida` plugin's `UserPromptSubmit` hook searches the PKB at `PKB_MCP_URL`
with every prompt. The hook is a separate process: it cannot use the OAuth
token the client holds for its own `services` connection, so it needs its own
credential in the environment the client is launched from (the container or
launchd environment, not the agent's shell).

The hook, the tracer and the rest of the runtime read one Cloudflare Access
service-token pair, named after the HTTP headers it becomes:

- `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` -- sent as
  `CF-Access-Client-Id` and `CF-Access-Client-Secret` on PKB/MCP calls and on
  OTLP trace export. The launching context (interactive shell, polecat
  container, launchd, CI) decides which stored service token fills the pair;
  least privilege is the launcher's job (for example, a worker container gets
  a token without polecat dispatch access). Nothing reads the token from
  `OTEL_EXPORTER_OTLP_HEADERS`, which every OTel SDK in the process tree would
  pick up.

**Check it is working.** A grounded turn carries
`<academicOps PKB search results>` in its hook context. A failing one carries
`aops hooks: handler 'search_the_pkb' failed with ...`. The MCP client reports
an HTTP 401 as `MCPError(-32603, 'Server returned an error response')`; seen
on every prompt, that means the hook has no valid credential.

**Find the cause.** From where the client runs, send a stateless MCP `server/discover`
request with the headers the hook would send (add `-H` for each), and read the
status:

```bash
curl -sS -D - -o /dev/null -X POST "$PKB_MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' -H 'Mcp-Method: server/discover' \
  -d '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"probe","version":"0"}}}}'
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

`make install-dev` builds `dist/` (including `dist/openclaw/` for OpenClaw), registers it as a local marketplace named
`aops`, installs every plugin from it into Claude Code (and Antigravity when
`agy` is on `PATH`), and activates pre-commit. For OpenClaw, point your
OpenClaw plugin directory or marketplace config at `dist/openclaw/`.

`make uninstall-dev` reverses it and restores the release channel.

## Polecat

The polecat container image and launcher are maintained outside this repository and supplied by the installer, together with any Docker MCP server registered behind the `services` portal.

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
