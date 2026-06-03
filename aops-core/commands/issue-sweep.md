---
name: issue-sweep
type: command
category: instruction
description: Thin shortcut — delegates to the survey skill in sweep mode. Quality-gated GitHub issue triage — one cycle per invocation.
triggers:
  - "issue sweep"
  - "sweep issues"
  - "triage issues"
  - "drain issue backlog"
  - "process open issues"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
  - operations
  - quality-assurance
allowed-tools: Agent
permalink: commands/issue-sweep
---

# /issue-sweep — Survey Shortcut (sweep mode)

**Purpose**: Shortcut that delegates to the survey skill in `sweep` mode. Runs ONE cycle of the open-issue sweep on `nicsuzor/academicOps`. Classifies ≤ 20 issues, presents the dispatch plan, waits for sign-off, executes confirmed actions, logs the cycle. **HALT after one cycle.**

Runs **undirected** by default (cursor-driven over the oldest-untriaged batch) or **directed** when given a focus — a specific blocker / failure / issue to investigate and prioritise first. A directed sweep is _focus-first, not focus-only_: it still scans the general backlog, and a focus sets attention only — it does not relax the escalation evidence bar (see the survey skill's "Directed vs undirected sweep").

**Hard halts**: No silent dispatch. No improvised dispositions (sixth bucket). No cursor in task body — labels are the cursor.

## Dispatch

Delegate to junior (jr) — interactive confirmation gates require user interaction that pauli's lean profile doesn't support:

```python
Agent(
  subagent_type='aops-core:jr',
  prompt="""Read aops-core/skills/survey/SKILL.md. Execute in sweep mode.

Context from user: <paste user's invocation context — batch size override, dry-run flag, or a FOCUS (a specific blocker / failure / issue number to investigate and prioritise first). If a focus is given, run a directed sweep per the skill's "Directed vs undirected sweep": triage the focal root-cause cluster first, then continue the general backlog scan; focus sets attention only, not the escalation bar.>

Follow the sweep mode workflow exactly: pre-flight → pull batch (focal cluster first if directed) → classify → present plan and gate → execute confirmed → append cycle log → /verify handoff → HALT.""",
  tools=[
    'Bash', 'Read', 'Grep', 'Glob', 'Skill', 'AskUserQuestion',
    'mcp__plugin_aops-core_pkb__get_task',
    'mcp__plugin_aops-core_pkb__create_task',
    'mcp__plugin_aops-core_pkb__update_task',
    'mcp__plugin_aops-core_pkb__append',
    'mcp__plugin_aops-core_pkb__task_search',
  ],
)
```

The dispatched jr agent owns the session from here. The main context is clean.

## Arguments

- `/issue-sweep` — run one undirected cycle, batch size 20 (default)
- `/issue-sweep <issue#>` — directed cycle: investigate that issue and its root-cause cluster first, then continue the general backlog scan
- `/issue-sweep "<focus phrase>"` — directed cycle aimed at a described blocker/failure (resolves to the matching issue cluster)
- `/issue-sweep --batch 10` — override batch size for this cycle
- `/issue-sweep --dry-run` — produce cycle plan and gate, but do not execute or write cycle log

## What this command does NOT do

- Does not fix any issue — single-tasks and fix-epics are queued in PKB, executed later.
- Does not invoke `/supervisor` — fix-epics are left `queued`; user picks which to run next.
- Does not run on a schedule — manual invocation only until the rubric is validated over 3–5 cycles.
- Does not consume `/loop` — cadence is decided after manual cycles prove the rubric.

## See also

- Full sweep workflow: `aops-core/skills/survey/SKILL.md` (sweep mode)
- Fix-epic execution: `/supervisor`
- Individual session review: `/learn` (survey skill, retro mode)
- Trend analysis: `/trend-review` (survey skill, trend mode)
