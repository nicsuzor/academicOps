---
trigger: always_on
description: Test executable behavior for plausible defects; markdown owes no tests.
---

## Tests verify behaviour

- **Outputs, not contents:** Test public interfaces, never internals, configs, or markdown (verify instructions via agent runs; specs via review).
- **Defect check:** Name a plausible bug first; test must fail when present (fixes need red-before-fix tests).
- **Banned defects:** Ban mirror, tautological, implementation-coupled tests, and one-off checks; rewrite or delete tests failing on valid edits.
- **Quality & hooks:** Keep tests single-behavior (AAA), hermetic (boundary doubles), independently expected. Spawn hooks across environments and assert fail-closed exit (e.g., 127).
