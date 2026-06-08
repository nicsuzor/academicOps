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

- `/learn` — Review the current session/transcript (auto-detect the current session context/ID and pass it).
- `/learn <path>` or `/learn <session-id>` — Review the specified transcript/session.
- `/learn that last task should have been xyz` — Dual action: fix the target behavior immediately AND file the tracking RCA issue in the background.

## Workflow

1. **Resolve Session Context**:
   - If a specific `<path>` or `<session-id>` is provided, use that.
   - If no explicit path or session ID is provided, locate the current session ID or the active transcript path for the current conversation.
   - **No Random Fallback**: You must NEVER dispatch Pauli without specifying the target session or transcript, and Pauli must never select a random transcript. If no session context, ID, or path can be resolved, halt and report an error.

2. **Dispatch Pauli**:
   - Delegate the retro execution to the **Pauli** coordinator agent (not junior):
     `Agent(subagent_type='pauli', prompt='Run survey skill in retro mode on session: <resolved-session-id-or-path> [optional directive context]')`
   - You MUST explicitly pass the target session ID or transcript path in the prompt to Pauli. Same-session review by a fresh subagent (like `pauli` dispatched within the session) is explicitly allowed.
