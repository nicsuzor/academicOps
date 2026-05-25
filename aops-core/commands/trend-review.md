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

# /trend-review — Survey Shortcut (trend mode)

**Purpose**: Shortcut that delegates to the survey skill in `trend` mode. Reviews many sessions to assess whether a SYSTEM (gate, agent, skill, workflow) is achieving its goals across the population.

**Distinction from /learn**: `/learn` reviews individual sessions for agent behavior quality. `/trend-review` reviews MANY sessions to assess systemic effectiveness.

## Dispatch

Delegate to junior with the extended tool set the survey skill requires:

```python
Agent(
  subagent_type='junior',
  prompt="""Read aops-core/skills/survey/SKILL.md. Execute in trend mode.

Context from user: <paste the review question and any parameters — component to assess, time window, success criteria, specific concern>

If consuming inputs from dogfood outputs, apply the Phase 0 gate from aops-core/skills/dogfood/SKILL.md as the Phase 0 verification gate before inclusion.

Follow the trend mode workflow exactly: define question → identify data sources → sample strategically → deep-read each sample → synthesize → produce report → save report.""",
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

The dispatched junior agent owns the session from here. The main context is clean.

## Arguments

- `/trend-review` — clarify the review question interactively, then execute
- `/trend-review "How well is enforcer + RBG catching axiom violations?"` — pass the question directly
- `/trend-review <component> [--since <date>]` — assess a specific component over a time window

## What this command does NOT do

- Does not fix the component — it assesses effectiveness only.
- Does not review individual agent behavior — use `/learn` for that.
- Does not produce a numeric score — qualitative assessment with evidence.

## See also

- Full trend workflow: `aops-core/skills/survey/SKILL.md` (trend mode)
- Individual session review: `/learn` (survey skill, retro mode)
- Issue triage: `/issue-sweep` (survey skill, sweep mode)
