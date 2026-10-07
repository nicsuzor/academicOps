---
title: Prompt Hydration
type: spec
status: proposed
tier: core
depends_on: []
tags: [framework, routing, context]
---

# Prompt Hydration

`aops:hydrate` (`plugins/aops/skills/hydrate/SKILL.md`) searches the PKB for
ambiguous words in a prompt might mean and returns a shortlist of ids.

## When it runs

Every `UserPromptSubmit` (agy: the first `PreInvocation` of a turn) that carries
text from Nic: a console prompt or a Telegram message. This closes the control gap
where freeform prompts get baseline context only, unlike prompts that arrive
through a skill or a claimed task.

Messages from agents (`<cross-session-message>`, `<teammate-message>`,
`<task-notification>`, or any other `<...-message>` / `<...-notification>`
wrapper) are not searched. They get the hearsay reminder and arm the
premise-check gate instead (`specs/enforcement/report-verification.md`). A
prompt that batches both gets both: Nic's part is searched, and the agent part
is gated. The rules live in `plugins/ida/hooks/prompt_origin.py`.
