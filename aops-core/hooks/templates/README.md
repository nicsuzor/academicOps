# Hook Templates

This directory contains message templates used by framework hooks. Templates allow agent-facing messages to be edited without modifying Python code.

## Format

Templates are markdown files with YAML frontmatter:

```markdown
---
name: template-name
title: Human-readable Title
category: template
description: |
  What this template is used for.
  Variables: {var_name} - Description of variable
---

Template content goes here. Use {variable_name} for interpolation.
```

## Usage

Templates are loaded using `lib.template_loader.load_template()`:

```python
from pathlib import Path
from lib.template_loader import load_template

# Load without variables
content = load_template(Path("hooks/templates/my-template.md"))

# Load with variable interpolation
content = load_template(
    Path("hooks/templates/my-template.md"),
    {"var_name": "value"}
)
```

## Current Templates

| Template                          | Used By                  | Purpose                                    |
| --------------------------------- | ------------------------ | ------------------------------------------ |
| `custodiet-context.md`            | `custodiet_gate.py`      | Full context for compliance checks         |
| `custodiet-instruction.md`        | `custodiet_gate.py`      | Short instruction to spawn custodiet       |
| `hydration-gate-block.md`         | `hydration_gate.py`      | Message when blocking without hydration    |
| `hydration-gate-warn.md`          | `hydration_gate.py`      | Warning when hydration skipped (warn mode) |
| `prompt-hydrator-context.md`      | `user_prompt_submit.py`  | Full context for prompt hydration          |
| `prompt-hydration-instruction.md` | `user_prompt_submit.py`  | Short instruction to spawn hydrator        |
| `fail-fast-reminder.md`           | `fail_fast_watchdog.py`  | Reminder when tool returns error           |
| `task-gate-block.md`              | `task_required_gate.py`  | Block message for three-gate check failure |
| `task-gate-warn.md`               | `task_required_gate.py`  | Warning message for warn-only mode         |
| `overdue-enforcement-block.md`    | `overdue_enforcement.py` | Block when compliance check overdue        |

## Adding New Templates

1. Create a `.md` file with YAML frontmatter
2. Document any variables in the frontmatter description
3. Update the hook to use `load_template()` from `lib.template_loader`
4. Add the template to the table above

## Error Handling

- `FileNotFoundError` is raised if template is missing (fail-fast)
- `KeyError` is raised if template references undefined variables
- Hooks should catch and handle errors appropriately for their use case
