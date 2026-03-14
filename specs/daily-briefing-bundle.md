---
title: Daily Briefing Bundle
type: spec
status: draft
tier: workflow
depends_on: []
tags: [skill, daily, workflow, briefing]
version: 0.2.0
---

# Daily Briefing Bundle

A morning-only document containing everything requiring Nic's judgment today: decisions with coversheets, pre-drafted emails, calendar context, and FYIs. Generated on demand, reviewed linearly, annotated in place, processed back into the system.

## Two Documents, Two Jobs

The **daily note** (`/daily` skill) is a living progress tracker. It runs throughout the day: email triage, task recommendations, session logs, PR tracking, work summaries. It answers "what's going on?" and accumulates state.

The **briefing bundle** (this spec) is a morning snapshot. It reads the daily note, adds editorial judgment, and produces a self-contained brief that answers "what do I need to decide?" It is consumed in a single sitting and discarded after processing.

|                | Daily Note                                        | Briefing Bundle                                              |
| -------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| **Lifecycle**  | Created once, updated all day                     | Generated fresh each morning, annotated, processed, archived |
| **Job**        | Track progress, sync sessions, triage email       | Present decisions, draft emails, enable action               |
| **Tone**       | Dashboard — here's what's happening               | Brief — here's what you need to do                           |
| **Content**    | Task tree, session logs, PR status, FYI summaries | Coversheets, email drafts, calendar prep, annotation targets |
| **Updated by** | Agent (repeatedly)                                | Agent (once) → Nic (annotations) → Agent (processing)        |
| **Persists**   | Yes — SSoT for the day                            | No — actions flow back to PKB and Outlook                    |

**The bundle is a downstream consumer.** It reads the daily note and synthesis.json rather than re-querying data sources. New queries are only for what the daily note doesn't provide: full task context for coversheets, email content for drafts, and calendar details.

**What the daily note should NOT try to do** (that's the bundle's job): write coversheets, draft emails, make recommendations with annotation targets, or produce self-contained decision items. The daily note surfaces priorities; the bundle makes them actionable.

## User Expectations

Nic can expect the following behavior from the Briefing Bundle workflow:

1. **Linear, High-Signal Review**: A single document generated each morning containing 5-15 items requiring judgment. Every decision item MUST have a clear, justified recommendation ("Accept because...", not "It depends").
2. **No Silent Execution**: Generating a bundle (`/bundle`) is a non-destructive, draft-only action. No tasks are updated and no emails are sent until the bundle is annotated and processed.
3. **Annotation-Driven Agency**: The system only acts on Nic's explicit intent. Annotations like `<!-- @nic: approved -->` or `<!-- @nic: send -->` are the only triggers for state changes in the PKB or Outlook.
4. **Ephemeral Lifecycle**: The bundle is a "scratchpad" for the morning brief. Once `/process-bundle` runs, the "truth" of those decisions is persisted in the Task Graph or email drafts, and the bundle file itself can be safely archived or deleted.
5. **ADHD-Friendly Flow**: Top-to-bottom reading with no need to jump between apps or files. Every decision includes the minimum context needed to act, with supporting details tucked into collapsed sections.

## Design Philosophy

Board papers work because a skilled secretary pre-digests the material, orders it by importance, writes a coversheet that tells the reader exactly what is needed from them, and limits the supporting material to what is necessary for the decision at hand.

**The key constraint is attention, not information.** The bundle surfaces 5-15 items needing human judgment, presents them with enough context to act, and makes acting as frictionless as annotating a document.

**Guiding metaphor**: Chief of Staff preparing the morning brief for a principal with ADHD. Be decisive about what matters. Put the hardest thing first while energy is highest. Never present a menu when you can present a recommendation.

**ADHD-specific design constraints**:

- Every item is self-contained — no "see email for details" without the excerpt inline
- Full email drafts, not talking points — composition friction ≈ starting from scratch
- Linear top-to-bottom flow — no jumping between sections
- Checkboxes on every item — visible progress, clear finish line
- Energy-ordered — decisions first (hardest), FYIs last (easiest)

---

## Core Requirements

### 1. Executive Summary

Max 10 lines at the top. Contains: item counts by type, the single most urgent item (bold), today's calendar shape (free blocks vs packed), and a recommended work sequence (numbered, 1-3 sentences). Includes an annotation quick-reference legend.

### 2. Decision Coversheets

Every decision item uses this template:

```markdown
### [Title] -- [[project]]

**Decision needed**: [One line: what exactly to decide]
**Recommended action**: **[Accept/Decline/Approve/Defer]** -- [one sentence justification]
**Deadline**: [date, with "X days overdue" if applicable]
**Stakes**: [What happens if deferred another week]

**Key context**:

- [Most important fact]
- [Second most important fact]
- [Relevant constraint or consideration]

**Task**: [[task-id]]

- [ ] Resolved

<!-- @nic: approved / decline / defer to DATE / other -->

<details><summary>Supporting detail</summary>

[Extended context, email excerpts, related tasks -- only if needed]

</details>

<details><summary>Draft email (recommended action)</summary>

To: recipient@example.com
Subject: Re: [Original subject]
In-Reply-To: [entry_id]

Hi [Name],

[Draft text per STYLE.md email conventions]

Best,
Nic

</details>
```

Rules:

- The recommendation is explicit and justified in one sentence. Never "it depends."
- Max 5 bullet points of context above the fold. If more is needed, it goes in the details section.
- For accept/decline decisions, pre-draft both options. Recommended option is the visible details section; alternative is a second collapsed section.
- Context is pulled from the task file, related emails, and calendar. Only decision-relevant excerpts.

### 3. Email Drafts

For every item requiring an email response, include a complete draft written in Nic's voice (per STYLE.md). Drafts include `To:`, `Subject:`, `In-Reply-To:` (Outlook entry_id for threading). Each draft has an annotation target: `<!-- @nic: send / send as edited / redraft - [feedback] -->`. Approved drafts are staged as Outlook drafts (never auto-sent).

### 4. Calendar Section

Today's meetings plus tomorrow preview. Each meeting includes: time, title, attendees (with brief context on who they are if not obvious), prep notes, and pre-reads if applicable. Highlights free blocks for deep work.

### 5. FYI Items

One-line headline, 2-3 sentence summary, source attribution. Grouped by project. Each has `<!-- @nic: noted -->` annotation target. Items that might generate a task include a suggested task title Nic can approve via annotation. Max 5 lines per FYI above the fold.

### 6. Carryover

Items carried from previous days, grouped by age (oldest first). Each has a checkbox. Items appearing 3+ consecutive days get a flag: "⚠️ Carried 3 days — decide: act, defer, or cancel?"

### 7. Annotation Round-Trip

The bundle uses `<!-- @nic: -->` / `<!-- @claude: -->` annotation conventions. Processing is invoked via `/process-bundle` or detected at session start.

| Annotation                           | System Action                                                        |
| ------------------------------------ | -------------------------------------------------------------------- |
| `<!-- @nic: approved -->`            | Execute recommended action, update task                              |
| `<!-- @nic: send -->`                | Create Outlook draft via `messages_reply` or `messages_create_draft` |
| `<!-- @nic: send as edited -->`      | Create draft with edited text                                        |
| `<!-- @nic: decline -->`             | Execute opposite action                                              |
| `<!-- @nic: defer to YYYY-MM-DD -->` | Update task due date, remove from bundle                             |
| `<!-- @nic: noted -->`               | Mark as seen, no further action                                      |
| `<!-- @nic: task: [title] -->`       | Create PKB task                                                      |
| `<!-- @nic: [freeform] -->`          | Agent interprets and executes                                        |

Processing produces a receipt table appended to the bundle: `| # | Item | Annotation | Action Taken | Status |`.

---

## Bundle Structure

Ordering is deliberate: energy-intensive first, passive last.

```
YAML frontmatter (type: bundle, date, item_counts)

## Executive Summary (max 10 lines)

## Decisions (N items)
  ### [Decision title] -- [project]
    [Coversheet with annotation target]

## Calendar (today + tomorrow preview)
  ### HH:MM -- [Meeting title]
    [Prep notes, attendees, pre-reads]

## Emails (N items)
  ### Reply: [Subject] -- to [Recipient]
    [Draft with annotation target]

## FYI (N items)
  ### [Project] -- [Headline]
    [Summary with annotation target]

## Carryover (N items)
  [Items by age, checkboxes]

## Done
  (Empty -- visible finish line)
```

---

## Workflow

### Generate (agent)

1. **Read daily note** — extract Focus items, FYI summaries, carryover, task tree
2. **Read synthesis.json** if available — structured task data
3. **Load yesterday's bundle** — carry forward unprocessed annotations
4. **Enrich** — for each decision item: `get_task(id)` for full context, `messages_get(entry_id)` for email threading, `calendar_list_upcoming(days=2)` for calendar
5. **Classify** items into sections (Decision/Calendar/Email/FYI/Carryover)
6. **Order** within sections: deadline today > overdue > calendar-driven > high-priority > email > FYI
7. **Draft** coversheets, email replies, FYI summaries
8. **Write** Executive Summary
9. **Self-review** — verify task IDs resolve, check density limits, trim if >15 items, ensure every item has checkbox and annotation target
10. **Export** to `daily/YYYYMMDD-bundle.md`

### Review (Nic)

Open in Obsidian. Work top to bottom. Annotate decisions, approve/edit email drafts, note FYIs. Save.

### Process (agent)

Scan for `<!-- @nic: -->` annotations without matching `<!-- @claude: -->` responses. Execute each action. Append processing receipt. Commit.

---

## Decisions Made

- **Trigger**: On-demand (`/bundle`), not scheduled. Automate once format stabilises.
- **Bundle is ephemeral**: Actions persist in PKB and Outlook. Old bundles are archival.
- **No duplication**: Items in both daily note and bundle are cross-referenced, not repeated in full.
- **Drafts only**: Email drafts are staged in Outlook, never auto-sent.
- **Morning only**: No end-of-day variant. The daily note handles day-end synthesis.
- **OSB items**: Include from PKB tasks with a note that email context is unavailable (secure device).

## Future Work (not in MVP)

- PDF export with bookmarks (Baskervville body, section bookmarks, A4)
- Document appendices for review items (converted DOCX/PDF inline)
- Bundle metrics tracking (items per bundle, draft acceptance rate, carryover rate)
- Template adjustment proposals based on usage patterns
- Tablet/iPad annotation extraction (Apple Pencil → markdown)
- Session-start hook to auto-detect annotated bundles

---

## Data Sources

| Source         | Tool                                                    | Purpose                         |
| -------------- | ------------------------------------------------------- | ------------------------------- |
| Daily note     | Read file                                               | Focus items, FYIs, carryover    |
| synthesis.json | Read file                                               | Structured task data            |
| Task details   | `get_task(id)`                                          | Full context for coversheets    |
| Calendar       | `calendar_list_today`, `calendar_list_upcoming(days=2)` | Meeting schedule + tomorrow     |
| Email content  | `messages_get(entry_id)`                                | Threading info for drafts       |
| Email search   | `messages_search`                                       | Find related emails for context |
| Draft creation | `messages_reply`, `messages_create_draft`               | Approved draft staging          |
| Annotations    | `/annotations` skill                                    | Process `@nic:` comments        |

## Giving Effect

This spec is implemented via a pair of skills that coordinate between the daily note, the briefing bundle document, and the external data sources (PKB and Outlook).

- **Implementation**: [[aops-core/skills/briefing-bundle/SKILL.md]]
- **Implementation**: [[aops-core/skills/process-bundle/SKILL.md]]
- **Upstream**: [[aops-core/skills/daily/SKILL.md]] — daily note that the bundle reads
- **Upstream**: [[aops-core/skills/annotations/SKILL.md]] — annotation processing convention
