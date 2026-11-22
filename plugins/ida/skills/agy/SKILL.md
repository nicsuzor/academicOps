---
name: agy
description: Run a low-context headless Antigravity (agy) agent from Claude Code for quick text transforms, grounded web searches, named-file reads, or schema-validated JSON output under 5 minutes. Use for short, read-only, or structured-output queries delegated to agy. Exclude for repository writes or work over 5 minutes (use /dispatch), or when already inside an agy session.
---

# /agy -- Low-Context Headless Antigravity Invocation

Invoke `agy` headlessly from Claude Code using isolated, minimal custom agent profiles (`inheritCustomizations: false`, `inheritMcp: false`) to strip MCP schemas, workspace rules, plugins, and slash-command tables from Turn 1. If already running inside an `agy` session, use native tools or subagents directly. Route any work requiring repository writes, broad codebase edits, or more than 5 minutes (10-minute ceiling) to isolated container dispatch (`/dispatch`).

## 1. Choose a Low-Context Agent Profile

Always pass `--agent <profile>` so `agy` never boots a full default session:

| Profile | Capabilities | Working directory |
| :- | :- | :- |
| `headless-bare` | Zero file or web tools (`finish` only; excludes default prompt components) | Clean directory outside repos (e.g. `/tmp`) |
| `headless-web` | Grounded web search (`search_web`, `read_url_content`, `finish`; excludes default prompt components) | Clean directory outside repos (e.g. `/tmp`) |
| `headless-ro` | Read-only local files (`view_file`, `grep_search`, `find_by_name`, `list_dir`, `finish`; keeps workspace path context) | Target directory (plus `--add-dir <abs_path>` if needed) |

For `headless-ro`, name explicit file paths in the prompt; when broad search or diff collection is needed, gather the matching lines or diff in the caller and pass them to `headless-bare`.

## 2. Startup Options & Invocation

Apply these startup flags on every local headless call:

- `--sandbox`: Mandatory. Never pass `--dangerously-skip-permissions` or `--mode accept-edits` on local runs.
- `--disable-slash-commands`: Mandatory. Strips slash-command routing and stops leading `/` paths or diffs in prompts from misfiring as CLI directives.
- `--model <model>`: Select an explicit model from `agy models` matching the needed capability tier (`fast`, `mid-tier`, or `flagship`).
- `--print-timeout <duration>`: Bound every call (default `5m`, hard ceiling `10m`) and set the caller's shell timeout slightly higher so `agy` terminates cleanly.
- `-p` / `--print`: Always place last as a single quoted string. Because `agy -p` does not consume stdin directly, embed piped content into the `-p` prompt argument.

```bash
# Grounded web lookup from a clean directory (zero repo rules scanned)
(cd /tmp && agy --sandbox --agent headless-web --model "<model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "Search the web: <question>. Include source URLs.")

# Embedded diff transform with zero file or web access
DIFF="$(git diff --staged)"
(cd /tmp && agy --sandbox --agent headless-bare --model "<model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "$(printf 'Audit this diff for breaking changes.\n\n---\n%s' "$DIFF")")

# Read-only inspection of named local files (add --add-dir /abs/path if reading outside cwd)
agy --sandbox --agent headless-ro --model "<model>" \
  --disable-slash-commands --print-timeout 5m --output-format json \
  -p "Read path/to/file.py and summarize retry defaults."
```

## 3. Pre-Flight JSON Schema Validation & Output Checks

`--json-schema` requires `--output-format json` (or `stream-json`) and a valid JSON Schema whose root declares `"type": "object"` (bare `"string"` or `"array"` schemas and missing files fail at startup with exit code `1`).

1. **Validate and inline upfront**: Before changing into `/tmp` (so relative schema paths never break), validate the schema with `jq` and compact it into a variable:
   ```bash
   SCHEMA="$(jq -ce 'if type == "object" and .type == "object" then . else error("root_not_object") end' schema.json)"
   (cd /tmp && agy --sandbox --agent headless-bare --model "<model>" \
     --disable-slash-commands --print-timeout 5m \
     --output-format json --json-schema "$SCHEMA" -p "<prompt>")
   ```
   For inline schemas, pipe the JSON string into the same `jq -ce` check via `<<<"$RAW_SCHEMA"`.
2. **Validate the response before reading output**:
   - With `--output-format json` or `stream-json`, verify process exit code `0`, `.status == "SUCCESS"`, `.finished_reason == null` (non-null indicates `print_timeout`, `interrupted`, or `error`), and empty `.denied_actions`. Extract `.structured_output` when `--json-schema` is active (fail if null or absent) or `.response` otherwise.
   - Without `--json-schema` or envelope metadata needs, `--output-format text` relies on exit code `0` and stdout.
   - Optional footprint check: inspect `.usage` (`input_tokens`, `cache_read_tokens`, `output_tokens`, `thinking_tokens`) and `.conversation_id` on JSON envelopes.

## 4. Avoid Repeated Spawn Taxes

- **Sequential follow-ups**: Save `.conversation_id` from `--output-format json` and pass `--conversation <id>` (or `-c`) on follow-up calls within the cache TTL to reuse the warm prefix cache.
- **Batch prompts**: Keep one persistent headless process open with `--input-format stream-json --output-format stream-json` (omitting `-p`), writing one NDJSON user message to stdin after each prior turn's `result` event.

## 5. Verify & Fail Fast

- Treat `agy`'s reply as another agent's report: verify cited URLs or file:line references before relying on or relaying any claim; uncited claims are leads, not verified facts.
- Any non-zero exit, timeout, `.status != "SUCCESS"`, non-null `.finished_reason`, non-empty `.denied_actions`, or missing `.structured_output` is a failure -- report it verbatim without silent fallback or retrying with weakened flags.
