---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT). Section order is load-bearing; rationale lives in specs/workflows/daily.
---

# Daily Note Structure (SSoT)

Order is fixed: **Lede → Today's Log → (Escalated Deadlines, if any) → Status → What Needs Attention → Carryover → Prompt Ledger → Work Log.** Omit any empty section. Fill the skeleton below.

```markdown
---
title: "Daily Summary - YYYY-MM-DD"
type: daily
date: YYYY-MM-DD
daily_narrative: "2-3 present-tense lines — the shape of right now. The distilled version of Today's Log. Populated ONLY in this frontmatter field; do not repeat in the body."
daily_story: []
---

# Daily Summary - YYYY-MM-DD

<!-- Lede: The present-tense summary is stored only in the frontmatter daily_narrative field. The body must NOT repeat this text. -->

<!-- Degraded sources: one line, ONLY when a source genuinely failed after a real attempt. Omit otherwise. -->

## Today's Log

<!-- What happened so far today. SOURCE (mandatory): reconstruct this from today's PRIMARY sources — the session transcripts at `$AOPS_SESSIONS/transcripts/$(date +%Y-%m)/$(date +%Y%m%d)-*-claude-*.md` (prefer `-abridged.md`). You MUST open them before writing this section. Do NOT synthesise it from artifacts already in the note (prior retro stamps, yesterday's log) or from the reconcile sweep's merged-PR list — those are second-hand and reproduce the file, not the day. While the day is in flight: verbatim user prompts in time order, one outcome line each, then a "what you were trying to do" line. At day's end: an editorial synthesis (proportional detail, named patterns, honest about dropped threads). Describe the past factually; never rank future work. Omit this whole section on an empty morning (no same-day interactive session transcripts). -->

**11:50 (nicwin/WSL, brain)** — _"/pull aops-2b248ee4 and dispatch locally"_ → failed at the config layer: `unknown gates keys: ['commit']`; blocked all dispatch on this host.

**What you were trying to do**: dispatch a chain of SEV2 framework tasks; a stale-yaml bug ate ~75 min — caught it, cut a prerelease, dispatch reopened.

## 🚨 ESCALATED DEADLINES

<!-- Conditional: only when a deadline meets the escalation rule (see SKILL.md). Consequence text VERBATIM. Hoisted tasks are dropped from the Status deadline list below. -->

> [!CAUTION]
>
> ### 🚨 CRITICAL DEADLINE: [task-id] [[Title]]
>
> **Consequence if missed**: <verbatim consequence prose>
> **Due**: YYYY-MM-DD (today) | **Effort**: M [IMMOVABLE]

## Status

<!-- Prioritised snapshot. Curated top-3 ready tasks by focus score and one-line deltas replace raw aggregate counts. Raw counts are collapsed below the fold. Per-project rollup is included. -->

**Top 3 Ready Tasks:**
- [task-id] [[Title]] (Focus: score, Project: slug, Priority: N)
- [task-id] [[Title]] (Focus: score, Project: slug, Priority: N)
- [task-id] [[Title]] (Focus: score, Project: slug, Priority: N)

**Task Count Deltas:**
- Net change since yesterday: +N ready, -M blocked (Total: X ready, Y blocked)

**Project Rollup:**
- **academicOps**: Q: 0 | B: 0 | N: 0
- **brain**: Q: 0 | B: 0 | N: 0
- **buttermilk**: Q: 0 | B: 0 | N: 0
- **mem**: Q: 0 | B: 0 | N: 0
- **sessions**: Q: 0 | B: 0 | N: 0
- **overwhelm**: Q: 0 | B: 0 | N: 0

<details>
<summary>Raw Task Counts (collapsed)</summary>

Ready by priority: P0 A · P1 B · P2 C · P3 D
Ready: X | Blocked: Y
</details>

**Deadlines (≤ 7 days):**

- [task-id] [[Title]] — due YYYY-MM-DD (3d)

**Calendar (today):**

- 09:00 — [[Meeting]] — (location)

### My priorities

<!-- STRUCTURAL GUARD (User-owned): Create this heading empty; never write here. Preserve anything the user adds. Omission of this heading is prohibited. -->

## What Needs Attention

<!-- Needs your call and time-sensitive items FIRST. Inbox, mobile captures, ambiguous completions, and stale-claim/ready-queue items. PR/workflow status collapsed inside details below. -->

### Needs your call / Time-sensitive
- [ ] **[task-id]** Title / Action needed — Reason/details

### [[Contact]] — Subject

> verbatim quote of the key content

- **→ Task**: [task-id] Reply to [[Contact]]
- [ ] acknowledged

<details>
<summary>Outstanding Workflows (collapsed)</summary>

**Ready to merge:**
- [ ] [#489](url) [[repo]] — title
</details>

## Carryover

<!-- Uncompleted tasks from yesterday, VERIFIED against live PKB (drop missing/done/ticked). Omit entirely if empty. -->

- [ ] [task-id] [[Title]] — 2d overdue

## Prompt Ledger

<!-- Tail the most recent ~10 lines from `$AOPS_SESSIONS/state/prompt_ledger.md`. Regenerate first if missing or stale (older than today): `uv run python aops/scripts/transcript.py --ledger --since <7-days-ago>` from the academicOps checkout. Reverse-date-sorted, one line per genuine Nic-typed prompt; outcome/link are blank when not resolvable from the session summary — never fill them in by hand or infer them from the transcript yourself. Omit this whole section if the ledger file doesn't exist and can't be generated. -->

- [2026-07-09 12:40] [claude-code-cli] [f355deff] [short summary of the question] [short summary of the outcome, or blank] [link to task/PR/PKB note, or blank]

## Work Log

<!-- Provenance only, collapsed. Merged PRs + completed tasks. No session narrative (that lives in Today's Log). No open-PR table (that lives in Outstanding Workflows). -->

<details>
<summary>(collapsed — merged PRs and completed tasks)</summary>

No PRs merged today. No tasks completed today.

Stale-claim reconcile: 0 closed, 0 released, 0 flagged. Ready-queue reconcile: 0 flagged.

</details>
```
