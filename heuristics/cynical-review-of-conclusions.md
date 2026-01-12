---
name: cynical-review-of-conclusions
title: Cynical Review of Conclusions
priority: 51
type: heuristic
category: spec
tags: [framework, heuristics, review, evidence]
---

# Cynical Review of Conclusions

**Statement**: Before attributing failure to a specific cause (model, component, configuration), verify the attribution with evidence. Ask: "What unwarranted assumptions am I making?"

## Derivation

Agents jump to conclusions based on single observations. A cynical critic would ask: "You haven't discharged the burden of showing that other models/configurations would not make the same mistake."

## Examples

| Conclusion                   | Cynical Challenge              | Required Evidence                  |
| ---------------------------- | ------------------------------ | ---------------------------------- |
| "Haiku skipped the hydrator" | Did you test with Sonnet/Opus? | Run same test with multiple models |
| "The hook failed"            | Did the hook fire at all?      | Check hook execution logs          |
| "Instructions unclear"       | Did the agent even see them?   | Verify context injection           |

## Enforcement

Soft gate: Before filing issues that attribute failure to a specific cause, verify the attribution experimentally or acknowledge the assumption explicitly.

## Anti-pattern

❌ "Haiku is too eager to complete simple tasks" (single observation, no comparison)
✅ "Haiku skipped pipeline in test X. TODO: verify Sonnet/Opus behavior before concluding this is model-specific."
