---
trigger: always_on
description: Tests exercise behaviour that can break, never restate our own implementation.
---

## Tests verify behaviour, not our own code

A test exercises behaviour that could break in a way that matters. Do not write a test that restates the implementation: one that asserts a string the code itself emits is or is not printed, that a file still references what it references, that a mapping still holds the entry the same PR added, or that a checker still covers the globs it was configured with.
