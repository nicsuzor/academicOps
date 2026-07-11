# Hook Message Templates

Templates for user-facing messages and context injections rendered by the gate
engine (`lib/gates/definitions.py`, `lib/gates/engine.py`) via
`lib/template_registry.py`. Every template file has a corresponding
`TemplateSpec` entry there — the registry is the single source of truth for
which template a given key resolves to.

## Template Index

| Template                            | Gate                   | Purpose                                              |
| ----------------------------------- | ---------------------- | ---------------------------------------------------- |
| `hydration-gate-warn.md`            | router (unconditional) | Lightweight skills-routing hint                      |
| `pkb-nudge.md`                      | router (unconditional) | Static UPS nudge to search the PKB                   |
| `task-notification-guidance.md`     | router (unconditional) | Guidance on background task-notification prompts     |
| `exit-reflection-context.md`        | `exit_reflection`      | Session record for the FULL-tier checklist           |
| `exit-reflection-bound.md`          | `exit_reflection`      | Status message when a task is bound                  |
| `exit-reflection-complete.md`       | `exit_reflection`      | Status message when a legal exit fires               |
| `exit-reflection-policy-message.md` | `exit_reflection`      | Short message, FULL tier blocks/warns                |
| `exit-reflection-policy-context.md` | `exit_reflection`      | Full checklist injected on Stop, FULL tier           |
| `exit-reflection-lite-reminder.md`  | `exit_reflection`      | Lightweight honesty reminder, LITE tier              |
| `exit-reflection-degraded.md`       | `exit_reflection`      | Escape-hatch message when FULL tier degrades to warn |
| `ida-reminder.md`                   | `ida`                  | Head-surface Stop honesty check                      |
| `ida-askuserquestion-reminder.md`   | `ida`                  | Capability-verification nudge on `AskUserQuestion`   |

See [`specs/enforcement/GATES.md`](../../../specs/enforcement/GATES.md) for the runtime catalogue of every gate.

## Editing Templates

1. Templates use standard `{{placeholder}}` syntax.
2. Placeholders must be defined in `TemplateSpec` in `lib/template_registry.py`.
3. Keep messages concise and action-oriented.
4. Deleting a gate means deleting its templates too (replace, don't version) — do not leave orphaned `.md` files behind.
