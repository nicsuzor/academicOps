---
status: "accepted"
date: 2026-11-09
decision-makers: ["framework-architect", "review-supervisor"]
---

# Distinguish PKB Graph Edge Purposes and Enforce Parsimony

## Context and Problem Statement

Following the initial deployment of the PKB flow model and three-relation graph architecture, agent task authoring suffered from an over-correction where link density became excessively dense (exemplified by tracking tasks adding frontmatter `supports` links to every item they track). Ambiguous instructions previously prohibited interconnections in body prose, causing agents to duplicate all contextual markdown citations as formal frontmatter edges with weights. Furthermore, tasks frequently authored redundant child-to-ancestor weight edges or wired leaf bugfixes directly to targets, and tracking tasks misclassified tracking as "supporting" the tasks they tracked. How should the framework distinguish edge purposes, eliminate redundant frontmatter wiring, formalize component-weighted hierarchy rules with zero leaf `serves` edges, and retire `supports`?

## Considered Options

- Three-purpose edge model: weight flow (`serves`), sequencing (`needs`), and structural clustering (body wikilinks) with single-injection component weighting
- Universal frontmatter edges for all relationships (all citations converted to formal frontmatter links)
- Unconstrained agentic link creation without edge contracts or hierarchy constraints
- Mechanical graph linter scripts checking link density in target repositories

## Decision Outcome

Chosen option: "Three-purpose edge model: weight flow (`serves`), sequencing (`needs`), and structural clustering (body wikilinks) with single-injection component weighting", because:

1. It cleanly separates the three fundamental purposes of graph edges: (1) weight flow to targets (`serves`), (2) execution sequencing via `needs`, and (3) structural clustering and human understanding via markdown body wikilinks.
2. It eliminates redundant frontmatter clutter: direct references in task bodies (`[[node_id]]`) already function as clustering and semantic interconnection edges in physics models and search; anything cited in the body does not need duplicate formal frontmatter edges.
3. It enforces hierarchy parsimony (Component-Weighting & Leaf-Inheritance Rule): weight links (`serves`) point strictly to `type: target` nodes (never task-to-epic) and sit exclusively on Strategic Value Carriers -- enduring component/subsystem epics, multi-session initiative epics, and standalone major deliverables (freestanding commitments to external stakeholders belonging to no component or initiative epic) -- priced at their full holistic weight (never as a remainder after child tasks). Child tasks, bugfixes, and subtasks carry zero `serves` edges and inherit worth via closed-form backward induction over `parent` and `needs`.
4. It retires `supports` / `soft_depends_on` and enforces tracking-task boundaries: soft contextual references use markdown `[[wikilinks]]` under `## Pointers`, and a tracking or coordination task never wires frontmatter edges to the tasks it tracks (tracking makes zero difference to the tracked task's difficulty or probability of success; standalone valued tracking initiatives serve user understanding targets directly).
5. It clarifies weight requirements: target weight edges (`serves`) require probability and quantum; `needs` edges are Boolean execution gates requiring neither.

### Consequences

- Good, because graph link density is drastically simplified, eliminating noisy and redundant frontmatter links.
- Good, because body wikilinks provide natural clustering for visualization and search without bloating formal graph weight matrices.
- Good, because tracking tasks link cleanly to user understanding targets rather than polluting tracked task dependencies.
- Good, because flow valuation remains mathematically sound by preventing double-counting across parent-child hierarchies.
- Bad, because existing tasks carrying redundant frontmatter links or misapplied `supports` must be cleaned up during routine graph reconciliation.
