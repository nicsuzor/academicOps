---
name: session-trace
description: Read what a past session actually did from the Arize Phoenix span store -- assemble a readable markdown transcript with step durations, token usage and cost, answer "how did this decision get made", or query spans for tool calls, errors, latencies, token spend and subagent dispatches. Use when asked how or why an agent decided something, what a session or worker really ran, where time or tokens went, or to resolve values a local transcript truncated. Not for live tails, or for launching and driving a run.
---

# Session Trace

Phoenix keeps every span whole: untruncated tool inputs and outputs, model output, token
counts and millisecond latencies. Read it rather than a session's own account of itself.

## Transcript: how did this decision get made

```bash
uv run python "${CLAUDE_SKILL_DIR}/scripts/phoenix_transcript.py" <session-id / conversation-id | slug | trace-id> --out <dir>/<slug>.transcript.md [--sanitize-paths]
```

- Configuration is flags or environment: `--base-url` or `$PHOENIX_MCP_URL` (the Phoenix
  HTTP root), and `--project` or `$PHOENIX_MCP_PROJECT`. Phoenix UI deep-links resolve via
  `--ui-base-url` or `$PHOENIX_UI_URL` (default derived from the Phoenix endpoint). With neither
  flag nor variable set, the script supplies no default value and halts. Spans already fetched another
  way render with `--from-file spans.json`.
- One paged fetch on `session.id`; a thousand-span session takes seconds.
- It writes two files and prints the summary (totals, per-turn table, cost by model,
  slowest steps, errors):
  - `<slug>.transcript.md` -- the full record: one `## Turn N` per turn, one `### N.M`
    per model or tool call with its duration, tokens and cost, payloads folded in
    `<details>`, nothing truncated. Every turn links directly to its Phoenix session and span(s).
  - `<slug>.outline.md` -- prompts, model calls with their text, and replies; each tool
    call is one bullet under the model call that made it, labelled with the call's own
    action summary (agy `toolAction` / `toolSummary`, Claude Code `description`), with a line beneath
    naming what it acted on: the calls and literal arguments inside a code-mode block,
    else the command, path or query. Every turn links directly to its Phoenix session and span(s).

## Deliverable and durable storage

When session transcripts are requested, the primary output is the two generated files
(`<slug>.transcript.md` full and `<slug>.outline.md` condensed). Both files must be saved
to a durable destination (such as the PKB or a committed repository artifact), never left
only on the local filesystem of an ephemeral container where files vanish on exit.

- **Persisting to the PKB**: Create durable notes (e.g. via `pkb_create` with `type: "note"`,
  tags `["session-trace", "transcript"]` or `["session-trace", "outline"]`, linking to the
  relevant task or session). Pass `--sanitize-paths` to `phoenix_transcript.py` (or sanitize
  literal host filesystem paths like `/home/*` or `/Users/*`) so that PKB host-path rejection
  guards are not triggered during ingestion.
- **Persisting to a repository**: Save the files under the designated project/evaluation path
  and commit them to the branch or PR.

Read the summary, then the outline for the turns that bear on the question. Open a step's
payload by its anchor (`grep -n 'id="t5-3"' <slug>.transcript.md`) rather than reading the
whole transcript, because that is where the cost goes. Answer with the turn and step
anchors where the decision was made, and provide the durable pointer (or path) to the
persisted transcript and outline files.

To find the session: a full session ID / conversation ID, a slug, or a trace id all resolve. Given only a task or a
time, find the session with Recipe A or F in [references/sql-recipes.md](references/sql-recipes.md).

## Other exports

- `uv run python scripts/phoenix_trace.py <session-id / conversation-id>` -- the span forest as JSON (`full`, with
  `roots` and `orphans`) and a controller view. Check `meta.session_error_count`,
  `orphans`, `meta.trace_contamination` (traces shared with other sessions), and rank
  `subagents[]` by `collapsed_span_count` for the expensive branches.
- `uv run python "${CLAUDE_SKILL_DIR:-plugins/ida/skills/session-trace}/scripts/phoenix_token_cost.py" --since <time>` -- spend ranked across sessions, or
  `--by task`. Prices are list prices per million tokens; the dollar column is
  comparable spend, not an invoice. Gemini spans may carry no token counts.

## Cross-session search

With no session id in hand ("every prompt mentioning X"), follow "Cross-session search" in
[references/sql-recipes.md](references/sql-recipes.md): filter and project on the server, write
rows to a file in session scratch, print counts and ids only, and read the file by anchor.
Never let search results accumulate in your context.

## Ad-hoc queries

The span store is also reachable through the `services` MCP proxy:
`portal_codemode_execute` calling `codemode.phoenix_execute` with an async Python block
that runs `await call_tool("executeSql", {"sql": ...})` (several per block is fine). Read
[references/span-store.md](references/span-store.md) before writing a query, then take
the recipe from [references/sql-recipes.md](references/sql-recipes.md).

## Constraints

- Filter on `session.id`, never `trace_id`: one trace can hold several sessions across agent interactions.
- Subagent session identity varies by harness:
  - In `claude` (Claude Code), in-process subagents / teammates may share the dispatching session's
    `session.id`, whereas background or detached workers run in their own sessions.
  - In `agy` (Antigravity), `invoke_subagent` spawns each subagent with its own distinct `session.id`
    (`conversationId` in the `invoke_subagent` response, matching `sender=<uuid>` on inbound messages).
  - When a subagent runs under its own distinct `session.id`, the child session carries no explicit parent
    attribute in its span metadata; correlate them using Recipe F (matching prompt text, time window, and agent type).
- Phoenix tool spans prove execution rather than logical entailment or sufficiency; auditing and QA must inspect durable primary deliverables rather than ephemeral container paths, evaluating whether observed evidence logically entails the claimed outcomes.
