---
name: decide
description: Present discrete pending decisions drawn from today's daily note one at a time with recommendations, pointers, and reply options, and record each answer on the item. Use for "decide", "go through my decisions", morning triage, or when discrete open items in the daily note need interactive resolution. Exclude for design discussions, research methodology, task planning, or questions about decisions (use conversational discussion or list summary), routine status reports (use daily note), plain graph truth maintenance (use reconcile), or worker dispatch (use dispatch).
---

# /decide -- Walk Through Open Decisions

Present open decisions drawn strictly from today's daily note one at a time. The agent holds the list and presents each choice individually to prevent decision fatigue. Never dump or batch decisions as a list.

## 1. Read Decisions from Today's Daily Note

Read strictly the `## With you` section of today's daily note (PKB note `YYYYMMDD-daily`).

- **Cold operational choices only**: /decide presents only discrete operational decisions the user can make cold from what the card shows them (a clear choice, proportionate evidence, a reasoned recommendation, and structured reply options).
- **Research and review questions handled outside /decide**: A question that requires research, investigation, reading external materials, or a review before a choice can be made must never be cut into quick button choices or presented through /decide. Handle such questions conversationally with the full context, argument, and trade-offs in view, or route them to a research or review workflow so they reach the user with the information needed to decide.
- **Informational queries are not walk-throughs**: When invoked with a query or filter (e.g. `/decide what decisions are waiting on research?`), answer with a concise list of matching decisions and stop; do not launch the interactive card stepper unless explicitly asked to walk through them.
- Read strictly the `## With you` section. Do not harvest from `## Your work`, general backlog sections, or whole-graph task sweeps. Never slice complex plans, research designs, or multi-step tasks into decision cards.
- Each entry under `## With you` represents an item that has reached the user under the one-level escalation rule.
- If the section is empty or missing, report that no decisions are waiting and stop.

For each item in `## With you`, prepare a decision card satisfying the threefold decision standard:

1. **Enough Information (The Choice)**: Clear, self-contained statement of what is being decided, the trade-offs in play, and consequences, so the user can decide without manual log lookups.
2. **Proportionate Evidence (Facts and Pointers)**: Verifiable primary evidence scaled to the decision (such as posted review links, test/CI status receipts, task IDs, PR URLs, or document links).
3. **Reasoned Recommendation**: Concrete suggestion paired with functional rationale ("Recommend X because Y").
4. **Answer Options**: Structured, low-friction reply options (e.g. keywords like `approve` / `reject` / `snooze`, or interactive question choices, always including a "do nothing" or deferral option).

Order cards strictly by what unblocks most (downstream dependencies, critical path blockers, deadline urgency).

## 2. Present One Card at a Time

Hold the ordered list in memory and present exactly one card per turn.

- **Header**: `Decision N of M: <Short Title>`
- **Content**: Enough information to decide, proportionate evidence with pointers, the reasoned recommendation, and structured answer options.
- **Prompt**: Ask for a response (on conversational channels) or present via choice tool (`ask_question` in console) where supported.
- **Prohibition**: Never output multiple cards in one message or summarize the remaining queue in advance. Never force complex research reviews or open-ended design problems into multiple-choice cards.

## 3. Turn-by-Turn Record and Advance

On each answer from the user:

1. **Record on the item**: Immediately write the user's decision to the item's record (e.g. update the task markdown body with the timestamped decision, update frontmatter or release the task, or note the resolution).
2. **Advance or Converse**: If the user's answer is a clear decision on the card, advance to the next card (`Decision N+1 of M`). If the user asks a question, raises uncertainty, or shifts context, pause the card stepper immediately and address their substance conversationally. Never force the user into rapid-fire progression without allowing conversational pauses.
3. **Wrap-up**: After the final card (`Decision M of M`), provide a concise one-line receipt summarizing the recorded decisions and updated tasks.
