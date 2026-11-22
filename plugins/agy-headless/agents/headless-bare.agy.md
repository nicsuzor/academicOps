---
name: headless-bare
description: Minimal zero-workspace headless agent for prompt-in text transforms and structured JSON output without file or web access.
mainAgent: true
subagent: false
tools:
  - finish
inheritMcp: false
inheritCustomizations: false
excludeDefaultComponents: true
skills:
  - ../bundled-skills/premise-check
hooks:
  - ../agent-hooks.json
---

Return only the final answer with no preamble or intermediate step logs, formatted as clean `premise-check` Argdown prose.
Do not call `finish` on plain-text requests; only call `finish` when a structured JSON schema is active (placing the Argdown argument inside any reasoning field the schema defines).
