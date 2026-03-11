---
name: eval
type: skill
category: analysis
description: Agent session quality assessment — merged into /qa as Agent Session Evaluation mode
triggers:
  - "evaluate session"
  - "evaluate response"
  - "assess quality"
  - "performance evaluation"
  - "how good was that"
  - "review agent work"
  - "assess agent performance"
modifies_files: true
needs_task: false
mode: execution
domain:
  - quality-assurance
allowed-tools: Bash,Read,Write,Glob,Grep,Agent
version: 3.0.0
tags:
  - v0.3
  - quality-assurance
  - evaluation
---

# /eval — Agent Session Evaluation

This skill is merged into `/qa`. Use the **Agent Session Evaluation** mode there.

See: [[../../skills/qa/SKILL.md]]

All evaluation logic, quality dimensions, and the session extraction script are documented in `/qa`.
The dimensions reference and extraction script remain at their current paths:

- Quality dimensions: [[references/dimensions.md]]
- Session extractor: `skills/eval/scripts/prepare_evaluation.py`
