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

To proceed correctly, spawn the hydrator subagent:

```
Delegate to **prompt-hydrator**:

"Read {temp_path} and provide workflow guidance."
```
