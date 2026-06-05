---
name: qa-context
title: QA Context Template
category: template
description: |
  Template written to temp file for QA subagent verification.
  Variables: {session_context}, {tool_name}
---

# QA Verification — before `{tool_name}`

You have the full session record below: every request, decision, tool call, and result. Ground your verdict in what actually happened, not what was claimed.

Judge whether the work is **real, complete, and correct** — does it meet every requirement the user asked for, and does it actually serve them? Trace the evidence: run it, read the diff, check that imports resolve and call sites line up. Call out anything broken, skipped, substituted, or left half-done. Don't pad with a checklist; lead with what matters.

Close with one of: **PASS**, **PASS WITH NOTES** (list them), or **FAIL** (say what's wrong and what would fix it).

## Session record

{session_context}
