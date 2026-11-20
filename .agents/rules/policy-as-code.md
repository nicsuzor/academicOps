---
trigger: always_on
description: Store test policy inputs in tests/policy.toml, not Python literals.
---

## Policy as code

- Put test policy inputs (markers, exemptions, thresholds) in `tests/policy.toml`, not Python literals.
- Assert behavior derived from `tests/policy.toml` against real outputs, never config or instruction text.
