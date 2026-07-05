---
name: learn
type: command
category: instruction
description: Thin shortcut — delegates to the triage skill in retro mode. Triages recent transcripts, classifies issues, files GitHub bug reports.
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

Reviews recent session transcripts through a framework-development lens, identifies problems, files GitHub issues for root-cause analysis, and applies immediate fixes. Delegates to the `triage` skill in `retro` mode.

## Privacy & Forensic Issue Rules

- **Privacy**: Anonymize all findings. No real names, emails, student details, or raw session dumps in GitHub issues.
- **RCA Rigor (The Issue Report)**: This is a routine division of labor — you file the forensic facts, a separate detached pass later decides whether a framework change is warranted. So the filed GitHub issue stays focused on forensic findings (incident facts, structural shape, and concrete impact). Don't bake speculative remediations into the issue report itself; keep it factual so it serves as high-quality evidence. (And don't over-fit: one salient incident isn't reason enough for a big framework change that doesn't generalise — that call belongs to the cross-incident pass.)
- **No Fixing Inhibition**: Keeping the _issue report_ forensic does NOT inhibit you from fixing the reviewed session's own mistakes immediately. It does NOT extend to changing the framework's future behavior — that's the issue's job to surface, never this pass's job to implement.

## Workflow

Delegate the retro execution to the **Pauli** coordinator agent:
`Agent(subagent_type='pauli', prompt='Run triage skill in retro mode on session: <resolved-session-id-or-path> [optional directive context]')`

If no explicit path or session ID is provided, locate the current session ID or active transcript path for the current conversation and pass it.
