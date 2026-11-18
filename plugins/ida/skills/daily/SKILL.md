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
- **No Local Transcript or Hook Log Scraping**: Sweeps and subagents must never read or scrape local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files. Prompt and trace recoveries query Arize Phoenix via `ida:phoenix`.
- **Groundwork-First Prompt and Task Progression**: Every daily run's prompt and reconciliation sweeps load open high-value-prompt tracking tasks alongside window prompts and advance each item via groundwork:
  - Settle unknowns from the PKB first, then live GitHub and traces.
  - Close (`done`) shipped deliverables and releases the user knows about without waiting to verify user-side installation.
  - Place or promote ready next agent steps onto the graph at `status: queued` via `/q` and dispatch them via `/dispatch`.
  - Set tasks whose agent groundwork and recommendation are complete and that hit an invariant boundary or explicitly user-reserved pre-action hold/choice to `status: review` (`assignee: user`) so they surface in `## With you`.
- **Subagent Routing**: Dispatch execution sweeps to worker subagents and Step 4 graph synthesis to the knowledge base custodian using unprefixed subagent type names so dispatches resolve uniformly across client harnesses.
- **Autonomous Execution Mode**: Run unattended and recurring daily-note jobs in autonomous non-plan execution modes; when invoked interactively under a harness with plan mode active, keep plan-exit summaries terse (`<= 10` lines) and batch tool calls to avoid cadence interrupts.
- **Single-Pass Progress-Task Drafting**: Compose and checkpoint drafts directly onto the run's PKB progress task in a single semantic pass and pass the post-lock `modified` timestamp to the final diff write; never write local scratch draft files or run mechanical word-count or regex scripts.

## 3. Conversational Handover

When invoked via interactive or chat channels (such as Telegram), reply with the note's top layer, readable in under a minute:

1. The note's `## Start here` item: what to do first, its first step and what is ready.
2. Today's fixed times and anything overdue owed to other people, from `## Today`.
3. How many decisions wait in `## With you`, naming the top one, with `/decide` offered for the rest.
