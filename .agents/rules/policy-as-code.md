---
trigger: always_on
description: Define architectural policies and test invariants in tests/policy.toml rather than hardcoding literals in Python test files.
---

## Policy as Code in Tests

Do not hardcode architectural policies, messaging invariants, or enforcement levels inside Python test files.

- Policies (e.g., required text snippets, specific hook mappings, or message exemptions) must be defined in `tests/policy.toml`.
- Tests must assert against the configuration in `policy.toml`, never against hardcoded Python literals.
- This separates the _mechanism_ of the test from the _policy_ of the platform, allowing non-engineers to review and modify policies without rewriting code.
- This never licenses asserting that `policy.toml` -- or any agent, skill, settings, or instruction file -- still declares the same names or values it declares today. `policy.toml` supplies an input an assertion is _derived from_ (an exemption list to check real messages against, a threshold to check a real count against); the assertion itself checks something the code does with that input, never the config's own content restated as its own check.
