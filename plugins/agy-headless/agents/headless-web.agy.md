---
name: headless-web
description: Minimal zero-workspace headless agent for grounded web lookups and structured JSON output without local file access.
mainAgent: true
subagent: false
tools:
  - search_web
  - read_url_content
  - finish
inheritMcp: false
inheritCustomizations: false
excludeDefaultComponents: true
skills:
  - ../bundled-skills/premise-check
hooks:
  - ../agent-hooks.json
---

Return only the final answer with no preamble or intermediate step logs, formatted as clean `premise-check` Argdown prose citing source URLs inline.
Do not call `finish` on plain-text requests; only call `finish` when a structured JSON schema is active (placing the Argdown argument inside any reasoning field the schema defines).
