---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT). Section order is load-bearing; rationale lives in specs/workflows/daily.
---

# Daily Note Structure (SSoT)

Order is fixed: **Lede → Today's Log → (Escalated Deadlines, if any) → Status → What Needs Attention → Carryover → Work Log.** Omit any empty section. Fill the skeleton below.

```markdown
---
title: "Daily Summary - YYYY-MM-DD"
type: daily
date: YYYY-MM-DD
daily_narrative: null
daily_story: []
---

# Daily Summary - YYYY-MM-DD

<!-- Lede: 2–3 present-tense lines — the shape of right now. The distilled version of Today's Log; also persist to the daily_narrative frontmatter field. -->

A stale-config bug ate the morning before polecat dispatch came back online; you cut a prerelease to clear it. Nothing on fire — one decision (v2-obsoletes-v1) is waiting on you.

<!-- Degraded sources: one line, ONLY when a source genuinely failed after a real attempt. Omit otherwise. -->

## Today's Log

<!-- What happened so far today. While the day is in flight: verbatim user prompts in time order, one outcome line each, then a "what you were trying to do" line. At day's end: an editorial synthesis (proportional detail, named patterns, honest about dropped threads). Describe the past factually; never rank future work. Omit this whole section on an empty morning. -->

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

<!-- Factual snapshot. No recommendations, no curated categories, no suggested sequences. Counts come from mcp__pkb__task_summary, never hand-counted. -->

Ready by priority: P0 0 · P1 3 · P2 107 · P3 265

**Deadlines (≤ 7 days):**

- [task-id] [[Title]] — due YYYY-MM-DD (3d)

**Calendar (today):**

- 09:00 — [[Meeting]] — (location)

### My priorities

<!-- User-owned. Create this heading empty; never write here. Preserve anything the user adds. -->

## What Needs Attention

<!-- Inbox (from /email): self-contained FYI items with verbatim quotes + a "[ ] acknowledged" line. Mobile captures routed via /q or /remember (one line each). Outstanding Workflows: PR buckets from pr-state.json; ready-to-merge PRs as "- [ ]" checkboxes. "Needs your call": ambiguous task completions, never auto-closed. -->

### [[Contact]] — Subject

> verbatim quote of the key content

- **→ Task**: [task-id] Reply to [[Contact]]
- [ ] acknowledged

### Outstanding Workflows

**Ready to merge:**

- [ ] [#489](url) [[repo]] — title

## Carryover

<!-- Uncompleted tasks from yesterday, VERIFIED against live PKB (drop missing/done/ticked). Omit entirely if empty. -->

- [ ] [task-id] [[Title]] — 2d overdue

## Work Log

<!-- Provenance only, collapsed. Merged PRs + completed tasks. No session narrative (that lives in Today's Log). No open-PR table (that lives in Outstanding Workflows). -->

<details>
<summary>(collapsed — merged PRs and completed tasks)</summary>

No PRs merged today. No tasks completed today.

</details>
```
