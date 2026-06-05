---
name: trend-review
type: command
category: instruction
description: Thin shortcut — delegates to the survey skill in trend mode. Multi-session performance trend analysis.
triggers:
  - "trend review"
  - "performance trends"
  - "how well is X working"
  - "assess effectiveness"
  - "review many sessions"
modifies_files: true
needs_task: false
mode: execution
domain:
  - quality-assurance
  - framework
allowed-tools: Agent
permalink: commands/trend-review
---

# /trend-review — Performance Trend Analysis

Delegate to a `junior` agent to execute a multi-session performance trend analysis using the `survey` skill in `trend` mode.

## Dispatch

Invoke `junior` with the following parameters and tools:

```python
Agent(
  subagent_type='junior',
  prompt="""Read aops-core/skills/survey/SKILL.md. Execute in trend mode.

User context: <paste target component, timeframe, and evaluation criteria>

If analyzing dogfood outputs, apply the Phase 0 verification gate from aops-core/skills/dogfood/SKILL.md before inclusion.

Analyze strategic samples, synthesize systemic effectiveness, and produce a concise summary report of findings.""",
  tools=[
    'Bash', 'Read', 'Grep', 'Glob', 'Edit', 'Write', 'Skill',
    'mcp__plugin_aops-core_pkb__search',
    'mcp__plugin_aops-core_pkb__task_search',
    'mcp__plugin_aops-core_pkb__get_document',
    'mcp__plugin_aops-core_pkb__pkb_context',
    'mcp__plugin_aops-core_pkb__append',
    'mcp__plugin_aops-core_pkb__create_task',
    'mcp__plugin_aops-core_pkb__update_task',
  ],
)
```

## Output Expectations

- Produce a structured, evidence-backed evaluation report summarizing trends and systemic effectiveness of the target component.
- Keep the final report concise and focused on high-level findings and specific action points.
