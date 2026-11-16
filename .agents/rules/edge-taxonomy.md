---
trigger: always_on
description: Follow the three-purpose edge taxonomy (serves, needs, and markdown Pointers) with component-level single injection and zero leaf serves edges.
---

## Three-Purpose Edge Taxonomy and Invariants

Task graph edges follow the Three-Purpose Edge Taxonomy per [`specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md`](../../specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md):

- **Single injection invariant (Component-Weighting & Leaf-Inheritance Rule)**: Strategic Value Carriers -- enduring component/subsystem epics, multi-session initiative epics, and standalone major deliverables (freestanding commitments to external stakeholders belonging to no component or initiative epic) -- wire `serves` weight-flow links strictly to priced `target` nodes (never task-to-epic), priced at their full holistic weight (never as a remainder after child tasks). Child tasks, bugfixes, and subtasks carry zero `serves` edges and inherit worth via `parent` or `needs`. `supports` is retired.
- **Prerequisites use `needs`**: Upward execution gating is declared exclusively via `needs: [<task_id>]`.
- **Contextual references use `## Pointers`**: Soft references, cited documentation, and related artifacts live exclusively as markdown `[[wikilinks]]` in `## Pointers`. Duplicate frontmatter edges for body citations are prohibited.
