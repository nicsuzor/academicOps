---
trigger: always_on
description: Follow the three-purpose edge taxonomy (serves/supports, needs, and markdown Pointers) without redundant edges.
---

## Three-Purpose Edge Taxonomy and Invariants

Task graph edges follow the Three-Purpose Edge Taxonomy per [`specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md`](../../specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md):

- **Single injection invariant**: Top-level deliverable tasks wire `serves` to priced targets; subtasks never carry redundant `serves` edges. Auxiliary tasks that directly reduce effort or raise success probability wire `supports` (forbidden for tracking tasks).
- **Prerequisites use `needs`**: Upward execution gating is declared exclusively via `needs: [<task_id>]`.
- **Contextual references use `## Pointers`**: Soft references, cited documentation, and related artifacts live exclusively as markdown `[[wikilinks]]` in `## Pointers`. Duplicate frontmatter edges for body citations are prohibited.
