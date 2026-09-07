# pkb

PKB custodian (`pauli`), memory skills, and client integration for the PKB MCP server.

## Components

### Agents

| Agent   | Purpose                                                                  |
| ------- | ------------------------------------------------------------------------ |
| `pauli` | Custodian of the PKB and effectual strategist. Sole writer to the graph. |

### Skills

| Skill       | Purpose                                                            |
| ----------- | ------------------------------------------------------------------ |
| `hydrate`   | Fast semantic search producing a shortlist of IDs.                 |
| `q`         | Strategic intake: places, connects, and values tasks on the graph. |
| `remember`  | Continuous capture and consolidation of durable knowledge.         |
| `reconcile` | Truth maintenance over task statuses and finished PRs.             |
| `learn`     | Systemic root-cause diagnosis of failure classes.                  |
| `tick`      | Periodic sweep to advance stalled in-flight epics.                 |

### Hooks

| Event              | Purpose                                                        |
| ------------------ | -------------------------------------------------------------- |
| `UserPromptSubmit` | Grounds user prompts in PKB context or emits honesty reminder. |

## Configuration

| Setting                | Source      | Purpose                                                               |
| ---------------------- | ----------- | --------------------------------------------------------------------- |
| `PKB_MCP_URL`          | environment | HTTP endpoint for the PKB MCP server.                                 |
| `AOPS_UVX_SEARCH_PATH` | environment | Optional colon-separated path to find `uvx` for `scripts/run-mcp.sh`. |

Access to `$ACA_DATA` is strictly through MCP tools; direct filesystem manipulation is prohibited.

## Dependencies

- External PKB MCP server at `$PKB_MCP_URL`.
- `lib/hooks/` injected at build time.
- `uv` (for `uvx` MCP launching).
