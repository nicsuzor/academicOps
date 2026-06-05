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

# /learn — Analyze Session Transcripts (retro mode)

Reviews recent session transcripts through a framework-development lens, identifies problems, and files GitHub issues. Delegates to the `survey` skill in `retro` mode.

## Privacy & Recusal Rules

- **Privacy**: Anonymize all findings. No real names, emails, student details, or raw session dumps in GitHub issues.
- **Recusal**: Focus strictly on forensic findings (causal chain and framework layer fields). You are recused from proposing how to fix the issue or suggesting new axioms/gates in the report.

## Invocation & Arguments

- `/learn` — auto-select the most recent unreviewed markdown transcript.
- `/learn <path>` — review the specified markdown transcript path.
- `/learn <session-id>` — review the session matching the ID.

## Workflow

Delegate the retro execution to the Junior coordinator agent:
`Agent(subagent_type='junior', prompt='Run survey skill in retro mode with [transcript context]')`
