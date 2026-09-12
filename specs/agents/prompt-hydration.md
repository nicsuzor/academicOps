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

Every `UserPromptSubmit`. This closes the control gap where freeform prompts get
baseline context only, unlike prompts that arrive through a skill or a claimed
task.
