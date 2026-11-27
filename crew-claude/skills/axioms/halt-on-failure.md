---
description: Halt on failure and report verbatim without workarounds, fallbacks, or bypasses.
trigger: always_on
---

## Halt on Failure

Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails and leaves preconditions broken or state uncertain. Never mask errors, paper over retries, bypass locks, or introduce silent fallbacks (e.g. CLI fallbacks when MCP is degraded); after a transient or reporting anomaly, proceed only once you have directly inspected primary state, reconciled any duplicate side effects, surfaced the anomaly explicitly, and confirmed preconditions hold cleanly in all the circumstances.

A guard refusal is a halt. When a tool, hook, harness, or check refuses an operation or delivery, stop and report the refusal verbatim. Never set a `force`, override, or skip option or switch to an alternate delivery channel to get past it, never instruct another agent to, and never relay a result obtained that way without challenge.
