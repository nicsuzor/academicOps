---
trigger: always_on
description: Tests exercise behaviour that can break, never restate our own implementation.
---

## Tests verify behaviour, not our own code

A test exercises behaviour that could break in a way that matters. Do not write a test that restates the implementation: one that asserts a string the code itself emits is or is not printed, that a file still references what it references, that a mapping still holds the entry the same PR added, or that a checker still covers the globs it was configured with.

A change to any agent-facing instruction text -- e.g. an agent definition, skill, workflow template, rule, axiom, AGENTS.md or CLAUDE.md, or slash command (markdown, unlike an executable CLI or script) -- owes no new test that asserts its wording. Prove it by a fresh agent's run that follows it, judged against the acceptance criteria. Where an instruction asks for test-first, the failing baseline is a run without the change, not a wording test. A spec is checked by review.
