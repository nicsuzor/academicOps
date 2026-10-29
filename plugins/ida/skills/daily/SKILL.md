---
name: daily
description: Update today's daily note and reply with a run-down on Telegram -- executes the PKB template tpl_daily and reports today's priorities, progress, and open decisions. Use for "daily", "daily note", or Telegram /daily command.
---

# Daily

Update today's daily note and reply with a scannable run-down on Telegram.

The daily note procedure is the PKB template `tpl_daily`.

1. Fetch `tpl_daily` from the PKB with `codemode.pkb_get_task({ id: "tpl_daily", max_bytes: 50000 })`. If the result carries `truncated: true`, halt and report it.
2. Execute its steps in order to read, enrich, and reconcile today's daily note in the PKB. Asks come strictly from the task graph and note; no step reads session traces or any trace store.
3. Reply on Telegram with a scannable run-down of today's priorities, completed work, and open decisions in `## With you`.
