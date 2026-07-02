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

## Immediate Fixes Policy (Fix AND File)

You may fix the reviewed session's own mistakes immediately (a wrong file it wrote, a broken reference it left, a task it mis-filed, a mechanical bug it hit) AND you must still file the tracking GitHub issue. This never extends to editing the framework's rules, gates, hooks, or agent instructions to change future behavior — that's a framework change, always out of scope here, regardless of how minor or well-scoped to the one incident it looks. Invocations like `/learn that last task should have been xyz` trigger a dual action: fix the reviewed session's mistake now, and file the RCA issue in the background. Refer to the canonical retro mode protocol in [skills/triage/SKILL.md](skills/triage/SKILL.md#mode-retro) for the exact scope boundary.

## Invocation Styles

- `/learn` — Review the current session/transcript (auto-detect the current session context/ID and pass it).
- `/learn <path>` or `/learn <session-id>` — Review the specified transcript/session.
- `/learn that last task should have been xyz` — Dual action: fix the reviewed session's own mistake immediately AND file the tracking RCA issue in the background.

## Workflow

1. **Resolve Session Context**:
   - If a specific `<path>` or `<session-id>` is provided, use that.
   - If no explicit path or session ID is provided, locate the current session ID or the active transcript path for the current conversation.
   - **No Random Fallback**: You must NEVER dispatch Pauli without specifying the target session or transcript, and Pauli must never select a random transcript. If no session context, ID, or path can be resolved, halt and report an error.

2. **Dispatch Pauli**:
   - Delegate the retro execution to the **Pauli** coordinator agent:
     `Agent(subagent_type='pauli', prompt='Run triage skill in retro mode on session: <resolved-session-id-or-path> [optional directive context]')`
   - You MUST explicitly pass the target session ID or transcript path in the prompt to Pauli. Same-session review by a fresh subagent (like `pauli` dispatched within the session) is explicitly allowed.
