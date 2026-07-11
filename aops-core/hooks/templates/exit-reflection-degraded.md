---
name: exit-reflection-degraded
title: Exit-Reflection Escape-Hatch (degraded)
category: template
description: |
  LOUD, user-visible message emitted when the exit_reflection gate's FULL
  tier degrades from DENY to WARN-and-allow after N consecutive Stop blocks
  in the same turn — the safety escape-hatch that prevents a structurally-
  broken auditor dispatch from permanently trapping the session. This is
  failure-degradation only, NOT a normal bypass. Variables: {threshold} — the
  consecutive-block count reached.
---

⚠ EXIT-REFLECTION ESCAPE-HATCH: the full-checklist exit gate blocked exit {threshold} times without a legal exit (auditor run, or an honest release_task completion/failure). Degrading to WARN-and-allow so a broken dispatch cannot permanently trap the session. This is a DEGRADED exit — the session was NOT reflected on. If you see this repeatedly, exit-reflection dispatch is broken; flag it.
