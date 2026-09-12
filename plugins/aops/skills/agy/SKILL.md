---
name: agy
description: Run tasks using the headless Antigravity (agy) CLI powered by Gemini models. Use to delegate high-volume or model-specific work to the agy runtime.
---

# Agy Wrapper

Invoke the headless `agy` CLI to execute tasks using Gemini models. If currently running inside an `agy` session, execute work directly using native tools.

## Directory grant

`agy` auto-denies file access outside its launch workspace once running
headless. Resolve exactly the directories this task legitimately needs —
never a literal list — and grant each with its own `--add-dir`:

```bash
mapfile -t AGY_DIRS < <(polecat add-dirs)
printf 'agy directory grant on this machine:\n'
printf '  %s\n' "${AGY_DIRS[@]}"
ADD_DIR_FLAGS=()
for d in "${AGY_DIRS[@]}"; do ADD_DIR_FLAGS+=(--add-dir "$d"); done
```

`polecat add-dirs` reads the registered project slugs from
`$AOPS_SESSIONS/polecat.yaml` and resolves each to this machine's own checkout
path via `<polecat_home>/local.yaml`, then adds `$AOPS_SESSIONS` itself. A
project with no checkout on this machine is silently skipped. Printing the
resolved list before invoking `agy` is what lets a reader see the actual scope
for this run, on this machine, without hard-coding it here.

Grant nothing else under `$HOME`. Never pass `--dangerously-skip-permissions`
— it auto-approves every tool call, not just directory access.

## Invocation

```bash
agy --agent james --mode accept-edits "${ADD_DIR_FLAGS[@]}" --prompt '<instructions>'
```

- `--mode accept-edits` auto-approves native file-edit tool calls
  (`write_to_file`, `replace_file_content`) inside the granted directories.
  Reads there are auto-approved regardless of mode; without `accept-edits`,
  writes fall back to an interactive confirmation headless mode cannot answer.
- The delegated agent must edit through its own native file tools, never
  through a shell command. A shell-based edit (`run_command` piping into a
  file, `sed -i`, and the like) needs the `command` permission, which headless
  mode cannot grant, and fails with: `a tool required the "command" permission
  that headless mode cannot prompt for`. Native edits fall under the
  write-file permission `--mode accept-edits` already covers, so no
  `command(...)` allow-rule is needed.
- An edit attempted outside a granted directory still denies: only reads are
  auto-approved outside the directories listed above.

## Options

- `--model <name>`: Specify model tier (defaults to `gemini-3.8-flash`; use `gemini-3.1-pro-high` for complex tasks).
- `--print-timeout <duration>`: Increase timeout for long-running jobs (default is `5m`, e.g. `--print-timeout 25m`).
- `--agent <agent>`: Target agent persona: `james` (default), `pauli`, `rbg`, or `marsha`.

## Execution and Status Rules

- **Check status, not exit codes**: `agy` exits `0` even when returning errors. Check the JSON payload: treat any output where `status != "SUCCESS"`, `response` is empty, or `denied_actions` is non-empty as a failure — a denied action means a tool needed a permission this invocation did not grant.
- **Skill expansion**: Prefix slash commands with their plugin namespace (e.g. `/aops:hydrate`) for print mode expansion.
- **Completion**: Do not buffer through stream filters (`grep`, `tail`). Deliver returned responses directly to the caller.
