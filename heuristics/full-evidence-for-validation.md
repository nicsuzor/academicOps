---
name: full-evidence-for-validation
title: Full Evidence for Human Validation
priority: 58
type: heuristic
category: spec
parent: llm-semantic-evaluation
tags: [framework, heuristics, verification]
---

# Full Evidence for Human Validation

**Statement**: Demo tests and verification output must show FULL untruncated content so humans can visually validate. Truncating evidence defeats the purpose of verification.

## Derivation

Truncated output hides failures. Full evidence enables human judgment.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Convention via `@pytest.mark.demo` requirement. See [[RULES.md]].
