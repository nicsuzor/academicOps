---
name: agy
description: Invoke local headless synchronous agy from Claude Code for faster reading, local and web searches, and lower cost. Used by James and his subagents like any other subagent. Exclude for isolated background polecats (route to sara) or when already running inside agy.
---

# agy -- Local Headless Synchronous Subagent

When `james` or his subagents run inside Claude Code, invoke local headless `agy` synchronously to read files faster, run local and Google-grounded web searches faster, and reduce token cost.

## Treat It Like Any Other Subagent

Give `agy` the same outcome-oriented brief you would give any subagent, and do not micromanage it:

- State the goal, relevant file paths or URLs, and the exact output format you want back (for example, cited observations or clean Argdown prose per `ida:premise-check`).
- Leave tool choice, reading order, search queries, and intermediate steps to `agy`. Do not over-constrain its working directory, flags, or permissions beyond what safety requires.
- Run `agy` locally in-session only; work requiring an isolated container goes to `sara` as a fire-and-forget polecat.

## Model Selection & Invocation

Default to the `fast` tier model; escalate to `mid-tier` or `flagship` only when task complexity requires it.

```bash
agy --model <model> --output-format text --print-timeout 5m --print '<brief>'
```

- Run in the foreground with a shell timeout exceeding `--print-timeout` so `agy` controls its own deadline.
- Pass `--print` last as a single quoted string containing the full brief.

## Verification & Fail-Fast

Treat returned output as another agent's handback: verify claims on the face of the record against inline citations (`path:line`, command outputs, URLs) per `ida:premise-check`. On non-zero exit, timeout, or error output, halt and report verbatim without silent fallbacks.
