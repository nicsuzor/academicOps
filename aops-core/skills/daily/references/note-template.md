---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT)
---

# Daily Note Structure (SSoT)

This template defines the sections and their purpose. The daily note is a hybrid: Carryover, Status, and What Needs Attention are **factual reports** (the agent lists, the user ranks); Today's Log is an **editorial synthesis** (the agent is a smart editor of past work). The user always owns forward prioritisation.

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

## Carryover

- [ ] [example-carryover-task] **[[Committee Task]]** — deadline tomorrow
- [ ] [academic-example1] Reply to [[External Contact]] — response pending

## Status

```
P0 ░░░░░░░░░░ 3/85
P1 █░░░░░░░░░ 12/85
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85
```

Pending decisions: 4 (ready + review assigned to you)

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

## Today's Log

(Omit this section entirely when the work date has no sessions yet. When populated, this is an editorial synthesis — narrative prose, not a table of sessions. See [[instructions/work-summary]] Step 5.3.)

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

**Five sections, in order: Carryover → Status → What Needs Attention → Today's Log → Work Log.** Carryover leads because a returning user's first question is "what was I in the middle of?" Status is a factual snapshot; What Needs Attention surfaces inbox/PRs. Today's Log and Work Log sit lower — both are empty in the morning and most useful end-of-day.

**Status is reportive, not prescriptive.** Priority bars, deadline list, calendar, and decision counts — no SHOULD/DEEP/ENJOY/QUICK/UNBLOCK categories, no suggested sequences, no "start here because..." rationales. The `### My priorities` subsection is a user-owned space; the agent creates the empty heading and never writes to it.

**Editor-friendly surfaces.** The note is designed to be kept open in a text editor throughout the day. Carryover items, inbox "acknowledged" markers, and Ready-to-merge PRs are rendered as checkboxes (`- [ ]`) so the user can tick them off. User ticks are preserved across regenerations.

**Work Log is collapsed by default.** Wrap the Work Log block in `<details><summary>…</summary> … </details>`.

**No empty placeholders.** If a section has no content, omit it or use a brief natural-language statement ("No sessions today"). Today's Log is omitted entirely in the morning before any sessions have run — no empty heading.

**Carryover only when non-empty.** No section at all if nothing to carry over.

**Proportional detail.** Inbox items involving real people get full context; routine notifications get a line. Today's Log treats a five-hour autonomous run that closed a framework bug as a paragraph and nine single-prompt dispatches as a clause. Do not inject forward urgency ("this is the most important thing to do today") — forward prioritisation belongs to `### My priorities` and the user.

**Editorial synthesis on history; no ranking of what's next.** Today's Log is narrative prose — a smart editor's account of what happened, with named patterns, proportional detail, and honest silences. Status and the inbox are factual — they list what exists without weighting it. These are compatible: editorial judgment about past work is welcome; editorial judgment about future work is the user's.

**No duplication.** Open PRs live in `## What Needs Attention / Outstanding Workflows` only. Merged PRs live in Work Log only. Session narration lives in Today's Log only — the Work Log does not carry a session table.

**Actions linked to tasks.** Every actionable inbox item has a `→ Task` link with a task ID.
