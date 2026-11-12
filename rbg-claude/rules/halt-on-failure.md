---
description: Halt on failure and report verbatim without workarounds, fallbacks, or bypasses.
trigger: always_on
---

## Halt on Failure

Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails. Never mask errors, paper over retries, bypass locks, or introduce silent fallbacks (e.g. CLI fallbacks when MCP is degraded).

A guard refusal is a halt. When a tool, hook, or check refuses an operation, stop and report the refusal verbatim. Never set a `force`, override, or skip option to get past it, never instruct another agent to, and never relay a result obtained that way without challenge.
