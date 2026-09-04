---
description: On any failure, halt, surface it in full, and wait — no workarounds, fallbacks, or bypasses.
trigger: off
---

## Halt on Failure — no workarounds, no fallbacks, ever

When an instruction, tool, dependency, lock, or validation step fails — partially, silently, or ambiguously — halt, surface the failure in full, and wait for direction. Fail loudly rather than degrade quietly.

- Never **mask** a failure (defaults, silent fallbacks, swallowed exceptions, papering retry loops), **route around** it (`--no-verify`, `--force`, skip flags, a working-looking substitute), or **reassign** it ("environmental", "pre-existing", "out of scope").
- Never bypass a lock, held resource, or guarded gate without explicit user authorisation. Encountering one is a halt-and-ask, not an obstacle to clear.
- Every failure belongs to the agent that encountered it and is surfaced in the same turn it is observed, to the authority who can authorise a fix. There is no inbox of failures owed to someone else; we do not leave traps for future agents.

Adding a fallback so a step "works" when its intended tool, credential, or service fails — such as reaching directly into `$ACA_DATA` with filesystem tools or the `pkb` CLI when MCP tools are degraded — converts a loud failure into a silent one. Prohibited however convenient.
