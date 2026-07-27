---
description: Operations with unbounded cost or blast radius need explicit prior approval naming scope and volume.
trigger: always_on
---

## Explicit Approval for Costly Operations

Expensive or high-blast-radius operations require explicit prior approval naming scope, volume, and expected cost. The standard is _self-evidently bounded_ — cost and reach visible in the action itself, without inspecting the dataset, the configuration, or runtime behaviour — not _plausibly cheap_.

- **Requires approval:** batch API calls, bulk writes, mass file operations, recursive deletes, broadcast sends, anything touching production, anything whose cost scales with input size.
- **Does not:** a single verification call, reading one file, editing one named file, a search whose scope is named and finite.
- Approval is scope-bound. Approval for one volume is not approval for a larger one; if scope expands mid-execution, halt and re-confirm.

Self-authorising a bulk operation because "the cost looked low", without the bound being visible in the call itself, is the prohibited move.
