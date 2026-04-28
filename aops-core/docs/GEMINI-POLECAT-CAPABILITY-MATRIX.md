# Gemini Polecat Capability Matrix

Reference for agents building or debugging Gemini-mode polecats (`polecat run -g`).
Documents the validated tool surface, known limitations, and the pre-release
validation protocol that catches MCP-access regressions before they ship.

## Background: the 2026-04-28 silent-data-loss incident

A Gemini spike polecat completed its investigation but could not call
`release_task` because `gemini-extension.json` was missing `PKB_MCP_URL` in the
pkb MCP server env block (the field had `RUST_LOG: warn` instead). The worker
logged "I do not have direct access to the remote task management tools" and
exited. The result would have been lost without the supervisor manually
transcribing from stdout. Fixed in PR #784.

This incident revealed two gaps:

1. **No static validation** of the Gemini extension MCP config — the test suite
   didn't assert `PKB_MCP_URL` was present in the source `gemini-extension.json`.
2. **No E2E test** for non-PR (spike/knowledge) task result persistence.

Both are now addressed. See [Validation](#validation) below.

---

## Capability matrix

| Capability                                       | Claude polecat | Gemini polecat | Notes                                                                       |
| ------------------------------------------------ | -------------- | -------------- | --------------------------------------------------------------------------- |
| PKB MCP tools (`release_task`, `get_task`, etc.) | ✓              | ✓              | Via HTTP/SSE transport; `PKB_MCP_URL` injected into both                    |
| File tools (read/write/replace/glob)             | ✓              | ✓              |                                                                             |
| Shell execution                                  | ✓              | ✓              |                                                                             |
| Git operations                                   | ✓              | ✓              |                                                                             |
| GitHub CLI (`gh`)                                | ✓              | ✓              |                                                                             |
| aops-core skills (`activate_skill`)              | ✓              | ✓              | Gemini: via `gemini-extension.json` `tools` array                           |
| Framework agents (enforcer, rbg, etc.)           | ✓              | Partial        | Gemini loads from `agents/` in the extension; frontmatter keys differ       |
| Hooks (gate enforcement)                         | ✓              | Partial        | Gemini router fires but tool-name differences apply                         |
| Claude-specific MCP servers                      | ✓              | ✗              | Claude Code reads from `.mcp.json`; Gemini uses `gemini-extension.json`     |
| Web search (`WebSearch` tool)                    | ✓              | ✓              | Gemini: `google_web_search` builtin                                         |
| Stop hook (container exit signal)                | ✓              | ✗              | Gemini has no stop hook; polecat uses PKB-poll termination watchdog instead |

### Known Gemini agent definition errors

Gemini logs `[ExtensionManager] Error ... Unrecognized key(s) in object: 'skills', 'subagents'`
at every boot for agents with Claude-Code-only frontmatter keys. This is cosmetic
noise from the Claude-side agent definitions leaking into the Gemini build.
It does **not** affect tool availability but is a signal that the Claude/Gemini
build surface is drifting. See `tests/e2e/test_gemini_extension_validation.py`
for the static checks that gate this.

---

## MCP wiring

Gemini polecats access PKB over HTTP/SSE transport. The wiring is:

```
polecat run -g
  → _build_docker_cmd(cli_tool="gemini", env={PKB_MCP_URL: ..., ...})
  → docker run -e PKB_MCP_URL=... aops-crew gemini ...
  → gemini loads ~/.gemini/extensions/aops-core/gemini-extension.json
  → mcpServers.pkb.command: "bash scripts/run-mcp.sh"
  → mcpServers.pkb.env: { ACA_DATA: ..., PKB_MCP_URL: ${PKB_MCP_URL} }
  → run-mcp.sh reads PKB_MCP_URL → launches pkb_perf_proxy.py in HTTP mode
  → Gemini session has full PKB MCP tool set
```

The critical link is `mcpServers.pkb.env.PKB_MCP_URL`. If that field is missing
or wrong, `run-mcp.sh` has no URL, falls through to local stdio, and the
container has no `pkb` binary — zero PKB tools in the session.

### Claude vs Gemini MCP path

Claude polecats get MCP config from `.mcp.json` in the worktree (written by
`create_sandbox_settings()`) **and** from the `PKB_MCP_URL` env var that
`_build_docker_cmd` injects via `docker run -e`. Either path is sufficient.

Gemini polecats get MCP config **only** from `gemini-extension.json`. The env
var reaches the container, but unless `gemini-extension.json` explicitly passes
it into the MCP server subprocess env, the server never sees it. Both the
container env and the extension manifest env block must be correct.

---

## Validation

### Pre-release checklist (run before every release)

These tests are fast enough to run on every PR:

```bash
# Static validation — no Docker, no Gemini binary required.
uv run pytest tests/e2e/test_gemini_extension_validation.py -v
```

This includes `TestSourceManifestMcpConfig` which specifically asserts:

- `pkb` is registered as an MCP server in `gemini-extension.json`
- `PKB_MCP_URL` is in the pkb server env block
- `PKB_MCP_URL` value uses template substitution (`${PKB_MCP_URL}`)
- `RUST_LOG` is not in the pkb server env block (the exact 2026-04-28 regression)

### Full integration validation (pre-release with Gemini auth)

```bash
# Requires: Docker + aops-crew image, PKB_MCP_URL, Gemini credentials
POLECAT_E2E=1 POLECAT_E2E_PROJECT=aops \
uv run pytest tests/polecat/test_gemini_pkb_persistence_e2e.py -v -m e2e
```

This creates a real spike task, runs a Gemini polecat against it, and asserts:

1. The task reaches a terminal status (worker called `release_task`)
2. The task body is non-empty (worker wrote a summary)

If the test times out (10 min), PKB MCP is broken inside the Gemini container.
Check `gemini-extension.json` first, then `aops-core/scripts/run-mcp.sh`.

The termination test also covers this path:

```bash
POLECAT_E2E=1 POLECAT_E2E_PROJECT=aops \
uv run pytest tests/polecat/test_polecat_termination_e2e.py -v -m e2e
```

### Gemini sandbox integration (optional, requires `RUN_GEMINI_SANDBOX_IT=1`)

```bash
RUN_GEMINI_SANDBOX_IT=1 GEMINI_AUTH_IN_CONTAINER=1 \
uv run pytest tests/polecat/test_gemini_sandbox.py -v -m integration
```

---

## Diagnosing PKB MCP access failures

If a Gemini polecat says "I do not have direct access to task management tools":

1. **Check `gemini-extension.json`** — `mcpServers.pkb.env.PKB_MCP_URL` must be
   `"${PKB_MCP_URL}"`. This is what the static tests validate.

2. **Check `PKB_MCP_URL` in the container** — run the integration test to confirm
   the env var reaches the container:
   ```bash
   uv run pytest tests/polecat/test_cli_docker_integration.py::TestDockerEndState::test_pkb_url_reaches_container -v
   ```

3. **Check `run-mcp.sh`** — if `PKB_MCP_URL` is set but MCP still fails, the
   script at `aops-core/scripts/run-mcp.sh` may be failing to find `uvx` or
   `pkb_perf_proxy.py`. Check the Gemini session transcript (`.aops/polecats/<task-id>.jsonl`).

4. **Check Tailscale** — the PKB MCP server is at
   `http://services.stoat-musical.ts.net:8026/mcp`. If the container can't
   reach Tailscale, `PKB_MCP_URL` needs to use the fallback public endpoint.
   See `aops-core/docs/MCP-TRANSPORT.md`.
