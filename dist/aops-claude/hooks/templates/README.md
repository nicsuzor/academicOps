# Hook Message Templates

Templates for user-facing messages and context injections.

## Template Index

| Template                      | Used By             | Purpose                               |
| ----------------------------- | ------------------- | ------------------------------------- |
| `hydration-gate-warn.md`      | `router.py`         | Lightweight skills-routing hint       |
| `custodiet-policy-message.md` | `custodiet_gate.py` | Message when custodiet blocks/warns   |
| `custodiet-context.md`        | `custodiet_gate.py` | Instructions for custodiet subagent   |
| `handover-policy-message.md`  | `handover_gate.py`  | Message when stop blocked by handover |
| `qa-policy-message.md`        | `qa_gate.py`        | Message when stop blocked by QA       |
| `qa-context.md`               | `qa_gate.py`        | Instructions for QA subagent          |
| `stop-handover-block.md`      | `router.py`         | Context injection when stop blocked   |

## Editing Templates

1. Templates use standard `{{placeholder}}` syntax.
2. Placeholders must be defined in `TemplateSpec` in `lib/template_registry.py`.
3. Keep messages concise and action-oriented.
