# ida

The strategic face, and the only agent that speaks to the user.

## What it provides

### Agents

| Agent | Does                                                                                                                                                |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ida` | The strategic face, and the only agent that speaks to the user. Plans, prioritises, and holds anything needing the user's decision. Never executes. |

### Skills

| Skill           | Does                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `premise-check` | Evaluate the logical integrity of reports Ida receives and record a reasoned verdict (mandatory audit requirement). |

### Hooks

| Handler                 | Event           | Does                                                                                                            |
| ----------------------- | --------------- | --------------------------------------------------------------------------------------------------------------- |
| `premise_check_arm`     | `PostToolBatch` | Arms the premise check when `aops:ida` dispatches a subagent (`Agent` tool call), pending a recorded verdict.   |
| `premise_check_handler` | `PreToolUse`    | Refuses the next `Agent` dispatch while the premise check is armed, until `premise-check`'s verdict disarms it. |

Verdict recording and OpenTelemetry trace emission live in
`hooks/premise_check_verdict.py`, invoked via `skills/premise-check/scripts/verdict.py`.

## Depends on

- `lib/hooks/`, injected into `hooks/` at build time (`manifest/plugin.toml`).
