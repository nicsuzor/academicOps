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

Every daily note run must execute Steps 0 through 7 in sequential order to completion:

- **Step 0**: Read existing daily note content and enrich it (preserve user annotations, elevate verbatim requests, itemize merged PR checklists).
- **Step 1**: Read user asks from the graph and group into dense thematic objectives.
- **Step 1.5**: Triage mobile captures in `notes/mobile-captures/`.
- **Step 2**: Situate verbatim requests into tracking tasks and situated work tasks.
- **Step 3**: Read today's agenda (correspondence sweep, email, and calendar).
- **Step 4**: Reconcile the graph (`wf-reconcile`).
- **Step 5**: Collect open PRs needing the user across repositories.
- **Step 6**: Assemble state via graph review subagent (`pauli`).
- **Step 7**: Write the note to the PKB and read it back.

### Execution Invariants

- **No Shortcutting**: Never skip steps, truncate passes, or terminate early based on subjective currency of an existing note or the breadth of the full pass.
- **Graceful Degradation**: When external services (GitHub, Email, Calendar) are unreachable, attempt all available tool channels before recording quiet single-line status in-place.
- **Trace Receipts Only**: Record step completion receipts in internal execution traces and telemetry. Never append run execution logs, hourly heartbeats, cron timestamps, or raw reconcile mutation dumps to the daily note body.

## 3. Conversational Handover

When invoked via interactive or chat channels (such as Telegram):

1. Summarize today's priorities and progress scannably (under one minute reading time).
2. Highlight open decisions needing the user from `## With you`.
