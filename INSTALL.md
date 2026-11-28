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
claude plugin marketplace add nicsuzor/academicOps
claude plugin install ida@academicOps
claude plugin install crew@academicOps
claude plugin install sara@academicOps   # optional: remote dispatch to polecat containers
claude plugin install tools@academicOps
```

The `services` MCP server is installed at user level across all surfaces, never shipped inside a plugin:

- **Local Claude Code**: `claude mcp add --transport http --scope user services <PKB_MCP_URL>`. Must use `--scope user`; `--scope local` was observed to register nothing.
- **Claude Code Cloud / Cowork**: The claude.ai account connector named `services`.
- **Antigravity (agy)**: Configured in user-level MCP settings (`~/.gemini/antigravity-cli/settings.json` or `~/.gemini/antigravity-cli/mcp/services.json`).

Plugins install with no `--config`: `ida-telegram` and `aops-debug` install the same way as `ida`, `crew`, `sara` and `tools`.

Nothing else has a default. Set the environment variables each plugin needs
before first use -- the per-surface list is in
[Environment variables by surface](#environment-variables-by-surface), and
each plugin's own `plugins/<dir>/README.md` documents its complete surface.

## Environment variables by surface

Hooks and MCP servers are separate processes: they read only the environment
the client is launched from (the shell, launchd, the container, or the cloud
environment's settings), never the agent's own shell. Set each variable there.
No value is given here; every one is the installer's choice.

**Surfaces.** _Laptop_ is Claude Code on the user's own machine (CLI or the
desktop app's Code tab). _Telegram_ is an interactive Ida session carrying the
`ida-telegram` channel. _Crew container_ is a long-lived container running the
crew with the user's directions. _Web_ is Claude Code on the web, which runs
the crew. _agy_ is an interactive Antigravity session. A crew container that carries the
Telegram channel takes the Telegram column too. In a Cowork session the hooks
do nothing (see [`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md#hooks)), so
none of this applies there.

**Cells.** _required_: the hook refuses, fails or loses its purpose on that
surface without it. _optional_: read if set; behaviour degrades or falls back
without it. _not set_: leave it unset on that surface.

**Live tracing is crew's.** The OTel tracing hooks ship only in the `crew`
plugin (`plugins/crew/hooks/handlers.py`, span pipeline
`lib/hooks/claude_code_tracer.py`, agy spans `plugins/crew/hooks/agy_tracer.py`).
Every surface that runs the crew is traced live, because it carries the user's
directions and the responses to them. The tracer behaves the same on every
surface: a missing endpoint or a failed export warns, unless
`AOPS_TELEMETRY_FAILURE_MODE=block` is set, in which case `SessionStart`
refuses (`lib/hooks/claude_code_tracer.py`, `get_telemetry_failure_mode`).

**Polecat containers have no column.** A polecat is a headless worker
container with strictly limited permissions: it installs no plugins, has no
PKB access, and receives its instructions as its prompt. No hook runs there,
so nothing below is read there. When the container exits, the dispatch service
records the final output on the task and uploads the whole session log to the
trace store in one batch.

### Tracing (crew)

| Variable | Read at | Laptop | Telegram | Crew container | Web | agy |
| - | - | - | - | - | - | - |
| `GENAI_ENGINE_TRACE_ENDPOINT`, else `OTEL_EXPORTER_OTLP_ENDPOINT`, else `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` -- OTLP collector; first one set wins | `lib/hooks/claude_code_tracer.py` `discover_config`, `is_telemetry_configured`; `plugins/crew/hooks/handlers.py` `_format_session_metadata` | optional | required | required | required | optional |
| `GENAI_ENGINE_TRACE_PROTOCOL`, else `OTEL_EXPORTER_OTLP_PROTOCOL`, else `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | `lib/hooks/claude_code_tracer.py` `discover_config` | optional | optional | optional | optional | optional |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` -- one Cloudflare Access pair, sent as headers on OTLP export and on the PKB search (both halves or neither) | `lib/hooks/claude_code_tracer.py` `_cf_access_headers`; `plugins/crew/hooks/handlers.py` `_resolve_mcp_headers` | required | required | required | optional | required |
| `AOPS_TELEMETRY_FAILURE_MODE` -- `block` or `warn` | `lib/hooks/claude_code_tracer.py` `get_telemetry_failure_mode`; `plugins/crew/hooks/handlers.py` `session_start` | optional | optional | optional | optional | optional |
| `OTEL_SERVICE_NAME` | `lib/hooks/claude_code_tracer.py` `_build_and_export_spans`; `plugins/crew/hooks/handlers.py` `_format_session_metadata` | optional | optional | optional | optional | optional |
| `PHOENIX_PROJECT_NAME` | `lib/hooks/claude_code_tracer.py` `resolve_project_name` | optional | optional | optional | optional | optional |
| `BETA_TRACING_ENDPOINT` -- shown in the `SessionStart` banner only; the tracer never exports to it | `plugins/crew/hooks/handlers.py` `_format_session_metadata` | optional | optional | optional | optional | not set |
| `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` | `lib/hooks/claude_code_tracer.py` `_MAX_ATTR_BYTES` | optional | optional | optional | optional | optional |
| `HTTPS_PROXY` / `ALL_PROXY`; `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` / `SSL_CERT_FILE`; `OTEL_EXPORTER_OTLP_CERTIFICATE` / `OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE` -- egress proxy and CA for OTLP export | `lib/hooks/claude_code_tracer.py` `_proxy_http_kwargs` | optional | optional | optional | optional | optional |
| `AOPS_TRACER_STATE_DIR`, else `TRACER_STATE_DIR`, else `AOPS_TRACER_DIR` -- per-session tracer state | `lib/hooks/claude_code_tracer.py` `_tracer_state_dir`; `lib/hooks/dispatch.py` `_tracer_state_dir` | optional | optional | optional | optional | optional |
| `AOPS_AGENT_NAME` -- agent name when the payload has none | `lib/hooks/claude_code_tracer.py` `resolve_agent_name` | optional | optional | optional | optional | optional |
| `AOPS_TASK_ID`, `GENAI_ENGINE_TASK_ID` -- task id on spans | `lib/hooks/claude_code_tracer.py` `discover_config` | not set | not set | optional | not set | not set |
| `ANTIGRAVITY_APP_DATA_DIR` -- where agy token counts are read from | `plugins/crew/hooks/token_extractor.py` (Gemini conversation db lookup) | not set | not set | optional | not set | optional |

### PKB, sessions and credentials (crew)

| Variable | Read at | Laptop | Telegram | Crew container | Web | agy |
| - | - | - | - | - | - | - |
| `PKB_MCP_URL` -- PKB MCP endpoint; `SessionStart` raises without it | `plugins/crew/hooks/handlers.py` `_format_session_metadata`, `_run_pkb_search` | required | required | required | required | required |
| `PKB_MCP_TOOL_PREFIX` | `plugins/crew/hooks/handlers.py` `_post_mcp_search` | optional | optional | optional | optional | optional |
| `AOPS_SESSIONS` -- sessions directory; `polecat.yaml` read from it | `lib/hooks/claude_code_tracer.py` `_load_polecat_config`; `plugins/crew/hooks/handlers.py` `_BASIC_VARS` | optional | optional | optional | optional | optional |
| `POLECAT_HOME` -- worktree root named in crew's auto-mode rules; no hook reads it | `plugins/crew/manifest/auto-mode.json` | optional | optional | optional | optional | not set |
| `AOPS_BOT_GH_TOKEN` -- moved into `CLAUDE_ENV_FILE` at `SessionStart`; redacted from spans | `plugins/crew/hooks/handlers.py` `_BASIC_VARS`; `lib/hooks/claude_code_tracer.py` (redaction) | optional | optional | optional | optional | optional |
| `AOPS_GIT_CONFIG_GLOBAL` -- becomes session-scoped `GIT_CONFIG_GLOBAL` | `plugins/crew/hooks/handlers.py` `_isolate_credentials` | optional | optional | optional | optional | not set |
| `AOPS_SURFACE` -- surface tag on PKB search requests | `plugins/crew/hooks/handlers.py` `_resolve_surface` | optional | optional | optional | optional | optional |
| `AOPS_IMAGE_PLUGINS_VERSION`, `AOPS_IMAGE_STALE`, `AOPS_IMAGE_STALENESS_WARNING` -- baked-image metadata | `plugins/crew/hooks/handlers.py` `_resolve_plugin_version`, `session_start` | not set | not set | optional | not set | not set |
| `AOPS_SESSION_POINTER_DIR` | `plugins/crew/hooks/handlers.py`, `plugins/ida/hooks/handlers.py` `_session_pointer_dir` | optional | optional | optional | optional | optional |
| `AOPS_HOOK_LOG_PATH` -- hook fire log | `lib/hooks/dispatch.py` `_log_fire` | optional | optional | optional | optional | optional |
| `AOPS_SESSION_ID` -- written by `SessionStart` into `CLAUDE_ENV_FILE` | `plugins/crew/hooks/handlers.py`, `plugins/ida/hooks/handlers.py` `_export_session_id`; read by `lib/hooks/claude_code_tracer.py` `resolve_session_id` | not set | not set | not set | not set | not set |

### Premise-check gate (ida)

| Variable | Read at | Laptop | Telegram | Crew container | Web | agy |
| - | - | - | - | - | - | - |
| `PREMISE_CHECK_GATE_MODE`, else `PREMISE_CHECK_MODE` | `plugins/ida/hooks/hearsay_gate.py` `hearsay_handler` | optional | optional | optional | optional | optional |
| `AOPS_PREMISE_CHECK_DIR`, else `AOPS_PREMISE_GATE_DIR` -- gate state | `plugins/ida/hooks/hearsay_gate.py` `_state_dir` | optional | optional | optional | optional | optional |

### Telegram channel (ida-telegram)

Read by `plugins/ida-telegram/src/config.ts` `loadConfig` (from the process
environment, then `$STATE_DIR/.env`) unless noted. Every other surface: not set.

| Variable | Read at | Telegram |
| - | - | - |
| `TELEGRAM_BOT_TOKEN` | `loadConfig`; `server.ts` starts the bot only when set | required |
| `MINI_APP_URL`, else `IDA_WEB_URL` -- the Mini App's public URL; `loadConfig` throws without it | `loadConfig` | required |
| `IDA_TELEGRAM_ROLE` -- `primary` on the one instance that polls | `loadConfig`; `plugins/ida-telegram/src/role.ts` `checkRole` | required |
| `ALLOWED_USER_IDS`, else `TELEGRAM_ALLOW_FROM` | `loadConfig` | required |
| `STATE_DIR` | `loadConfig` | optional |
| `CF_ACCESS_TEAM_DOMAIN` (or `CF_ACCESS_TEAM_NAME`), `CF_ACCESS_AUD`, `CF_ACCESS_ALLOWED_EMAILS`, `CF_ACCESS_CERTS_URL`, `CF_ACCESS_KEYS` (or `CF_ACCESS_PUBKEY`) -- Mini App access check | `loadConfig` | optional |
| `IDA_BRIDGE_TOKEN`, else `BRIDGE_TOKEN` | `loadConfig` | optional |
| `VOICE_REPLIES`, `VOICE_TRANSCRIBE_CMD`, `VOICE_SPEAK_CMD` | `loadConfig` | optional |
| `GEMINI_API_KEY`, `GEMINI_TTS_VOICE` -- Gemini voice replies | `plugins/ida-telegram/scripts/speak-gemini.py` | optional |
| `TELEGRAM_API_BASE_URL`, `MAX_CHAT_CHARS`, `PORT`, `IDA_NAME` (or `INSTANCE_NAME`, `INSTANCE_ID`), `TELEGRAM_BOT_COMMANDS`, `TELEGRAM_AUTO_INTERRUPT`, `GITHUB_TOKEN` | `loadConfig` | optional |

### Other plugins

| Variable | Read at | Laptop | Telegram | Crew container | Web | agy |
| - | - | - | - | - | - | - |
| `ACA_DATA` -- user data root (signature image for `pdf`) | `plugins/tools/skills/pdf/scripts/generate_pdf.py` | optional | optional | optional | optional | optional |
| `COPE_EVALUATOR_OTEL_TRACE_PATH` -- the rule evaluator's OTel file; the evaluator is not wired | `lib/hooks/dispatch.py` `_get_evaluator_otel_trace` | not set | not set | not set | not set | not set |

The client sets these itself; never set them by hand: `CLAUDE_PLUGIN_ROOT`,
`AGY_PLUGIN_ROOT`, `CLAUDE_ENV_FILE`, `CLAUDE_PROJECT_DIR`,
`CLAUDE_CODE_SESSION_ID`, `ANTIGRAVITY_CONVERSATION_ID`,
`CLAUDE_CODE_IS_COWORK`, `CLAUDE_CODE_ENTRYPOINT`, and the `GITHUB_*` run
variables.

## Prompt hydration credentials

The `crew` plugin's `UserPromptSubmit` hook searches the PKB at `PKB_MCP_URL`
with every prompt. The hook is a separate process: it cannot use the OAuth
token the client holds for its own `services` connection, so it needs its own
credential in the environment the client is launched from (the container or
launchd environment, not the agent's shell).

The hook, the tracer and the rest of the runtime read one Cloudflare Access
service-token pair, named after the HTTP headers it becomes:

- `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` -- sent as
  `CF-Access-Client-Id` and `CF-Access-Client-Secret` on PKB/MCP calls and on
  OTLP trace export. The launching context (interactive shell, crew
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

`make install-dev` builds `dist/`, registers it as a local marketplace named
`aops`, installs every plugin from it into Claude Code (and Antigravity when
`agy` is on `PATH`), and activates pre-commit.

`make uninstall-dev` reverses it and restores the release channel.

## Polecat

The polecat container image and launcher are maintained outside this repository and supplied by the installer, together with any Docker MCP server registered behind the `services` portal.

## Design

Build stages, client adapters, and what installation is permitted to touch:
[`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md).
