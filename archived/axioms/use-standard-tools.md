---
name: use-standard-tools
title: Use Standard Tools
priority: 21
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, tooling]
---

# Use Standard Tools

**Statement**: Use uv, pytest, pre-commit, mypy, ruff for Python development.

## Derivation

Standard tools have established ecosystems, documentation, and community support. Custom tooling creates maintenance burden.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Convention via `pyproject.toml` and `pre-commit` configuration. See [[RULES.md]].
