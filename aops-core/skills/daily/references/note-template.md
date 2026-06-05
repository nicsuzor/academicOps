---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT)
---

# Daily Note Structure (SSoT)

This template defines the sections and their purpose. The daily note is a hybrid: Carryover, Status, and What Needs Attention are **factual reports** (the agent lists, the user ranks); the Lede and Today's Log are **editorial synthesis** (the agent is a smart editor of past work). The user always owns forward prioritisation.

**Order is shape-first (AC-13 / AC-14 / AC-16):** Lede → Today's Log (recovery substrate) → Status → What Needs Attention → Carryover → Work Log. The synthesis leads; the "what was I just trying to do?" surface sits immediately under it; the dashboard and carryover follow to support, not block.

````markdown
---
title: "Daily Summary - YYYY-MM-DD"
type: daily
date: YYYY-MM-DD
daily_narrative: null
daily_story: []
narrative_generated: null
---

# Daily Summary - YYYY-MM-DD

The morning is the framework eating its own dogfood: yesterday's PR wave landed three fix-epics, today's first hour went to a stale-config bug that blocked polecat dispatch on WSL. You cut a prerelease to clear it; dispatch is reopening now. Nothing is on fire — one decision (the v2-obsoletes-v1 call) is waiting on you.

**Degraded sources:** Email — outlook MCP auth error, 0 items shown _(only when a source genuinely failed after a real attempt + retry; omit this line entirely when all sources loaded)_

## Today's Log

**Morning timeline.** Verbatim prompts in order, one outcome line each.

**11:50–11:51 (nicwin/WSL, brain)** — _"/supervisor aops-5430c4c1 — dispatch with local gemini polecats"_ → first attempt denied; retry ran, supervisor found the epic undecomposed and called pauli for preflight.

**12:14 (nicwin/WSL, brain)** — _"/pull aops-2b248ee4 and dispatch locally using gemini polecats"_ → dispatch failed at the config layer: `unknown gates keys: ['commit']`. Blocked all polecat dispatch on this host.

**What you were trying to do**: dispatch a chain of SEV2 framework tasks to local gemini polecats; a stale-yaml / code-drift bug from yesterday's PR wave ate ~75 minutes — caught it, cut a prerelease, dispatch path now reopened.

**Decisions in flight**: Pending decisions: 4 (ready + review assigned to you). Needs your call: [task-xyz] does the v2 work obsolete v1? (PR #501 linked).

(Omit `## Today's Log` entirely on an empty morning with no sessions. See [[instructions/morning-timeline]] / [[instructions/work-summary]].)

## 🚨 ESCALATED DEADLINES

> [!CAUTION]
>
> ### 🚨 CRITICAL DEADLINE: [task-dp27] [[ARC DP27 Assessor Reviews]]
>
> **Consequence if missed**: 7 full grant reviews (~1+ day of work) will be missed, causing a SEV3 consequence for relationship with ARC.
> **Due**: 2026-06-05 (today) | **Effort**: M (1.0 day) [IMMOVABLE]
>
> - [ ] **Action Required**: Complete the assessor reviews immediately.

- [ ] **[task-xyz]** [[Other Escalated Work]] — due 2026-06-08 (3d away) — **[⚠ SEV2 IMMOVABLE]** (Effort: S)

## Status

```
P0 ░░░░░░░░░░ 3/85
P1 █░░░░░░░░░ 12/85
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85
```

**Deadlines (≤ 7 days)**:

- [ns-xyz] [[Review Task]] — due 2026-04-24 (today)
- [ns-abc] [[Committee Vote]] — due 2026-04-27 (3d)
- [ns-def] [[Manuscript Review]] — due 2026-04-29 (5d)

**Calendar (today)**:

- 09:00 — [[Meeting Title]] — KG-Z9-607
- 12:00 — ~~[[Canceled Event]]~~ (canceled)
- 17:00 — [[Evening Event]]

### My priorities

(User-owned. The agent never writes here.)

## What Needs Attention

### [[Prospective Student]] — PhD Supervision Enquiry

[[Prospective Student]] ([[External University]]) inquired about PhD supervision. Research topic: [[Topic Area]]. CV attached.

- [ ] acknowledged

### [[External Contact]] — [[Partner Organisation]] Project

[[External Contact]] coordinating a meeting with [[Project Lead]] to discuss [[Meeting Topic]]. Asks for a time slot.

- **→ Task**: [academic-example1] Reply to [[External Contact]]
- [ ] acknowledged

### [[Academic Publisher]] — Editorial Board Invitation

Invited to join [[Journal Name]] editorial board. Application via online form.

- [ ] acknowledged

### Outstanding Workflows

**Ready to merge:**

- [ ] [#489](url) [[academicOps]] — Release 0.3.19

**Needs review:**

- [#501](url) [[buttermilk]] — Add extraction pipeline (open 2d)

**Needs fixes:**

- [#495](url) [[academicOps]] — Fix crontab paths — merge conflicts

* 3 draft/autonomous PRs across 2 repos

### PR Triage Dashboard

_(Note: Rendered only when total open PRs ≥ 10. Contains cluster decision cards. See [[instructions/pr-triage-dashboard]].)_

## Carryover (Human-Action Items)

_(Positioned here to support, not lead — the lede and Today's Log already answer "what was I doing?". Omit entirely when empty.)_

- [ ] [example-carryover-task] **[[Committee Task]]** — due tomorrow (orange) [DECIDE]
- [ ] [academic-example1] Reply to [[External Contact]] — 2 days overdue (red) [CONFIRM] Draft reply ready: `<summary>`. [ ] send?
- [ ] [fyi-item-1] Read the new proposal [FYI]

## Work Log

<details>
<summary>(collapsed — expand for merged PRs and completed tasks)</summary>

### Merged PRs

No PRs merged today.

### Completed Tasks

No tasks completed today.

</details>
````

## Design Notes

**Lede plus six sections, in order: Lede → Today's Log (recovery substrate) → Escalated Deadlines (hoisted conditional) → Status → What Needs Attention → Carryover → Work Log.** The note's headline job is US-5 recovery, so it is shape-first: the **lede** (2–3 line present-tense synthesis) leads because the returning user's first question is "what's the shape of right now?"; **Today's Log** sits immediately under it because "what was I just trying to do?" is the next question, and the Morning Timeline answers it verbatim (this is the recovery substrate, AC-14). **Escalated Deadlines** (if active) and **Status** (dashboard) follow; **What Needs Attention** (inbox/PRs) and **Carryover** follow as factual inventory; **Work Log** is provenance at the bottom. Earlier versions led with Carryover and buried the synthesis as a closing paragraph (AC-16 failure) — that is exactly the order this template now inverts.

**The lede is a compression, hoisted — never a closing paragraph.** It is the _same_ synthesis Today's Log produces, distilled to 2–3 lines and placed at the top (persist to `daily_narrative`). It must not restate the full timeline. When a source genuinely failed (after a real load attempt + retry), a one-line **Degraded sources** block sits directly under the lede — the degradation is visible _as degradation, up front_, never as full stale sections with footnotes (AC-15).

**Status is reportive, not prescriptive.** Priority bars, deadline list, calendar, and decision counts — no SHOULD/DEEP/ENJOY/QUICK/UNBLOCK categories, no suggested sequences, no "start here because..." rationales. The `### My priorities` subsection is a user-owned space; the agent creates the empty heading and never writes to it.

**Editor-friendly surfaces.** The note is designed to be kept open in a text editor throughout the day. Carryover items, inbox "acknowledged" markers, and Ready-to-merge PRs are rendered as checkboxes (`- [ ]`) so the user can tick them off. User ticks are preserved across regenerations.

**Work Log is collapsed by default.** Wrap the Work Log block in `<details><summary>…</summary> … </details>`.

**No empty placeholders.** If a section has no content, omit it or use a brief natural-language statement ("No sessions today"). Today's Log is omitted entirely in the morning before any sessions have run — no empty heading.

**Carryover only when non-empty.** No section at all if nothing to carry over.

**Proportional detail.** Inbox items involving real people get full context; routine notifications get a line. Today's Log treats a five-hour autonomous run that closed a framework bug as a paragraph and nine single-prompt dispatches as a clause. Do not inject forward urgency ("this is the most important thing to do today") — forward prioritisation belongs to `### My priorities` and the user.

**Editorial synthesis on history; no ranking of what's next.** Today's Log is narrative prose — a smart editor's account of what happened, with named patterns, proportional detail, and honest silences. Status and the inbox are factual — they list what exists without weighting it. These are compatible: editorial judgment about past work is welcome; editorial judgment about future work is the user's.

**No duplication.** Open PRs live in `## What Needs Attention / Outstanding Workflows` only. Merged PRs live in Work Log only. Session narration lives in Today's Log only — the Work Log does not carry a session table.

**Actions linked to tasks.** Every actionable inbox item has a `→ Task` link with a task ID.
