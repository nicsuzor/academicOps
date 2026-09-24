---
name: agy
description: Run tasks using the headless Antigravity (agy) CLI powered by Gemini models. Use to delegate high-volume or model-specific work to the agy runtime.
---

# Agy Wrapper

Invoke the headless `agy` CLI to execute tasks using Gemini models. If currently running inside an `agy` session, execute work directly using native tools.

- `agy` auto-denies file access outside its launch workspace.
- You can grant additional dirrectories by passing `--add-dir <dir>`.
- You may not seek to grant `agy` greater authority than you yourself possess.
- Never pass `--dangerously-skip-permissions`; it auto-approves every tool call, not just directory access.

## Invocation

```bash
agy --agent james --mode accept-edits --output-format json --print-timeout 30m --print '<instructions>'
```

- `--mode accept-edits` auto-approves native file-edit tool calls
  (`write_to_file`, `replace_file_content`) inside the granted directories.
  Reads there are auto-approved regardless of mode; without `accept-edits`,
  writes fall back to an interactive confirmation headless mode cannot answer.
- `--print` must always be the last argument, and must be a single string.

## Options

- `--model <name>`: Specify model tier (defaults to `gemini-3.8-flash`; use `gemini-3.1-pro-high` for critical tasks).
- `--print-timeout <duration>`: Increase timeout for long-running jobs (agy default is `5m`).

## Execution and Status Rules

- **Check status, not exit codes**: `agy` exits `0` even when returning errors. Check the JSON payload: treat any output where `status != "SUCCESS"`, `response` is empty, or `denied_actions` is non-empty as a failure. A denied action means a tool needed a permission this invocation did not grant.
- **Skill expansion**: Prefix slash commands with their plugin namespace (e.g. `/aops:hydrate`).
- **Completion**: Do not buffer through stream filters (`grep`, `tail`). Deliver returned responses directly to the caller.
