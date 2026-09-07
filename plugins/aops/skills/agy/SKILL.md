---
name: agy
description: Run tasks using the headless Antigravity (agy) CLI powered by Gemini models. Use to delegate high-volume or model-specific work to the agy runtime.
---

# Agy Wrapper

Invoke the headless `agy` CLI to execute tasks using Gemini models. If currently running inside an `agy` session, execute work directly using native tools.

## Invocation

```bash
agy --agent james --prompt '<instructions>'
```

## Options

- `--model <name>`: Specify model tier (defaults to `gemini-3.8-flash`; use `gemini-3.1-pro-high` for complex tasks).
- `--print-timeout <duration>`: Increase timeout for long-running jobs (default is `5m`, e.g. `--print-timeout 25m`).
- `--agent <agent>`: Target agent persona: `james` (default), `pauli`, `rbg`, or `marsha`.

## Execution and Status Rules

- **Check status, not exit codes**: `agy` exits `0` even when returning errors. Check the JSON payload: treat any output where `status != "SUCCESS"` or `response` is empty as a failure.
- **Skill expansion**: Prefix slash commands with their plugin namespace (e.g. `/aops:hydrate`) for print mode expansion.
- **Completion**: Do not buffer through stream filters (`grep`, `tail`). Deliver returned responses directly to the caller.
