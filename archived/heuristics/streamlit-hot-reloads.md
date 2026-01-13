---
name: streamlit-hot-reloads
title: Streamlit Hot Reloads
priority: 30
type: heuristic
category: spec
tags: [framework, heuristics, streamlit, tooling]
---

# Streamlit Hot Reloads

**Statement**: Don't restart Streamlit after changes. It hot-reloads automatically.

## Derivation

Restarting Streamlit wastes time and loses state. Hot reload is a built-in feature.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
