---
id: strategic-intake
name: strategic-intake-workflow
category: planning
bases: [base-task-tracking, base-memory-capture]
description: Place fragments in the planning hierarchy with connections and assumptions
permalink: workflows/strategic-intake
tags: [workflow, planning, strategy, fragments, intake]
version: 1.0.0
---

# Strategic Intake Workflow

**Purpose**: Receive fragments — ideas, constraints, connections, surprises — and place them in the planning hierarchy with appropriate links, assumptions, and enablements.

**When to invoke**: User says "I had an idea", "new constraint", "what if we...", "I just learned that...", or the strategy skill completes and the user is ready to place fragments operationally.

**Skill**: [[planning]] for decomposition patterns; [[strategy]] for upstream exploration if needed.

## Core Process

1. **Receive Fragment** — What's the idea, constraint, or connection? Don't demand completeness. Fragments are the input; coherence is the output over time.

2. **Search Before Placing** (P52) — Query PKB for existing related nodes. Use `mcp__pkb__search()` and `mcp__pkb__pkb_context()` to understand what already exists. Never create duplicates; link to or update existing nodes.

3. **Classify Level** — Where does this belong in the hierarchy?

   | Signal                            | Level       | Action                                   |
   | --------------------------------- | ----------- | ---------------------------------------- |
   | Desired future state, multi-month | **Goal**    | Create in `${ACA_DATA}/goals/`           |
   | Bounded effort toward a goal      | **Project** | Create in `${ACA_DATA}/projects/`        |
   | PR-sized verifiable unit          | **Epic**    | Create via PKB with parent project       |
   | Refinement of existing node       | **Update**  | Append to existing node                  |
   | Too vague to classify             | **Seed**    | Create with `status: seed`, link loosely |

4. **Place in Graph** — Create or update the node. Link to related nodes via wikilinks. Set appropriate status (`seed` for unexamined, `growing` for developing).

5. **Surface Assumptions** — What must be true for this fragment to matter? If non-obvious, note them explicitly. Assumptions are load-bearing hypotheses — if wrong, dependent work is invalid.

6. **Map Enablements** — Use `get_dependency_tree(id, direction='downstream')` to see what this unblocks. Use `pkb_trace()` to find connections to other active threads. Surface convergence points where multiple threads benefit from the same work.

7. **Propose Next** — Hand back to the user with: what changed, what's newly possible, and whether any existing assumptions need revisiting. If the fragment suggests an epic is ready for decomposition, offer to invoke the [[decompose]] workflow.

## Critical Rules

- **Place first, refine later.** Don't demand specification. A seed node with loose links is better than nothing.
- **Assumptions are first-class.** Every placement should consider: "what am I betting on?"
- **Read before write** (P52). Always search existing nodes before creating new ones.
- **Don't execute.** This workflow places and connects. Execution is downstream.
