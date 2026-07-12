---
id: decision-briefing
kind: process
category: general
description: Generate a structured, user-facing briefing for tasks blocked on a human decision — consequence analysis, not recommendations
requires: [task-tracking]
pairs-with: [human-approval]
conflicts: []
version: 1.0.0
permalink: workflows-process-decision-briefing
---

# Process: Decision Briefing

**When**: user needs to review and decide on tasks blocking progress (RFCs,
blocked tasks, experiments, design decisions).

**Key principle**: surface issues with complete context so the user decides
quickly. Agents do not make subjective recommendations — they provide
structured consequence analysis for each option (this template produces
briefings, not verdicts).

## Steps

1. **Gather tasks needing decision** — search for RFCs, blocked tasks,
   investigations, design decisions. If none, exit.
2. **Categorize and deduplicate** — priority: RFC > Blocked > Investigation >
   Design Decision > Experiment.
3. **Generate the briefing** — context, options, a consequence matrix (not
   subjective recommendations), and dependent tasks.
4. **Present to user** — structured briefing, batch-collect decisions.
5. **Execute decisions** — parse the response and act (approve, reject, defer,
   prioritize) one at a time with verification.

## Acceptance Criteria

Include ALL matching active tasks; enough context to decide without reading
the full issue; a consequence matrix, not a recommendation; dependent issues
shown per decision; actionable (user can respond "approve X, defer Y").

## Constraints

Do one thing: generate the briefing and capture decisions. Do NOT implement
approved changes in the same pass, and do NOT make subjective recommendations.
When a decision authorises an irreversible action, hand off to
[[human-approval]] rather than treating the briefing reply itself as that
authorisation.
