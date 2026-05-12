---
name: learn
type: command
category: instruction
description: Thin shortcut — delegates to the survey skill in retro mode. Surveys recent transcripts, classifies issues, files GitHub bug reports.
triggers:
  - "learn"
  - "retro"
  - "transcript review"
  - "session retro"
  - "review session"
  - "file a bug"
  - "framework issue"
  - "knowledge capture"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
allowed-tools: Agent
permalink: commands/learn
---

# /learn — Survey Shortcut (retro mode)

**Purpose**: Shortcut that delegates to the survey skill in `retro` mode. Reviews a recent session transcript through a framework-development lens, identifies problems, and files GitHub issues.

**Privacy rule**: Anonymise all findings before filing. No real names, emails, student details, or session dumps in GitHub issues.

## Workflow

Delegate to pauli with the extended tool set the survey skill requires:

```python
Agent(
  subagent_type='aops-core:pauli',
  prompt="""Read aops-core/skills/survey/SKILL.md. Execute in retro mode.

Context from user: <paste user's invocation context here — transcript path if specified, or omit for auto-select>

Follow the retro mode workflow exactly: select transcript → read in full → review against all seven lenses → for each finding produce facts + most-general Root Cause Category + the rule already in place at the time (if any) + an impact statement → file forensic issues (no remediation proposals) → stamp transcript → framework reflection.

**A17 (Recusal) — hard constraint**: /learn is the forensic phase. You are recused from proposing framework change motivated by the transcript you just read. Do NOT include "suggested axiom", "add a gate", "propose a mechanism", or any cost-ladder placement in the report or the filed issues. The detached judgment phase (sweep mode / /issue-sweep) reads your forensic report later, with no prior exposure to this incident, and is the only agent allowed to author rule changes. Recency is bias; the split is the discipline that prevents it.""",
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

The dispatched pauli agent owns the session from here. The main context is clean.

## Arguments

- `/learn` — auto-select the most recent unreviewed transcript
- `/learn <path>` — review the specified transcript
- `/learn <session-id>` — review the session matching that ID

## What this command does NOT do

- Does not run inline — always dispatches to pauli.
- Does not fix issues — it identifies and files them.
- Does not review code — it reviews agent behavior and framework compliance.

## See also

- Full retro workflow: `aops-core/skills/survey/SKILL.md` (retro mode)
- Trend analysis: `/trend-review` (survey skill, trend mode)
- Issue triage: `/issue-sweep` (survey skill, sweep mode)
