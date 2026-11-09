---
status: "accepted"
date: 2026-11-09
decision-makers: ["framework-architect", "review-supervisor"]
---

# Distinguish PKB Graph Edge Purposes and Enforce Parsimony

## Context and Problem Statement

Following the initial deployment of the PKB flow model and three-relation graph architecture, agent task authoring suffered from an over-correction where link density became excessively dense (exemplified by tracking tasks adding frontmatter `supports` links to every item they track). Ambiguous instructions previously prohibited interconnections in body prose, causing agents to duplicate all contextual markdown citations as formal frontmatter edges with weights. Furthermore, tasks frequently authored redundant child-to-ancestor weight edges, and tracking tasks misclassified tracking as "supporting" the tasks they tracked. How should the framework distinguish edge purposes, eliminate redundant frontmatter wiring, formalize project hierarchy rules, and enforce strict semantics for `supports`?

## Considered Options

- Three-purpose edge model: weight flow (`serves`/`supports`), sequencing (`needs`), and structural clustering (body wikilinks) with strict `supports` semantics
- Universal frontmatter edges for all relationships (all citations converted to formal frontmatter links)
- Unconstrained agentic link creation without edge contracts or hierarchy constraints
- Mechanical graph linter scripts checking link density in target repositories

## Decision Outcome

Chosen option: "Three-purpose edge model: weight flow (`serves`/`supports`), sequencing (`needs`), and structural clustering (body wikilinks) with strict `supports` semantics", because:

1. It cleanly separates the three fundamental purposes of graph edges: (1) weight flow to targets, (2) execution sequencing via `needs`, and (3) structural clustering and human understanding via markdown body wikilinks.
2. It eliminates redundant frontmatter clutter: direct references in task bodies (`[[node_id]]`) already function as clustering and semantic interconnection edges in physics models and search; anything cited in the body does not need duplicate formal frontmatter edges.
3. It enforces hierarchy parsimony: weight links (`serves`) are pushed as far up the parent hierarchy as accurate (single injection at the deliverable level), and subtasks inherit value via closed-form induction without redundant child-to-ancestor weight links. Weight links go exclusively to targets; weight propagates to other nodes via real blocking (`needs`) and supporting (`supports`) tasks.
4. It tightens `supports` semantics: a tracking or coordination task does not support the tasks it tracks (tracking makes zero difference to the tracked task's difficulty or probability of success); tracking tasks serve the strategic target of user understanding and are confined to that target edge.
5. It clarifies weight requirements: target weight edges require probability and quantum; `needs` edges are Boolean execution gates requiring neither; `supports` requires weights when propagating value between tasks or to targets.

### Consequences

- Good, because graph link density is drastically simplified, eliminating noisy and redundant frontmatter links.
- Good, because body wikilinks provide natural clustering for visualization and search without bloating formal graph weight matrices.
- Good, because tracking tasks link cleanly to user understanding targets rather than polluting tracked task dependencies.
- Good, because flow valuation remains mathematically sound by preventing double-counting across parent-child hierarchies.
- Bad, because existing tasks carrying redundant frontmatter links or misapplied `supports` must be cleaned up during routine graph reconciliation.
