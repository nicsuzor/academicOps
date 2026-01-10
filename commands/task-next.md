---
name: task-next
category: instruction
description: Get 2-3 task recommendations (should/enjoy/quick)
allowed-tools: Skill
permalink: commands/task-next
---

# /task-next

**Purpose**: Intelligent task selection assistant.

## Execution

Invoke the `daily` skill with focus mode to generate recommendations and update the focus dashboard.

```python
Skill(skill="daily", args="Regenerate the focus dashboard with additional recommendations")
```
