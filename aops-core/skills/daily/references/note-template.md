---
name: daily-note-template
category: reference
description: Daily note structure template (SSoT)
---

# Daily Note Structure (SSoT)

This template defines the sections and their purpose. The agent composes each section using judgment about what matters most in context — the template is a structural guide, not a form to fill in.

````markdown
# Daily Summary - YYYY-MM-DD

## Focus

```
P0 ░░░░░░░░░░ 3/85
P1 █░░░░░░░░░ 12/85 → [ns-abc] [[Project A]] (-3d), [ns-def] [[Project B]] (-16d)
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85
```

🚨 **DEADLINE TODAY**: [ns-xyz] [[Review Task]] - Due 23:59 AEDT (8 items)

**SHOULD**: [ns-abc] [[Overdue Committee Task]] - 3 days overdue. [[Internal Committee]] needs your vote.
**DEEP**: [ns-ghi] [[Research Writing Task]] - Advances research programme goals
**ENJOY**: [ns-jkl] [[Invited Article]] - [[External Collaborator]] invitation on [[Topic Area]]
**QUICK**: [ns-mno] [[Administrative Form]] - Simple form completion
**UNBLOCK**: [ns-pqr] [[Methodology Task]] - Blocks Phase 2 report chain (7.5 weight downstream)

_Suggested sequence_: Committee vote is critical — deadline today. Then tackle overdue external reply. Deep work on research writing if afternoon opens up.

### My priorities

(User writes here. Never overwritten by the agent.)

## What Needs Attention

### [[Prospective Student]] — PhD Supervision Enquiry

[[Prospective Student]] ([[External University]]) is inquiring about PhD supervision. Research on [[Research Topic Area]] — fits within the research programme. CV attached.

### [[External Contact]] — [[Partner Organisation]] Project

[[External Contact]] ([[Partner Organisation]]) coordinating meeting with [[Project Lead]] to discuss [[Meeting Topic]]. Connected via [[Existing Connection]] and [[Research Centre]]. **Needs reply with time slot.**

- **→ Task**: [academic-example1] Reply to [[External Contact]]

### [[Academic Publisher]] — Editorial Board Invitation

Invited to join [[Journal Name]] editorial board. Application via online form.

## Today's Story

[[Day of week]]. [[Key deadline task]] deadline is tomorrow — critical. Two supervision enquiries arrived overnight. [[Project Collaborator]] needs exact data column for project evaluation. No sessions or merged PRs yet.

## Work Log

### Merged PRs

No PRs merged today.

### Sessions

No sessions today.

## Carryover

- [example-carryover-task] **[[Committee Task]]** — deadline tomorrow
- [academic-example1] Reply to [[External Contact]] — meeting slots this week
````

## Design Notes

**Five sections, not twelve.** Focus, What Needs Attention, Today's Story, Work Log, Carryover/Abandoned. The v2 template had separate Task Tree, Session Log, Today's Path, Project Accomplishments, Mobile Captures, Open PRs, Terminal Overwhelm Analysis, and Reflection sections — these either merge into the Work Log or are folded into the sections they serve.

**No empty placeholders.** If a section has no content, omit it or use a brief natural-language statement. Never leave empty tables, "n/a" metrics, or `<!-- user notes -->` HTML comments visible. The note should read as a composed document, not a filled-in form.

**Proportional detail.** FYI items involving real people (students, collaborators, funders) get full context — who said what, what's being asked, what the deadline is. Routine notifications get a line. Internal framework PRs don't get the same visual treatment as research milestones.

**Work Log is reference, not the main event.** Merged PRs, session tables, and accomplishment checklists are collapsed into one section at the bottom. They exist for traceability and end-of-day reflection, not for the morning read.

**Carryover only when non-empty.** No section at all if nothing to carry over.

**Actions linked to tasks.** Every actionable FYI item has a `→ Task` link with a task ID.
