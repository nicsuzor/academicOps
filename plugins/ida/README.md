# ida

Strategic interface and sole user-facing agent in academicOps.

## Components

### Agents

| Agent | Purpose                                                                     |
| ----- | --------------------------------------------------------------------------- |
| `ida` | Strategic face to the user. Plans, prioritises, and audits. Never executes. |

### Skills

| Skill           | Purpose                                                            |
| --------------- | ------------------------------------------------------------------ |
| `premise-check` | Audits logical integrity of incoming reports and records verdicts. |
| `strategize`    | Evaluates altitude, tests effectual commitments, and routes work.  |

### Hooks

| Handler                 | Event           | Purpose                                         |
| ----------------------- | --------------- | ----------------------------------------------- |
| `premise_check_arm`     | `PostToolBatch` | Arms premise check on subagent dispatch.        |
| `premise_check_handler` | `PreToolUse`    | Blocks dispatch while premise check is pending. |

Verdict recording: `skills/premise-check/scripts/verdict.py`.
