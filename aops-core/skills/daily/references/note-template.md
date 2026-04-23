---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT)
---

# Daily Note Structure (SSoT)

This template defines the sections and their purpose. The agent composes each section using judgment about what matters most in context — the template is a structural guide, not a form to fill in.

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
- [ ] [academic-example1] Reply to [[External Contact]] — meeting slots this week

## Focus

```
P0 ░░░░░░░░░░ 3/85
P1 █░░░░░░░░░ 12/85 → [ns-abc] [[Project A]] (-3d), [ns-def] [[Project B]] (-16d)
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85
```

🚨 **DEADLINE TODAY**: [ns-xyz] [[Review Task]] - Due 23:59 AEDT (8 items)

- [ ] **SHOULD**: [ns-abc] [[Overdue Committee Task]] — 3 days overdue. [[Internal Committee]] needs your vote.
- [ ] **DEEP**: [ns-ghi] [[Research Writing Task]] — Advances research programme goals
- [ ] **ENJOY**: [ns-jkl] [[Invited Article]] — [[External Collaborator]] invitation on [[Topic Area]]
- [ ] **QUICK**: [ns-mno] [[Administrative Form]] — Simple form completion
- [ ] **UNBLOCK**: [ns-pqr] [[Methodology Task]] — Blocks Phase 2 report chain (7.5 weight downstream)

_Suggested sequence_: Committee vote is critical — deadline today. Then tackle overdue external reply. Deep work on research writing if afternoon opens up.

### My priorities

(User writes here. Never overwritten by the agent.)

## What Needs Attention

### [[Prospective Student]] — PhD Supervision Enquiry

[[Prospective Student]] ([[External University]]) is inquiring about PhD supervision. Research on [[Research Topic Area]] — fits within the research programme. CV attached.

- [ ] acknowledged

### [[External Contact]] — [[Partner Organisation]] Project

[[External Contact]] ([[Partner Organisation]]) coordinating meeting with [[Project Lead]] to discuss [[Meeting Topic]]. Connected via [[Existing Connection]] and [[Research Centre]]. **Needs reply with time slot.**

- **→ Task**: [academic-example1] Reply to [[External Contact]]
- [ ] acknowledged

### [[Academic Publisher]] — Editorial Board Invitation

Invited to join [[Journal Name]] editorial board. Application via online form.

- [ ] acknowledged

### Outstanding Workflows

**Ready to merge:**

- [ ] [#489](url) [[academicOps]] — Release 0.3.19 (+12/-3, 2 files) — _merge now_

**Needs review:**

- [#501](url) [[buttermilk]] — Add extraction pipeline — awaiting review (2d)

**Needs fixes:**

- [#495](url) [[academicOps]] — Fix crontab paths — merge conflicts

* 3 draft/autonomous PRs across 2 repos

_8 open PRs total — 1 ready to merge, 4 need attention_

## Today's Story

(Omit this section entirely when the work date has no sessions yet. Populated end-of-day.)

## Work Log

<details>
<summary>(collapsed — expand for merged PRs, sessions, and accomplishments)</summary>

### Merged PRs

No PRs merged today.

### Sessions

No sessions today.

</details>
````

## Design Notes

**Five sections, in order: Carryover → Focus → What Needs Attention → Today's Story → Work Log.** A returning user's first question is "what was I in the middle of?" (Carryover), so it leads. Focus follows — today's recommendations, informed by the carryover above. What Needs Attention surfaces email/FYI and actionable PRs. Today's Story and Work Log sit lower — both are empty in the morning and most useful end-of-day.

**Editor-friendly surfaces.** The note is designed to be kept open in a text editor (VS Code, Obsidian) throughout the day. Actionable items are rendered as markdown checkboxes (`- [ ]`) so the user can tick them off as they act: carryover items, Focus recommendations, Ready-to-merge PRs, and FYI "acknowledged" markers. User ticks are preserved across agent regenerations (see Section Ownership in SKILL.md).

**Work Log is collapsed by default.** Wrap the Work Log block in `<details><summary>Work Log</summary> … </details>`. VS Code and Obsidian both render this collapsed in preview; in raw-edit mode it's still readable. It exists for traceability, not the morning read.

**No empty placeholders.** If a section has no content, omit it or use a brief natural-language statement. Never leave empty tables, "n/a" metrics, or `<!-- user notes -->` HTML comments visible. Today's Story in particular is omitted entirely in the morning before any sessions have run — no empty heading.

**Carryover only when non-empty.** No section at all if nothing to carry over.

**Proportional detail.** FYI items involving real people (students, collaborators, funders) get full context. Routine notifications get a line. Internal framework PRs don't get the same visual treatment as research milestones.

**No duplication.** Open PRs live in `## What Needs Attention / Outstanding Workflows` only — Work Log does not carry a parallel Open PRs table. Merged PRs live in Work Log only.

**Actions linked to tasks.** Every actionable FYI item has a `→ Task` link with a task ID.
