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

# /learn — Analyze Session Transcripts & Apply Immediate Fixes

Reviews recent session transcripts through a framework-development lens, identifies problems, files GitHub issues for root-cause analysis, and applies immediate fixes. Delegates to the `survey` skill in `retro` mode.

## Workflow

Delegate the retro execution to the **Pauli** coordinator agent (not junior):
`Agent(subagent_type='pauli', prompt='Run survey skill in retro mode on session: <resolved-session-id-or-path> [optional directive context]')`

If no explicit path or session ID is provided, locate the current session ID or active transcript path for the current conversation and pass it.
