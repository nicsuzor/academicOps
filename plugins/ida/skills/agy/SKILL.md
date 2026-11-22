---
name: agy
description: Run a low-context headless Antigravity (agy) agent from Claude Code for quick text transforms, grounded web searches, named-file reads, flexible mid-tier exploration/reasoning, or schema-validated JSON output under 5 minutes. Returns answer-only premise-check Argdown handbacks by default. Exclude for repository writes or work over 5 minutes (use /dispatch), or when already inside an agy session.
---

# /agy -- Low-Context Headless Antigravity Invocation

Invoke `agy` headlessly from Claude Code using isolated custom agent profiles (`inheritCustomizations: false`, `inheritMcp: false`) that preload only `premise-check` (`preloadSkills: [premise-check]`) with zero hooks, stripping MCP schemas, workspace rules, other plugins, and slash-command tables. By default (`--output-format json` reading `.response` or `.structured_output`, or `--output-format text`), `agy` returns **only the final answer** -- never intermediate tool logs or thinking prose -- formatted as clean `premise-check` Argdown prose. If already inside an `agy` session, use native tools directly. Route repository writes or work over 5 minutes (10-minute ceiling) to `/dispatch`.

## 1. Choose a Low-Context Agent Profile

Always pass `--agent <profile>` so `agy` never boots a full default session:

| Profile | Capabilities | Default tier & working directory |
| :- | :- | :- |
| `headless-bare` | Zero file or web tools (`finish` only) | `fast`; clean dir outside repos (e.g. `/tmp`) |
| `headless-web` | Grounded web search (`search_web`, `read_url_content`, `finish`) | `fast`; clean dir outside repos (e.g. `/tmp`) |
| `headless-ro` | Read-only named local files (`view_file`, `grep_search`, `find_by_name`, `list_dir`, `finish`) | `fast`; target dir (`--add-dir <abs_path>` if needed) |
| `headless-explore` | Read-only exploration & multi-step reasoning (read-only `run_command`, file reads, web search, `finish`; zero write tools) | `mid-tier`; target dir (`--add-dir <abs_path>` if needed) |

For `headless-ro`, name explicit file paths in the prompt; when paths are unknown or cross-file reasoning is required, use `headless-explore` (or gather diffs/matches in the caller and pass them to `headless-bare`).

## 2. Startup Options, Mid-Tier Reasoning & Exploration

Apply these startup flags on every local headless call:

- `--sandbox`: Mandatory. Never pass `--dangerously-skip-permissions` or `--mode accept-edits` on local runs.
- `--disable-slash-commands`: Mandatory. Strips slash-command routing and stops leading `/` paths or diffs from misfiring as CLI directives. Do not combine with `--mode plan` (ignored while slash commands are disabled).
- `--model <model>`: Pin an explicit model from `agy models` matching the required capability tier (`fast`, `mid-tier`, or `flagship`) and desired reasoning effort.
- `--effort <level>`: Optional reasoning-effort override (`low`, `medium`, `high`, `xhigh`, `max`) only for models supporting adjustable effort; when `agy models` lists effort-suffixed entries, pick that entry via `--model` without adding `--effort`.
- `--print-timeout <duration>`: Bound every call (default `5m`, hard ceiling `10m`) and set the caller's shell timeout slightly higher so `agy` terminates cleanly.
- `-p` / `--print`: Always place last as a single quoted string. Because `agy -p` does not consume stdin directly, embed piped content into `-p`.

For flexible exploration or reasoning jobs on `headless-explore`, state the question, scope/directory boundaries, and evidence needed in a goal-oriented prompt rather than prescribing step-by-step commands:

```bash
# Grounded web lookup from a clean directory (returns answer-only Argdown handback in .response)
(cd /tmp && agy --sandbox --agent headless-web --model "<fast-model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "Search the web: <question>. Cite source URLs inline.")

# Embedded diff transform with zero file or web access
DIFF="$(git diff --staged)"
(cd /tmp && agy --sandbox --agent headless-bare --model "<fast-model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "$(printf 'Audit this diff for breaking changes.\n\n---\n%s' "$DIFF")")

# Flexible mid-tier exploration and reasoning (add --add-dir /abs/path if reading outside cwd)
agy --sandbox --agent headless-explore --model "<mid-tier-model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "Investigate how hook dispatch normalizes client events across the repository. State the flow, key invariants, and any edge cases with file:line citations."
```

## 3. Pre-Flight JSON Schema Validation & Output Checks

`--json-schema` requires `--output-format json` (or `stream-json`) and a valid JSON Schema whose root declares `"type": "object"` (bare `"string"` or `"array"` schemas and missing files exit `1` at startup). Include an `argdown` (or `reasoning`) string property in the schema when you also want the `premise-check` Argdown handback inside structured JSON.

1. **Validate and inline upfront**: Before changing into `/tmp` (so relative schema paths never break), validate the schema with `jq` and compact it into a variable:
   ```bash
   SCHEMA="$(jq -ce 'if type == "object" and .type == "object" then . else error("root_not_object") end' schema.json)"
   (cd /tmp && agy --sandbox --agent headless-bare --model "<fast-model>" \
     --disable-slash-commands --print-timeout 5m \
     --output-format json --json-schema "$SCHEMA" -p "<prompt>")
   ```
   For inline schemas, pipe the JSON string into the same `jq -ce` check via `<<<"$RAW_SCHEMA"`.
2. **Validate the response before reading output**:
   - With `--output-format json` or `stream-json`, verify process exit code `0`, `.status == "SUCCESS"`, `.finished_reason == null` (non-null indicates `print_timeout`, `interrupted`, or `error`), and empty `.denied_actions`. Extract `.structured_output` when `--json-schema` is active (fail if null or absent) or `.response` otherwise (answer only; use `--output-format stream-json` only if you explicitly need intermediate step events).
   - Without `--json-schema` or envelope metadata needs, `--output-format text` returns the final answer directly on stdout (verify exit code `0`).
   - Optional footprint check: inspect `.usage` (`input_tokens`, `cache_read_tokens`, `output_tokens`, `thinking_tokens`) and `.conversation_id` on JSON envelopes.

## 4. Avoid Repeated Spawn Taxes

- **Sequential follow-ups**: Save `.conversation_id` from `--output-format json` and pass `--conversation <id>` (or `-c`) on follow-up calls within the cache TTL to reuse the warm prefix cache.
- **Batch prompts**: Keep one persistent headless process open with `--input-format stream-json --output-format stream-json` (omitting `-p`), writing one NDJSON user message to stdin after each prior turn's `result` event.

## 5. Verify & Fail Fast

- Evaluate the returned `premise-check` Argdown handback on the face of the record per `ida:premise-check` (ask coverage, inline quoted evidence, warrants, and defeaters -- zero _de novo_ fact-checking; remand or rerun if evidence is missing) before relying on or relaying its answer.
- Any non-zero exit, timeout, `.status != "SUCCESS"`, non-null `.finished_reason`, non-empty `.denied_actions`, or missing `.structured_output` is a failure -- report it verbatim without silent fallback or retrying with weakened flags.
