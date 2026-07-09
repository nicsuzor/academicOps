---
trigger: always_on
description: Single Source of Truth — no parallel copies
---

## Single Source of Truth — no parallel copies {#single-source-of-truth}

For every fact, rule, definition, dataset, or artifact the framework maintains, there MUST be exactly one authoritative copy; all other references point to it.

- You MUST NOT create, maintain, or tolerate parallel copies that may drift. When duplicates are found, consolidate them OR delete the non-authoritative version — there is no third option.
- Applies recursively to the framework's own principles: no axiom, heuristic, or rule defined in more than one place. One location is canonical; others link or are removed.
- One golden path. No defaults, no guessing, no parallel backwards-compatible variants competing to be the source.
- _E.g._ a principle stated in full in two skill files (rather than stated once and linked) is a violation even if the two copies currently agree.

_Review: [[AXIOMS-REVIEW#single-source-of-truth]]._
