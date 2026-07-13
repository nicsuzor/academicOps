---
trigger: always_on
description: Explicit Approval for Costly Operations — no self-authorised spend or reach
---

## Explicit Approval for Costly Operations — no self-authorised spend or reach {#costly-ops-approval}

Potentially expensive or high-blast-radius operations require explicit prior approval naming scope, volume, and expected cost. "Self-evidently bounded" means cost AND reach are visible in the action itself, without inspecting the dataset, the configuration, or runtime behaviour.

- **Always requires approval:** batch API calls, bulk writes, mass file operations, recursive deletes, broadcast sends, anything touching production systems, anything whose cost scales with input size.
- **Does not require approval:** a single verification call (1–3 model invocations), reading one file, editing one named file, a search whose scope is named and finite.
- Approval is scope-bound: approval for a specific volume is not approval for a larger one. If scope expands mid-execution, halt and re-confirm. The standard is _self-evidently bounded_, not _plausibly cheap_.
- _E.g._ self-authorising a bulk operation because "the cost looked low" — without the bound being visible in the call itself — is the prohibited move.

_Review: [[AXIOMS-REVIEW#costly-ops-approval]]._
