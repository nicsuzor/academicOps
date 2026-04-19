# Hook Message Templates

Templates for user-facing messages and context injections.

## Template Index

| Template                     | Used By            | Purpose                               |
| ---------------------------- | ------------------ | ------------------------------------- |
| `hydration-gate-warn.md`     | `router.py`        | Lightweight skills-routing hint       |
| `enforcer-policy-message.md` | `enforcer_gate.py` | Message when enforcer blocks/warns    |
| `enforcer-context.md`        | `enforcer_gate.py` | Instructions for enforcer subagent    |
| `handover-policy-message.md` | `handover_gate.py` | Message when stop blocked by handover |
| `qa-policy-message.md`       | `qa_gate.py`       | Message when stop blocked by QA       |
| `qa-context.md`              | `qa_gate.py`       | Instructions for QA subagent          |
| `stop-handover-block.md`     | `router.py`        | Context injection when stop blocked   |

## Editing Templates

1. Templates use standard `{{placeholder}}` syntax.
2. Placeholders must be defined in `TemplateSpec` in `lib/template_registry.py`.
3. Keep messages concise and action-oriented.
