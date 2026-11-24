---
name: agy
description: Run a low-context headless Antigravity (agy) agent from Claude Code for quick text transforms, grounded web searches, read-only repo inspection, or schema-validated JSON output under 5 minutes. Returns answer-only premise-check Argdown handbacks by default. Exclude for repository writes or work over 5 minutes (use /dispatch), or when already inside an agy session.
---

# /agy -- Low-Context Headless Antigravity Invocation

Invoke `agy` headlessly from Claude Code via the single isolated profile `--agent headless-bare` (`inheritCustomizations: false`, `inheritMcp: false`, `preloadSkills: [premise-check]`, zero hooks, read-only tools `view_file`, `search_web`, `run_command`, `finish` -- no write tools). Isolation strips ambient MCP schemas, workspace rules, other plugins, and repo-cwd hooks without needing `cd /tmp`. The prompt defines the task and scope. By default, `agy` returns **only the final answer** as clean `premise-check` Argdown prose. If already inside an `agy` session, use native tools directly; route repository writes or work over 5 minutes (10-minute ceiling) to `/dispatch`.

## 1. Startup Flags & Invocation

Always pass `--agent headless-bare`, `--sandbox`, and `--disable-slash-commands`:

- `--sandbox`: Mandatory. Never pass `--dangerously-skip-permissions` or `--mode accept-edits` on local runs.
- `--disable-slash-commands`: Mandatory. Strips slash-command routing and stops leading `/` paths or diffs from misfiring as CLI directives. Do not combine with `--mode plan`.
- `--model <model>`: Pin an explicit model from `agy models` -- start at `fast` tier and escalate to `mid-tier` or `flagship` when task complexity requires it.
- `--effort <level>`: Optional (`low`, `medium`, `high`, `xhigh`, `max`) only for models supporting adjustable effort; when `agy models` lists effort-suffixed entries, select that entry via `--model` without adding `--effort`.
- `--print-timeout <duration>`: Bound every call (baseline `5m`, hard ceiling `10m`) and set the caller's shell timeout slightly higher.
- `-p` / `--print`: Place last as one quoted string (embed piped content into `-p`; `agy -p` does not read stdin). Pass `--add-dir <abs_path>` only when reading outside cwd.
- **Unprivileged containers (`CapEff: 0`)**: `run_command` fails with `operation not permitted` without flipping `.status` or `.denied_actions`; name explicit file paths for `view_file` or embed diffs/matches in `-p`.

```bash
# Answer-only Argdown handback (state goal, scope, and evidence needed -- not step-by-step commands)
agy --sandbox --agent headless-bare --model "<fast-model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "Search the web: <question>. Cite source URLs inline."
```

## 2. JSON Schema Validation & Output Checks

`--json-schema` requires `--output-format json` and a JSON Schema whose root declares `"type": "object"` (bare `"string"`/`"array"` schemas or missing files exit `1`). Include an `argdown` or `reasoning` string property when you want the `premise-check` handback inside structured JSON.

```bash
SCHEMA="$(jq -ce 'if type == "object" and .type == "object" then . else error("root_not_object") end' schema.json)"
agy --sandbox --agent headless-bare --model "<fast-model>" \
  --disable-slash-commands --print-timeout 5m \
  --output-format json --json-schema "$SCHEMA" -p "<prompt>"
```

- **JSON envelope**: Verify exit code `0`, `.status == "SUCCESS"`, `.finished_reason == null`, and empty `.denied_actions`. Read `.structured_output` (with `--json-schema`, fail if null/absent) or `.response` otherwise.
- **Plain text**: When JSON metadata/schema is unneeded, `--output-format text` writes the final answer directly to stdout (verify exit code `0`).
- **Sequential follow-ups**: Save `.conversation_id` from JSON output and pass `--conversation <id>` within the cache TTL to reuse the warm prefix cache (`-c` is `--continue` with no ID argument and errors if given one).

## 3. Verify & Fail Fast

- Check the returned `premise-check` Argdown handback on the face of the record per `ida:premise-check` (ask coverage, inline evidence, warrants, defeaters -- zero _de novo_ fact-checking) before relying on or relaying it.
- Any non-zero exit, timeout, `.status != "SUCCESS"`, non-null `.finished_reason`, non-empty `.denied_actions`, missing `.structured_output`, or `operation not permitted` tool error in `.response` is a failure -- report verbatim without silent fallback or weakened flags.
