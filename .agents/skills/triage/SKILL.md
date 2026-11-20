---
name: triage
type: skill
category: instruction
description: Triage a corpus, classify, and dispatch outputs across three modes -- retro (transcript review to issues), trend (longitudinal performance analysis), and sweep (GitHub issue triage to tasks and closures). Owned by pauli; delegates execution to pauli to keep main context clean.
---

# /triage -- Triage a Corpus, Classify, Dispatch

| Mode | Corpus | Primary output |
| - | - | - |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh` |
| `trend` | Many sessions / audit files | Trend report + recommendations |
| `sweep` | Open GitHub issues | PKB tasks (leaf and composite parent tasks), closures |

Every mode dispatches to `pauli`: premise evaluation and graph mutation belong to the custodian.

- **Read [references/forensic-scope.md](references/forensic-scope.md) before starting any mode.** Its in-scope/out-of-scope split and anonymisation clause bind `retro`, `trend`, and `sweep` alike.
- **Read [references/mode-procedures.md](references/mode-procedures.md) for the active mode before executing**, to apply exact selection rules, classification tables, output templates, and landing steps.

## Mode Contracts

### `retro` (Single Session -> Fixes and Issues)

- Review only the target session/conversation ID or path passed in the prompt; verify `$AOPS_SESSIONS/transcripts` exists and the rendered transcript is complete (proceed on raw `.jsonl` only with explicit user confirmation). Never grade your own work in the same context.
- Apply `references/forensic-scope.md`: fix session mistakes inline and test with `uv run pytest`; route framework changes as forensic `Bug: <brief-slug>` issues (max 3/session, no proposed solutions), updating existing matching issues/PRs first.
- Score bad-premise approvals against the approving review surface via the step-0 premise test (_was this worth building at all, in this shape?_).
- Stamp review provenance in the daily note (`### Retro review stamp: session <SID> (<project>)`) and open a PR for fixes.

### `trend` (Many Sessions -> Systemic Trend Report)

- Sample 8-15 sessions spanning early and recent periods across projects, reading `user_prompts` and `has_user_context` from `$AOPS_SESSIONS/transcripts/YYYY-MM/*.json` sidecars first and falling back to `*.full.md` only for reasoning and tool calls.
- Synthesise TP/FP/FN accuracy, temporal trends, coverage, and cost-benefit to `$AOPS_SESSIONS/reviews/<component>-trend-<date>.md`.

### `sweep` (Open Issues -> Tasks and Closures, Max 20/Cycle)

- Classify open `academicOps` issues using the disposition table in `references/mode-procedures.md` and execute low blast-radius dispositions autonomously.
- Escalate only ambiguous classifications, hard blocks, or enforcement proposals (which require root-cause generalisation, enforcement-map grounding, proportionality analysis, and >=3 recurrence links before rules/mechanisms).
- Leave `priority`, `severity`, and `inbox` status untouched on created tasks; verify closed issues reached `state: closed`, hand off to `verify`, and exit after one cycle.
