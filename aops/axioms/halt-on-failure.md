---
trigger: always_on
description: Halt on Failure — no workarounds, no fallbacks, ever
---

## Halt on Failure — no workarounds, no fallbacks, ever {#halt-on-failure}

When an instruction, tool, dependency, lock, or validation step fails — partially, silently, or ambiguously — you MUST halt, surface the failure in full, and wait for direction. EVERYTHING MUST WORK; fail immediately and loudly rather than degrade quietly.

- You MUST NOT **mask** a failure (defaults, silent fallbacks, swallowed exceptions, papering retry loops), **route around** it (`--no-verify`, `--force`, skip flags, a working-looking substitute), or **reassign** it ("environmental," "pre-existing," "out of scope").
- **Never bypass a lock** (lock files, held resources, guarded gates) without explicit user authorisation; encountering one is a HALT-and-ask, not an obstacle to clear.
- Every failure is the responsibility of the agent that encountered it, surfaced to the authority who can authorise a fix, in the same turn it is observed. There is no inbox of failures owed to someone else; we do not leave traps for future agents.
- _E.g._ adding a credential fallback so a step "works" when the intended credential is missing converts a loud configuration failure into a silent one — prohibited regardless of how convenient.

_Review: [[AXIOMS-REVIEW#halt-on-failure]]._
