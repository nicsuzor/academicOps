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

Delegate to junior with the extended tool set the survey skill requires:

```python
Agent(
  subagent_type='junior',
  prompt="""Read aops-core/skills/survey/SKILL.md. Execute in retro mode.

Context from user: <paste user's invocation context here — transcript path if specified, or omit for auto-select>

Follow the canonical retro mode workflow defined in aops-core/skills/survey/SKILL.md to produce forensic findings including Causal chain and Framework layer fields.

**`recusal` — hard constraint**: /learn is the forensic phase. You are recused from proposing framework change motivated by the transcript you just read. What counts as forensic includes structural articulation ("design X is impossible because Y") but you may NOT propose how to fix it. Do NOT include "suggested axiom", "add a gate", "propose a mechanism", or any cost-ladder placement in the report or the filed issues. The detached judgment phase (sweep mode / /issue-sweep) reads your forensic report later, with no prior exposure to this incident, and is the only agent allowed to author rule changes. Recency is bias; the split is the discipline that prevents it.""",
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

- `/learn` — auto-select the most recent unreviewed transcript
- `/learn <path>` — review the specified transcript (pass a markdown path, not a `.jsonl`)
- `/learn <session-id>` — review the session matching that ID

**Transcript source.** Review the human-readable **markdown** transcript, never the raw
session JSON/JSONL. The markdown corpus lives at `$AOPS_SESSIONS/transcripts/YYYY-MM/`,
filenames `YYYYMMDD-HHMM-<shortid>-<project>-claude-full.md` (preferred) with a
`-abridged.md` sibling as fallback. A session ID resolves to its markdown via the embedded
short id (first 8 chars of the UUID) — `ls "$AOPS_SESSIONS/transcripts"/*/*-<shortid>-*-claude-full.md`
— not to the raw `.jsonl` under `~/.claude/projects/`. The full resolution order
(`-full.md` → `-abridged.md` → raw `.jsonl` only as a disclosed last resort) and the
transcript-quality gate (stop and ask the user to fix/regenerate a missing, truncated, or
tool-stripped transcript rather than reviewing the raw JSONL silently) are defined in
`skills/survey/SKILL.md` retro-mode Step 1 — the dispatched agent follows them.

## What this command does NOT do

- Does not run inline — always dispatches to pauli.
- Does not fix issues — it identifies and files them.
- Does not review code — it reviews agent behavior and framework compliance.

## See also

- Full retro workflow: `aops-core/skills/survey/SKILL.md` (retro mode)
- Trend analysis: `/trend-review` (survey skill, trend mode)
- Issue triage: `/issue-sweep` (survey skill, sweep mode)
