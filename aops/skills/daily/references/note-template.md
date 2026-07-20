---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT). Section order is load-bearing; rationale lives in specs/workflows/daily.
---

# Daily Note Structure (SSoT)

Order is fixed: **Lede → Project Rollup → My priorities → (Escalated Deadlines, if any) → What Needs Attention → Carryover → Today's Log → Status → Prompt Ledger → Work Log.** Omit any empty section. Fill the skeleton below.

```markdown
---
title: "Daily Summary - YYYY-MM-DD"
type: daily
date: YYYY-MM-DD
daily_narrative: null
daily_story: []
---

# Daily Summary - YYYY-MM-DD

<!-- Lede: 2–3 present-tense lines — the shape of right now. The distilled version of Today's Log; persist to the daily_narrative frontmatter field, but do not duplicate it in the body if the frontmatter is populated. -->

A stale-config bug ate the morning before polecat dispatch came back online; you cut a prerelease to clear it. Nothing on fire — one decision (v2-obsoletes-v1) is waiting on you.

<!-- Degraded sources: one line, ONLY when a source genuinely failed after a real attempt. Omit otherwise. -->

## Project Rollup

<!-- One line per active project showing queued/blocked/needs-Nic state. -->

- **academicOps**: Q: 3 | B: 0 | Needs Nic: 1 (PR review)
- **brain**: Q: 1 | B: 2 | Needs Nic: 0
- **buttermilk**: Q: 0 | B: 0 | Needs Nic: 0
- **mem**: Q: 0 | B: 0 | Needs Nic: 0
- **sessions**: Q: 5 | B: 1 | Needs Nic: 2 (transcript audit)
- **overwhelm**: Q: 10 | B: 3 | Needs Nic: 1

### My priorities

<!-- User-owned. Create this heading empty; never write here. Preserve anything the user adds. Omission is blocked by template guard. -->

## 🚨 ESCALATED DEADLINES

<!-- Conditional: only when a deadline meets the escalation rule (see SKILL.md). Consequence text VERBATIM. Hoisted tasks are dropped from the Status deadline list below. -->

> [!CAUTION]
>
> ### 🚨 CRITICAL DEADLINE: [task-id] [[Title]]
>
> **Consequence if missed**: <verbatim consequence prose>
> **Due**: YYYY-MM-DD (today) | **Effort**: M [IMMOVABLE]

## What Needs Attention

<!-- Inbox (from /email): FYI items with verbatim quotes + a "[ ] acknowledged" line. Mobile captures routed via /q or /remember (one line each). "Needs your call": ambiguous task completions, plus stale-claim/ready-queue items flagged by the reconcile sweep (task ID + one-line reason) — never auto-closed or auto-cancelled. -->

### Needs your call

- [task-id] [[Title]] — ambiguous completion / stale claim reason

### Inbox & Mobile Captures

- **→ Task**: [task-id] Reply to [[Contact]]
- [ ] acknowledged

## Carryover

<!-- Uncompleted tasks from yesterday, VERIFIED against live PKB (drop missing/done/ticked). Omit entirely if empty. -->

- [ ] [task-id] [[Title]] — 2d overdue

## Today's Log

<!-- What happened so far today. SOURCE (mandatory): reconstruct this from today's PRIMARY sources — the session transcripts at `$AOPS_SESSIONS/transcripts/$(date +%Y-%m)/$(date +%Y%m%d)-*-claude-*.md` (prefer `-abridged.md`). You MUST open them before writing this section. Do NOT synthesise it from artifacts already in the note or from the reconcile sweep's merged-PR list. While the day is in flight: verbatim user prompts in time order, one outcome line each, then a "what you were trying to do" line. At day's end: an editorial synthesis. Describe the past factually; never rank future work. Omit this whole section on an empty morning. -->

**11:50 (nicwin/WSL, brain)** — _"/pull aops-2b248ee4 and dispatch locally"_ → failed at the config layer: `unknown gates keys: ['commit']`; blocked all dispatch on this host.

**What you were trying to do**: dispatch a chain of SEV2 framework tasks; a stale-yaml bug ate ~75 min — caught it, cut a prerelease, dispatch reopened.

## Status

<!-- Curated focus. Top 3 highest focus tasks and one-line count delta since last run. Raw counts must be collapsed. -->

**Top Focus Tasks:**

1. [task-id] [[Title]] — due YYYY-MM-DD (3d)
2. [task-id] [[Title]] — due YYYY-MM-DD (5d)
3. [task-id] [[Title]] — due YYYY-MM-DD (6d)

**Daily Movement:** +2 ready, -1 blocked, 0 closed since yesterday

**Calendar (today):**

- 09:00 — [[Meeting]] — (location)

<details>
<summary>(collapsed — raw status logging & PR status)</summary>

Ready by priority: P0 0 · P1 3 · P2 107 · P3 265

**Deadlines (≤ 7 days):**

- [task-id] [[Title]] — due YYYY-MM-DD (3d)

**Outstanding Workflows:**

- [ ] [#489](url) [[repo]] — title

</details>

## Prompt Ledger

<!-- Tail the most recent ~10 lines from `$AOPS_SESSIONS/state/prompt_ledger.md`. Reverse-date-sorted, one line per genuine Nic-typed prompt; outcome/link are blank when not resolvable from the session summary. Omit this whole section if the ledger file doesn't exist. -->

- [2026-07-09 12:40] [claude-code-cli] [f355deff] [short summary of the question] [short summary of the outcome, or blank] [link to task/PR/PKB note, or blank]

## Work Log

<!-- Provenance only, collapsed. Merged PRs + completed tasks. No session narrative. -->

<details>
<summary>(collapsed — merged PRs and completed tasks)</summary>

No PRs merged today. No tasks completed today.

Stale-claim reconcile: 0 closed, 0 released, 0 flagged. Ready-queue reconcile: 0 flagged.

</details>
```
