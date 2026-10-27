---
name: session-trace
description: Read what a past session actually did from the Arize Phoenix span store -- assemble a readable markdown transcript with step durations, token usage and cost, answer "how did this decision get made", or query spans for tool calls, errors, latencies, token spend and subagent dispatches. Use when asked how or why an agent decided something, what a session or worker really ran, where time or tokens went, or to resolve values a local transcript truncated. Not for live tails, or for launching and driving a run.
---

# Session Trace

Phoenix keeps every span whole: untruncated tool inputs and outputs, model output, token
counts and millisecond latencies. Read it rather than a session's own account of itself.

## Transcript: how did this decision get made

```bash
uv run python "${CLAUDE_SKILL_DIR}/scripts/phoenix_transcript.py" <session-id / conversation-id | slug | trace-id> --out <dir>/<slug>.transcript.md
```

- Configuration is flags or environment: `--base-url` or `$PHOENIX_MCP_URL` (the Phoenix
  HTTP root), and `--project` or `$PHOENIX_MCP_PROJECT`. With neither flag nor variable set,
  the script supplies no default value and halts. Spans already fetched another way render with
  `--from-file spans.json`.
- One paged fetch on `session.id`; a thousand-span session takes seconds.
- It writes two files and prints the summary (totals, per-turn table, cost by model,
  slowest steps, errors):
  - `<slug>.transcript.md` -- the full record: one `## Turn N` per turn, one `### N.M`
    per model or tool call with its duration, tokens and cost, payloads folded in
    `<details>`, nothing truncated.
  - `<slug>.outline.md` -- prompts, model calls with their text, and replies; each tool
    call is one bullet under the model call that made it, labelled with the call's own
    action summary (agy `toolAction`, Claude Code `description`), with a line beneath
    naming what it acted on: the calls and literal arguments inside a code-mode block,
    else the command, path or query.

Read the summary, then the outline for the turns that bear on the question. Open a step's
payload by its anchor (`grep -n 'id="t5-3"' <slug>.transcript.md`) rather than reading the
whole transcript, because that is where the cost goes. Answer with the turn and step
anchors where the decision was made, and hand back the transcript path.

To find the session: a full session ID / conversation ID, a slug, or a trace id all resolve. Given only a task or a
time, find the session with Recipe A or F in [references/sql-recipes.md](references/sql-recipes.md).

## Other exports

- `uv run python scripts/phoenix_trace.py <session-id / conversation-id>` -- the span forest as JSON (`full`, with
  `roots` and `orphans`) and a controller view. Check `meta.session_error_count`,
  `orphans`, `meta.trace_contamination` (traces shared with other sessions), and rank
  `subagents[]` by `collapsed_span_count` for the expensive branches.
- `uv run python scripts/phoenix_token_cost.py --since <time>` -- spend ranked across sessions, or
  `--by task`. Prices are list prices per million tokens; the dollar column is
  comparable spend, not an invoice. Gemini spans may carry no token counts.

## Ad-hoc queries

The span store is also reachable through the `services` MCP proxy:
`portal_codemode_execute` calling `codemode.phoenix_execute` with an async Python block
that runs `await call_tool("executeSql", {"sql": ...})` (several per block is fine). Read
[references/span-store.md](references/span-store.md) before writing a query, then take
the recipe from [references/sql-recipes.md](references/sql-recipes.md).

## Constraints

- Filter on `session.id` (session ID / conversation ID), never `trace_id`: one trace can hold several sessions.
- Subagents share the dispatching session's `session.id`; a spawned worker session
  carries no attribute naming its parent (Recipe F correlates them).
- Phoenix tool spans prove execution rather than logical entailment or sufficiency; auditing and QA must inspect durable primary deliverables rather than ephemeral container paths, evaluating whether observed evidence logically entails the claimed outcomes.
