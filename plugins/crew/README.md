# crew

The crew that works alongside ida: the james, pauli and marsha agents, the `axioms` skill, and two in-session rule-checking hooks.

- **james**: lead executor and dialectical review supervisor (`agents/james.md`).
- **pauli**: PKB custodian, planning lead, and strategic-fit reviewer (`agents/pauli.md`).
- **marsha**: qualitative quality and excellence reviewer (`agents/marsha.md`).

> **The hooks are currently disabled** (temporarily, since 2026-08-08, `v0.7.1`). The plugin still registers them, so each hook event runs the dispatcher, but no handler is enabled: the dispatcher returns nothing, and every tool call and stop goes through unchecked. The agents and the `axioms` skill are unaffected. The two checks below describe what the hooks do once re-enabled.

- **Turn-by-turn check** (disabled): Evaluates tool calls against live rules via a fast classifier model and injects advisory context on match. Fails open and never blocks.
- **Turn-boundary stop gate** (disabled): At a `Stop` event, holds completion once so the agent explicitly checks its work against governing rules and cites verifiable evidence.

## How it works

```mermaid
flowchart TD
    E["Hook event: PreToolUse, Stop or SubagentStop (Claude Code); PreInvocation (agy)"] --> D["crew hook dispatcher"]
    D --> H{"Any handler enabled for this event?"}
    H -- "No (current state)" --> N["No output: the tool call or stop proceeds unchecked"]
    H -. "PreToolUse, once re-enabled" .-> C{"Evaluator configured?"}
    C -- "No" --> N
    C -- "Yes" --> M["Classifier checks the tool call against live rules"]
    M -- "Rule matched" --> A["Advisory with the rule text; the call still proceeds"]
    M -- "No match, or evaluator outage (named once per session)" --> N
    H -. "Stop / SubagentStop, once re-enabled" .-> B["Stop held once per turn chain: agent asked to check its work against the rules and cite evidence"]
```

## Components

| Component | File | Purpose |
| - | - | - |
| `PreToolUse` / `PreInvocation` | `cope_hooks_disabled/dispatch.py` | Disabled. Ran turn/tool checks (Claude Code) or injected rule roster (agy). |
| `Stop` / `SubagentStop` | `cope_hooks_disabled/dispatch.py` | Disabled. Prompted rule verification before final handback. |
| Evaluation Handler | `cope_hooks_disabled/handlers.py` | Disabled. Evaluates tool calls against rules and injects advisories. |
| Stop Handler | `cope_hooks_disabled/handlers.py` | Disabled. Dispatches `rule-check.md` once per turn chain. |
| Evaluator Client | `cope_hooks_disabled/evaluator.py` | HTTP client for `cope` and `openai` wire protocols. |
| Rule Loader | `cope_hooks_disabled/rules.py` | Merges three rule scopes (`trigger: always_on`). |
| Messages | `hooks/messages/*.md` | Templates for advisories, prompts, and stop checks. |

## Rule Scopes

Rules are loaded and merged across three scopes (`axioms` cannot be overridden):

1. **Axioms:** The `axioms` skill's files, `skills/axioms/` (inviolable baseline).
2. **Project rules:** `$CWD/.agents/rules/*.md` (project-local).
3. **User rules:**
   - **In-session evaluator (COPE):** `$COPE_USER_RULES_DIR/*.md` (user-scoped, `trigger: always_on`).
   - **Compliance review:** Active PKB documents with `type: rule`.

Only markdown files declaring `trigger: always_on` are sent to the evaluator or roster.

## Configuration

Set via environment variables:

| Variable | Protocol / Hook | Default | Purpose |
| - | - | - | - |
| `COPE_EVALUATOR_URL` | All | none | Evaluator endpoint URL (omitted = clean no-op). |
| `COPE_EVALUATOR_PROTOCOL` | `cope` or `openai` | none | Protocol format spoken by endpoint. |
| `COPE_EVALUATOR_MODEL` | All | none | Model identifier sent in requests. |
| `COPE_EVALUATOR_API_KEY` | Optional | none | Bearer token for authenticated endpoints. |
| `COPE_EVALUATOR_TIMEOUT` | All | `5.0` | Max seconds allowed for per-tool check sweep. |
| `COPE_EVALUATOR_TRACE_PATH` | Tracing | none | Path to append JSONL rule evaluation logs. |
| `COPE_EVALUATOR_OTEL_TRACE_PATH` | Tracing | none | Path to append OTLP JSON file spans. |
| `COPE_USER_RULES_DIR` | Roster / Loader | none | Directory containing user-scoped rules (`*.md`). |

## Local Evaluator Stack

Run a local open-weights classifier (`zentropi-ai/cope-b-a4b` via llama.cpp + shim):

```bash
uv run python scripts/cope_eval_stack.py start \
  --server-bin <llama.cpp>/build/bin/llama-server \
  --model <path>/cope-b-a4b.Q4_K_M.gguf \
  --log-dir <state-dir> \
  --warmup .agents/rules
```

Point the agent environment at `COPE_EVALUATOR_URL=http://127.0.0.1:8099/v1/label` and `COPE_EVALUATOR_PROTOCOL=cope`.

## Dependencies

- `hooks/handlers.py`: Hook dispatcher runtime (`lib/hooks/dispatch.py` staged at build).
- `agents/`: the james, pauli and marsha agents.
- `skills/axioms/`: the `axioms` skill; its files are the baseline axioms.
- External or local Reflexes/CoPE or OpenAI-compatible classifier endpoint.
