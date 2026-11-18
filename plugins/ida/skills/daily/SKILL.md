---
name: daily
description: Generate or update today's daily note and reply with a scannable run-down on conversational channels -- fetches and executes change-only PKB template tpl_daily. Use for "daily", "daily note", or Telegram /daily command. Exclude for routine status reports without daily note generation, plain graph truth maintenance (use reconcile), or autonomous worker dispatch (use dispatch).
---

# /daily -- Generate or Update Today's Daily Note

The canonical daily-note lifecycle and interactive conversational handover are defined in PKB template `tpl_daily`.

- Fetch `tpl_daily` untruncated via `pkb_get_document` (`id: "tpl_daily"`, `detail: "full"`). If truncated or unavailable, halt immediately per fail-fast.
- Execute `tpl_daily` verbatim, including its Step 5 attended handover (opening with day shape/relief, `## Ways in` options without steering, `## Today` schedule plus due-today or overdue commitments, and the `## With you` decision count). Do not duplicate or override `tpl_daily` rules here.
