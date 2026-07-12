# Context Search — Technique & Citation Discipline

## Call ordering (stop early when you have enough)

1. **`get_task`** (only if you were handed a task id) — read what's already recorded before
   searching for more; don't duplicate context the task already carries.
2. **`task_search`** — prior/sibling tasks touching the same subject. Cheapest, highest hit rate
   for "has this been asked before."
3. **`search`** — broader PKB (docs, specs, notes) for the same subject.
4. **`get_semantic_neighbors`** — catches conceptually related nodes that keyword search misses
   (paraphrased prior decisions, adjacent specs). Use when 2–3 return thin.
5. **`retrieve_memory`** — durable facts, standing preferences, past corrections
   (`memory/feedback_*`, `memory/project_*`) bearing on this class of work.
6. **`get_dependency_tree`** — only if a task id exists; known blocking/related work for
   `Dependencies`.

Skip a step the moment two consecutive steps return nothing new — that's a signal you've found the
frontier of what's known, not a reason to keep spending budget "just in case."

## Citation discipline

Every `Context` bullet names a **spot-checkable node id** — a task id, memory filename/slug, doc
path, or spec section (`[[name]]`). A downstream reader must be able to open exactly that thing and
verify the bullet, without re-searching. Examples:

- Good: "Retry bound is ~3 before escalation ([[two-layer-decomposition]], 'Known-thin')."
- Bad: "The docs say retries are capped." — which docs? Not spot-checkable, don't write it.

If a search returns nothing relevant, say so explicitly rather than omitting the attempt — "No
relevant prior task found (`task_search('dashboard graph')` — 0 hits)" is itself information the
downstream reader needs (it rules out "did nobody check").

## Standards vs. Dependencies — don't conflate

- `Standards` = obligations this _class_ of work carries (from the workflow-library index + project
  config) — e.g. "outbound-facing work requires human review before send," per
  `references/standards-sourcing.md`.
- `Dependencies` = concrete task ids this specific ask is blocked by or related to. Pull from
  `get_dependency_tree` and any explicit mentions in the gathered context — not from the standards
  library.
