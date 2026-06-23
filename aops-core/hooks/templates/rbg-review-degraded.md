---
name: rbg-review-degraded
title: RBG Review Escape-Hatch (degraded)
category: template
description: |
  LOUD, user-visible message emitted when the rbg-review gate degrades from
  DENY to WARN-and-allow after N consecutive Stop blocks in the same turn —
  the safety escape-hatch that prevents a structurally-broken rbg dispatch from
  permanently trapping the session. This is failure-degradation only, NOT a
  normal bypass. Variables: {threshold} — the consecutive-block count reached.
---

⚠ RBG-REVIEW ESCAPE-HATCH: the final axiom-audit gate blocked exit {threshold} times without rbg returning a verdict. Degrading to WARN-and-allow so a broken rbg dispatch cannot permanently trap the session. This is a DEGRADED exit — the session was NOT axiom-audited. If you see this repeatedly, rbg dispatch is broken; flag it.
