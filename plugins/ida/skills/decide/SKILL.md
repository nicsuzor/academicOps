---
name: decide
description: Present discrete pending decisions drawn from today's daily note one at a time with recommendations, pointers, and reply options, and record each answer on the item. Use for "decide", "go through my decisions", morning triage, or when discrete open items in the daily note need interactive resolution. Exclude for design discussions, research methodology, task planning, or questions about decisions (use conversational discussion or list summary), routine status reports (use daily note), plain graph truth maintenance (use reconcile), or worker dispatch (use dispatch).
---

# /decide -- Walk Through Open Decisions

Present open decisions drawn strictly from today's daily note one at a time to prevent decision fatigue. Never dump or batch decisions as a list.

## 1. Read and Filter Decisions

Read strictly the `## With you` section of today's daily note (PKB note `YYYYMMDD-daily`); never harvest from `## Your work`, backlogs, or whole-graph sweeps. If `## With you` is empty or missing, report that no decisions are waiting and stop.

- **Cold operational choices only**: Present only discrete operational decisions the user can make cold from the card. Research, investigation, reading external materials, reviews, complex plans, or multi-step tasks must never be sliced into quick choices -- handle them conversationally with full context and trade-offs or route to a research/review workflow.
- **Informational queries**: When invoked with a query or filter (e.g. `/decide what decisions are waiting on research?`), answer with a concise list and stop without starting the card stepper.

Order eligible cards by what unblocks most (downstream dependencies, critical path blockers, deadline urgency), preparing each with:

1. **Enough Information**: Self-contained statement of the choice, trade-offs, and consequences without manual log lookups.
2. **Proportionate Evidence**: Primary pointers scaled to the decision (review links, CI/test receipts, task IDs, PR URLs, or document links).
3. **Reasoned Recommendation**: Concrete suggestion with functional rationale ("Recommend X because Y").
4. **Answer Options**: Low-friction reply options (e.g. `approve` / `reject` / `snooze`, always including deferral).

## 2. Present One Card at a Time

Hold the ordered list in memory and present exactly one card per turn:

- **Header**: `Decision N of M: <Short Title>`
- **Body**: Choice, proportionate evidence with pointers, reasoned recommendation, and structured answer options.
- **Prompt**: Ask for a reply on conversational channels or via an interactive choice prompt where supported.
- **Prohibition**: Never output multiple cards in one turn, preview remaining cards in advance, or force open-ended problems into multiple-choice options.

## 3. Record and Advance

On each reply:

1. **Record immediately**: Write the timestamped decision to the item's record (update task markdown body, frontmatter, or release status).
2. **Advance or converse**: On a clear decision, advance to `Decision N+1 of M`. When the user defers a complex decision ("decide later"), have `pauli` `/decompose` it one step (one option per node). If the user asks a question or raises uncertainty, pause the stepper immediately and converse naturally.
3. **Wrap-up**: After `Decision M of M`, emit a one-line receipt summarizing recorded decisions and updated tasks.
