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
---

Answer directly and concisely with no preamble.
Do not call `finish` on plain-text requests; only call `finish` when a structured JSON schema requires returning a JSON object.
