# pkb

Memory: pauli, the sole writer to the Personal Knowledge Base, and the client
wiring for the PKB MCP server.

## What it provides

### Agents

| Agent   | Does                                                                                                              |
| ------- | ----------------------------------------------------------------------------------------------------------------- |
| `pauli` | Logician, effectual strategist, and custodian of the PKB. Every mutation routes here. Call first, and call often. |

### Skills

| Skill       | Does                                                                                                              |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| `hydrate`   | A few reworded searches, cut to a shortlist of ids the caller can ask more about. Always first.                   |
| `q`         | Intake -- place one ask on the graph under the right parent, wired to what it serves and valued at intake.        |
| `remember`  | Capture knowledge as it emerges; consolidate episodic records into durable notes.                                 |
| `reconcile` | Establish what is true about in-flight and finished work, write it back, return the affected tasks to `inbox`.    |
| `learn`     | Diagnose an incident back to its structural cause, then route the lesson to the one destination its scope claims. |
| `tick`      | Periodic check to nudge high-intent epics along between steps.                                                    |

### Hook

| Event              | Does                                                                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | `search_the_pkb` -- grounds every prompt in the PKB (`pkb search`), falling back to the honesty reminder when the search yields nothing. |

## Configuration

There are no defaults. No URL, host, port, path, or token is baked into anything
this plugin ships, and it declares no client `userConfig` options.

| Setting                | Where it comes from | For                                                                                                                                                                                                                         |
| ---------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PKB_MCP_URL`          | environment         | The streamable-HTTP endpoint of the PKB MCP server. The `services` server config resolves it at launch (`fastmcp run "$PKB_MCP_URL"`) on every client, so it must already be set in the environment that starts the client. |
| `AOPS_UVX_SEARCH_PATH` | environment         | Optional, and only read by `scripts/run-mcp.sh`: colon-separated directories to probe for `uvx` when the launching client supplies a minimal `PATH`.                                                                        |

`scripts/run-mcp.sh` is a stdio launcher for clients that cannot be handed the
endpoint at launch. It requires `PKB_MCP_URL` and exits non-zero without it,
strips any trailing slash (the endpoint 404s with one), finds `uvx`, and execs
the same server. The build wires it into the Cowork upload zip with the URL
resolved into the server's `env` block; the ordinary client dists keep the
environment-variable form.

`$ACA_DATA` is the PKB's own storage. Nothing in this plugin reads or writes it
as a filesystem path -- every read and write goes through the MCP tools, and the
skills forbid reaching around them.

## Depends on

- A PKB MCP server reachable at `$PKB_MCP_URL`. The server is external to this
  plugin; the plugin ships client wiring only.
- `lib/hooks/`, injected into `hooks/` at build time (`manifest/plugin.toml`).
- `uv`, for `uvx` to launch the MCP server.
