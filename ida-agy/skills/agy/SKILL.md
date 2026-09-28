---
name: agy
description: Run tasks using the headless Antigravity (agy) CLI powered by Gemini models. Use to delegate high-volume or model-specific work to the agy runtime.
---

# Agy Wrapper

Invoke the headless `agy` CLI to execute tasks using Gemini models. If currently running inside an `agy` session, execute work directly using native tools.

## Normal invocation

Normal execution dispatches a task to `agy` by ID. Use `tmux` to run in a detached session, allowing the task to complete without you:

```bash
tmux new-session -d -s "$TMUX_NAME" agy --sandbox --mode accept-edits --output-format text --print-timeout 50m --add-dir <worktree> --agent james --print "/ida:pull <task_id>"
```

## Ad-hoc, short tasks that do not require repo access

For ad-hoc, one-off tasks with an immediate result, you can invoke `agy` directly from the command line.

- Do not use this direct invocation mode for any tasks that require r/w repo access or that may take longer than 5 minutes to complete.

```bash
agy --sandbox --mode accept-edits --output-format text --print-timeout 5m --agent james --print '<instructions>'
```

## Required arguments

- `--sandbox`: Run in a sandboxed environment. Mandatory.
- `--mode accept-edits` auto-approves native file-edit tool calls
  (`write_to_file`, `replace_file_content`) inside the granted directories. Never use `--dangerously-skip-permissions` to bypass our security model.
- `--print` must always be the last argument, and must be a single string.
- `--add-dir <worktree>`: always provide a worktree directory for `agy` to use if the task requires repo access.

## Options

- `--model <name>`: Specify model tier (defaults to `gemini-3.8-flash`; use `gemini-3.1-pro-high` for critical tasks).
- `--print-timeout <duration>`:
- `--output-format json`: Return JSON output if you need it. Default to plain text.
- `--output-format stream-json`: Return JSON output in real time (only if you're waiting for immediate results interactively).

## Execution and Status Rules

- **Run detached in background**: usually, you should dispatch in the background and avoid waiting for the result. The result will be returned to the PKB and will be reconciled by a separate process.
- If you dispatch directly, **do not poll**: you will receive a notification when the agent finishes. Check the output carefully for a description of what the agent did and whether it succeeded.
- **Skill expansion**: Prefix slash commands with their plugin namespace (e.g. `/ida:hydrate`).
- **Completion**: Do not buffer through stream filters (`grep`, `tail`).
