# rbg

In-session rule checking on two operational layers:

- **Turn-by-turn**: Evaluates tool calls against live rules via a fast classifier model and injects advisory context on match. Fails open and never blocks.
- **Turn-boundary stop gate**: At a `Stop` event, holds completion once so the agent explicitly checks its work against governing rules and cites verifiable evidence.

## Components

| Component                      | File                  | Purpose                                                           |
| ------------------------------ | --------------------- | ----------------------------------------------------------------- |
| `PreToolUse` / `PreInvocation` | `hooks/dispatch.py`   | Runs turn/tool checks (Claude Code) or injects rule roster (agy). |
| `Stop` / `SubagentStop`        | `hooks/dispatch.py`   | Prompts rule verification before final handback.                  |
| Evaluation Handler             | `hooks/handlers.py`   | Evaluates tool calls against rules and injects advisories.        |
| Stop Handler                   | `hooks/handlers.py`   | Dispatches `rule-check.md` once per turn chain.                   |
| Evaluator Client               | `hooks/evaluator.py`  | HTTP client for `cope` and `openai` wire protocols.               |
| Rule Loader                    | `hooks/rules.py`      | Merges three rule layers (`trigger: always_on`).                  |
| Messages                       | `hooks/messages/*.md` | Templates for advisories, prompts, and stop checks.               |

## Rule Layers

Rules are loaded and merged across three layers (earlier layers cannot be overridden):

1. **Layer 1:** Shipped `axioms/` (inviolable baseline).
2. **Layer 2:** `$CWD/.agents/rules/*.md` (project-local).
3. **Layer 3:** `$ACA_DATA/.agents/rules/*.md` (user-scoped).

Only markdown files declaring `trigger: always_on` are sent to the evaluator or roster.

## Configuration

Set via environment variables:

| Variable                         | Protocol / Hook    | Default | Purpose                                         |
| -------------------------------- | ------------------ | ------- | ----------------------------------------------- |
| `COPE_EVALUATOR_URL`             | All                | none    | Evaluator endpoint URL (omitted = clean no-op). |
| `COPE_EVALUATOR_PROTOCOL`        | `cope` or `openai` | none    | Protocol format spoken by endpoint.             |
| `COPE_EVALUATOR_MODEL`           | All                | none    | Model identifier sent in requests.              |
| `COPE_EVALUATOR_API_KEY`         | Optional           | none    | Bearer token for authenticated endpoints.       |
| `COPE_EVALUATOR_TIMEOUT`         | All                | `5.0`   | Max seconds allowed for per-tool check sweep.   |
| `COPE_EVALUATOR_TRACE_PATH`      | Tracing            | none    | Path to append JSONL rule evaluation logs.      |
| `COPE_EVALUATOR_OTEL_TRACE_PATH` | Tracing            | none    | Path to append OTLP JSON file spans.            |
| `ACA_DATA`                       | Roster / Loader    | none    | Root directory for layer 3 user rules.          |

## Local Evaluator Stack

Run a local open-weights classifier (`zentropi-ai/cope-b-a4b` via llama.cpp + shim):

```bash
python3 scripts/cope_eval_stack.py start \
  --server-bin <llama.cpp>/build/bin/llama-server \
  --model <path>/cope-b-a4b.Q4_K_M.gguf \
  --log-dir <state-dir> \
  --warmup .agents/rules
```

Point the agent environment at `COPE_EVALUATOR_URL=http://127.0.0.1:8099/v1/label` and `COPE_EVALUATOR_PROTOCOL=cope`.

## Dependencies

- `lib/hooks/`: Shared hook dispatcher runtime (`dispatch.py`).
- `lib/axioms/`: Injected Layer 1 baseline rules.
- External or local Reflexes/CoPE or OpenAI-compatible classifier endpoint.
