---
name: daily
description: Generate or update today's daily note and reply with a scannable run-down on conversational channels -- fetches and executes PKB template tpl_daily with mandatory completion of Steps 0 through 7. Use for "daily", "daily note", or Telegram /daily command. Exclude for routine status reports without daily note generation, plain graph truth maintenance (use reconcile), or autonomous worker dispatch (use dispatch).
---

# /daily -- Generate or Update Today's Daily Note

Execute the complete daily note lifecycle defined canonically in PKB template `tpl_daily`.

## 1. Dynamic Template Ingestion

Fetch the canonical template from the knowledge base using MCP:

- Call `pkb_get_document` with `id: "tpl_daily"`, `detail: "full"`, and `max_bytes: 50000`.
- Assert `truncated: false`. If truncated or unavailable, halt immediately per fail-fast.

## 2. Complete Step Execution Contract

Every daily note run must execute Steps 0 through 7 of `tpl_daily` in sequential order to completion, as that template defines them. This skill does not restate the steps; where anything here and `tpl_daily` differ, `tpl_daily` governs.

### Execution Invariants

- **No Shortcutting**: Never skip steps, truncate passes, or terminate early based on subjective currency of an existing note or the breadth of the full pass.
- **Graceful Degradation**: When external services (GitHub, Email, Calendar) are unreachable, attempt all available tool channels before recording quiet single-line status in-place.
- **Trace Receipts Only**: Record step completion receipts in internal execution traces and telemetry. Never append run execution logs, hourly heartbeats, cron timestamps, or raw reconcile mutation dumps to the daily note body.
- **No Local Transcript or Hook Log Scraping**: Sweeps and subagents must never read or scrape local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files. Prompt and trace recoveries query Arize Phoenix via `ida:session-trace`.
- **Subagent Routing Boundaries**: Sweeps dispatch to `ida:james` (execution sweeps) and Step 4 dispatches to `ida:pauli` (PKB graph and targeted `gh` queries only). Pauli operates strictly via PKB tools and targeted GitHub CLI queries, never reading local repository source files or shell output files on disk.

## 3. Conversational Handover

When invoked via interactive or chat channels (such as Telegram), reply with the note's top layer, readable in under a minute:

1. The note's `## Start here` item: what to do first, its first step and what is ready.
2. Today's fixed times and anything overdue owed to other people, from `## Today`.
3. How many decisions wait in `## With you`, naming the top one, with `/decide` offered for the rest.
