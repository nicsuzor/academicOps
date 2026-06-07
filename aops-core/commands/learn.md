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

## Privacy & Forensic Issue Rules

- **Privacy**: Anonymize all findings. No real names, emails, student details, or raw session dumps in GitHub issues.
- **RCA Rigor (The Issue Report)**: The filed GitHub issue must focus strictly on forensic findings (incident facts, structural shape, and concrete impact). Do NOT suggest or guess speculative remediations inside the issue report itself. Keep the issue report strictly factual so it serves as high-quality training/evidence data.
- **No Fixing Inhibition**: The recusal on _proposing speculative solutions in the issue report_ does NOT prohibit or restrict the agent from fixing the live codebase immediately. You are expected to fix the live problem whenever permitted or instructed.

## Immediate Fixes Policy (Fix AND File)

You may apply immediate codebase fixes (for minor tweaks or framework-caused defects) AND you must still file the tracking GitHub issue. Invocations like `/learn that last task should have been xyz` trigger a dual action: fix the immediate problem now, and file the RCA issue in the background. Refer to the canonical retro mode protocol in [skills/survey/SKILL.md](skills/survey/SKILL.md#mode-retro) for details.

## Invocation Styles

- `/learn` — Auto-select the most recent unreviewed markdown transcript.
- `/learn <path>` or `/learn <session-id>` — Review the specified transcript/session.
- `/learn that last task should have been xyz` — Dual action: fix the target behavior immediately AND file the tracking RCA issue in the background.

## Workflow

Delegate the retro execution to the Junior coordinator agent:
`Agent(subagent_type='junior', prompt='Run survey skill in retro mode with [transcript context] [optional directive context]')`
