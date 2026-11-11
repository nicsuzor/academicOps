---
name: daily
description: Generate or update today's daily note and reply with a scannable run-down on conversational channels -- fetches and executes change-only PKB template tpl_daily. Use for "daily", "daily note", or Telegram /daily command. Exclude for routine status reports without daily note generation, plain graph truth maintenance (use reconcile), or autonomous worker dispatch (use dispatch).
---

# /daily -- Generate or Update Today's Daily Note

Execute the complete daily note lifecycle defined canonically in PKB template `tpl_daily`.

## 1. Dynamic Template Ingestion

Fetch the canonical template from the knowledge base using MCP:

- Call `pkb_get_document` with `id: "tpl_daily"`, `detail: "full"`, and `max_bytes: 50000`.
- Assert `truncated: false`. If truncated or unavailable, halt immediately per fail-fast.

## 2. Step Execution Contract

A daily note run executes change-only steps defined canonically in PKB template `tpl_daily` since the last run's cursor timestamp. When Step 0 detects no delta, the run halts immediately with a zero-delta ledger. Where anything here and `tpl_daily` differ, `tpl_daily` governs.

### Execution Invariants

- **Change-Only Execution**: Process only changes occurring since the last completed run cursor; exit immediately when nothing changed.
- **Single-Flight Concurrency**: Never start a run while another daily note run is in progress.
- **Graceful Degradation**: When external services (GitHub, Email, Calendar) are unreachable, attempt all available tool channels before recording quiet single-line status in-place.
- **Trace Receipts Only**: Record step completion receipts in internal execution traces and telemetry. Never append run execution logs, hourly heartbeats, cron timestamps, or raw reconcile mutation dumps to the daily note body.

## 3. Conversational Handover

When invoked via interactive or chat channels (such as Telegram), reply with the note's top layer, readable in under a minute:

1. The note's `## Start here` item: what to do first, its first step and what is ready.
2. Today's fixed times and anything overdue owed to other people, from `## Today`.
3. How many decisions wait in `## With you`, naming the top one, with `/decide` offered for the rest.
