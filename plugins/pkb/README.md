# pkb

PKB custodian (`pauli`) and memory skills.

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

The PKB `services` MCP server is installed at user level (`services`) on each surface, not shipped inside the plugin.
Access to `$ACA_DATA` is strictly through MCP tools (`mcp__services__*`); direct filesystem manipulation is prohibited.

## Dependencies

- External PKB MCP server installed at user level (`services`).
- `lib/hooks/` injected at build time.
