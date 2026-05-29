---
name: qa-policy-context
title: QA Policy Context Injection
category: template
description: |
  Full context injection when QA gate blocks exit.
  Variables: {temp_path}
---

QA verification is required before you can exit.

- Invoke the **marsha** agent via the `/verify` skill against the requirements captured at `{temp_path}`.
- Follow whatever marsha returns, but don't print its output to the user — it just clutters the conversation.

This gate is currently BLOCKED; clearing it is quick once verification runs.
