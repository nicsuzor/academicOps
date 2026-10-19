---
title: How did this decision get made
status: draft
---

# How did this decision get made

Anyone working in a project where the framework's plugins are installed can ask,
at any time, how an agent arrived at a decision, and get back a readable
transcript of the run with a clear answer drawn from it. The transcript is
assembled from the trace store, where tool inputs and outputs, model output,
token counts and latencies are kept whole.

This is the agent-assisted complement to
[cross-surface observability](observability.md), which covers what the user can
open on the infrastructure directly with no agent processing.

## User stories

### US-1 Ask how a decision got made and get a readable transcript and a clear answer

As anyone working in a project where our plugins are installed, I want to ask
at any time "how did this decision get made?" and get a readable transcript of
the session that made it and a clear answer from an agent, without it taking
forever or costing a leg, so that I can understand and audit what an agent did
and why.

- **AC-1.1** Given a full session id, a session slug, or a trace id, when the
  question is asked, then the agent resolves it to the owning session and
  fetches that session's spans from the trace store in one paged request
  sequence filtered on `session.id`, with no per-span or per-turn queries.
- **AC-1.2** Given a session's spans, when the transcript is assembled, then it
  is a single markdown file with a table of contents linking to one header per
  turn, and within each turn, in order, the incoming prompt, each model call,
  each tool call, and the final reply. Prompts, tool inputs and outputs, and
  model context are placed in folded `<details>` sections, and no content is
  truncated.
- **AC-1.3** Given the transcript, when it is read, then every turn, model call
  and tool call shows its wall-clock duration; every model call shows its model,
  fresh input, cache read, cache write and output tokens and its estimated cost;
  and each turn and the whole session carry totals, with a summary table at the
  top giving each turn's duration, tokens and cost.
- **AC-1.4** Given the transcript, when the agent answers, then it reads the
  summary and the turns that bear on the question rather than the raw spans,
  and its answer names the turn and step anchors where the decision was made.
- **AC-1.5** Given any project with the plugins installed, when the question is
  asked, then the workflow and its script are available from the plugin itself,
  with no project checkout, and the script holds nothing specific to one user,
  deployment or project: the trace store URL and project come from flags or the
  environment, and it reads the attribute conventions its emitters use
  (OpenInference, OpenTelemetry GenAI, and Claude Code's native spans).

## Design

### Where it lives

- **Workflow template** -- `plugins/ida/skills/workflow-library/workflows/trace-decision.md`,
  in the universal tier: the contract (a question and an identifier in; the
  transcript and an answer anchored to it out).
- **Method** -- the `session-trace` skill in the `ida` plugin, which carries the
  trace store's query facts and recipes and the transcript script
  `scripts/phoenix_transcript.py`.
- **Project-local debugging** -- `.agents/skills/debug/` keeps interactive
  driving of a run (surfaces, containers under tmux, probes, filesystem audit)
  and points to `session-trace` for telemetry.

### Fetch

The script pages `GET /v1/projects/{project}/spans?attribute=session.id:<id>`
to exhaustion, 1,000 spans a page: about one second per page on the reference
deployment. A slug is resolved through the sessions listing; a trace id through
one `trace_id=` fetch. Spans can also be read from a saved file, so a fetch made
another way (for instance through an MCP proxy) can be rendered offline.

### Assemble

- **Turns** are clusters of root spans whose time windows overlap. Two emitters
  often each open a root for the same turn (a hook-based tracer's `CHAIN` turn
  and a client's native interaction span); clustering joins them without
  depending on either.
- **Tool calls** are deduplicated on their call id (`tool.call_id`,
  `tool_use_id`, `tool.id`, `gen_ai.tool.call.id`). The rendered call takes its
  input and output from the span that holds them whole and its duration from the
  execution span.
- **Model calls** are `LLM` spans, deduplicated on response id where present.
  Assistant text comes from `output.value`, `llm.output_messages` or
  `response.model_output`; the context the call received is folded.
- **Subagents** sharing the session are labelled from `agent.name` / `agent.id`
  where an emitter sets them.

### Metrics

Token fields are normalised to fresh input, cache read, cache write and output
across conventions (OpenInference `prompt` includes cache tokens; native
`input_tokens` does not). Cost uses the price table shared with
`phoenix_token_cost.py` (list prices per million tokens, overridable with
`--prices`); unpriced models are costed at zero and named in the footer. The
dollar figure is comparable spend, not an invoice.
