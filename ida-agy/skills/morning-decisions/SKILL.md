---
name: morning-decisions
description: Walk the user through morning decisions (daily emails, review tasks, open asks) one card at a time with recommendations, pointers, and reply options. Use for morning triage, "go through my decisions", "check my inbox/emails", or when a batch of decisions needs interactive user resolution. Exclude for routine status reports (use gather), plain graph maintenance (use reconcile), or autonomous worker dispatch (use dispatch).
---

# Morning Decisions

Walk the user through pending morning decisions — daily emails, tasks awaiting review, and open asks — one decision card at a time. The agent holds the list and presents each choice individually to prevent decision fatigue. Never dump or batch decisions as a list.

## 1. Prepare Decision Cards

Harvest candidate decisions that genuinely require the user's judgment:

- **Daily email / inbox**: Unread messages requiring personal approval, response, or scheduling.
- **Task graph / open asks**: Tasks in `review` or `partial` status waiting on a decision only the user can make.
- **External reviews**: PR reviews or external requests blocking active work.

Filter out noise: Items that can be resolved autonomously or are purely informational do not become decision cards.

Every decision card must contain all four parts:

1. **The Choice**: Clear, atomic statement of what is being decided.
2. **The Facts with Pointers**: Verifiable facts bearing on the decision, citing exact identifiers (`email:<id>`, task ID, PR URL, `path:line`).
3. **Recommendation and Why**: Concrete suggestion paired with functional rationale ("Recommend X because Y").
4. **Answer Options**: Structured, low-friction reply options (e.g. one-word keywords like `approve` / `reject` / `snooze`, or interactive question options).

Order cards strictly by **what unblocks most** (downstream weight, critical path blockers, deadline urgency).

## 2. Present One Card at a Time

Hold the ordered list in memory and present exactly one card per turn.

- **Header**: `Decision N of M: <Short Title>`
- **Content**: The choice, the facts with pointers, the recommendation with its reason, and the answer options.
- **Prompt**: Ask for a one-word reply (on conversational channels) or present via choice tool (`AskUserQuestion` in console) where supported.
- **Prohibition**: Never output multiple cards in one message or summarize the remaining queue in advance.

## 3. Turn-by-Turn Hand-off and Advance

On each answer from the user:

1. **Hand off verbatim**: Pass the user's exact words and the decision card verbatim to the dispatcher or downstream execution tool (e.g., to record the decision, update/release the PKB task, send the email reply, or unblock workers).
2. **Advance**: Immediately output the next card (`Decision N+1 of M`) with no intermediate chatter.
3. **Wrap-up**: After the final card (`Decision M of M`), provide a concise one-line receipt summarizing the actions dispatched and accounting for any non-decision items reviewed.
