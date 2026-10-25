---
alias:
  - wf-surface-probe
description: Surface integrity probe -- verify plugin discovery, hook execution, service reachability, subagent tool binding, and negative boundary containment across runtime surfaces.
id: wf-surface-probe
tags:
  - wf-template
  - testing
  - surface-probe
  - environment
title: wf-surface-probe
type: template
---

## What this step does

Verify environmental integrity and baseline tool and plugin bindings on a target surface before executing substantive work. Probes discovery, lifecycle hooks, backend services, subagent delegation, and negative security boundaries.

Judgment is non-delegable: the evaluating agent inspects primary evidence and issues verdicts; exit codes alone do not substitute for qualitative observation.

**Quiescence rule.** Never evaluate a loading, transition, or spinner state. Wait until the final response has rendered and a clean prompt is visible before recording a verdict.

## Input contract

- **Target surface** -- installation channel, client runtime, or execution container under test.
- **Expected plugin set** -- list of required plugins and explicitly excluded plugins for this surface.

## Probe sequence

Execute these five checks in order on the target surface. Each check requires its own verifiable receipt (command output, transcript excerpt, or pinpoint file:line citation):

1. **Plugin presence.** Inspect the surface's plugin listing or install tree. Confirm all intended plugins are present and any prohibited or surface-incompatible plugins are absent.
2. **Lifecycle hooks.** Trigger a clean session start and submit an initial prompt. Verify startup announcements and prompt hydration hooks trigger cleanly, injecting expected context into the prompt buffer.
3. **Service reachability.** Submit a probe query testing that core backend services (such as the Personal Knowledge Base) respond and return results. Verify reachability and response validity.
4. **Subagent binding.** Delegate a service or tool query to a subagent. Verify the subagent successfully inherits tool access and executes the call without namespace or allowlist rejections.
5. **Negative boundary.** Submit a call targeting an unauthorized tool, invalid scope, or mismatched namespace. Confirm the invocation fails closed with an access error rather than executing.

## Output contract

A surface verification matrix recording:
- Target surface identifier
- Five probe verdicts (PASS, FAIL, or INCONCLUSIVE) with pinpoint receipts
- Any discovered configuration, namespace, or environment discrepancies filed as one task per root cause
