---
name: hydration-gate-warn
title: Hydration Gate Advisory Message
category: template
description: |
  Advisory message shown when hydration gate is in warn mode.
  Alerts agent that hydrator should be invoked, but allows proceeding.
---

💧 Prompt not yet hydrated.

To ensure alignment with project workflows and axioms, it is recommended to invoke the **hydrator** skill:

- Gemini: `activate_skill(name='aops-core:hydrator')`
- Claude: `Skill(skill='aops-core:hydrator')`

You may proceed if the task is trivial, but hydration is recommended for any file-modifying work.
