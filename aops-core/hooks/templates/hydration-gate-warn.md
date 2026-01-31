---
name: hydration-gate-warn
title: Hydration Gate Warn Message
category: template
description: |
  Warning message shown when hydration gate is in warn mode.
  Alerts agent that hydrator should be invoked, but allows proceeding.
---

⚠️  HYDRATION GATE (warn-only): Hydrator not invoked yet.

This session is in WARN mode for testing. In production, this would BLOCK all tools.

To proceed correctly, invoke the **aops-core:prompt-hydrator** agent or skill:

- For Claude Code: `activate_skill(name="aops-core:prompt-hydrator", prompt="Analyze context in {temp_path}")`
- For Gemini CLI: `activate_skill(name="prompt-hydrator", prompt="Analyze context in {temp_path}")`
