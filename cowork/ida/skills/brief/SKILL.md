---
name: brief
description: Reify an expanded objective into dispatch-ready tasks by assembling workflow templates, defining task boundaries, and writing observable acceptance criteria. Never executes or dispatches.
---

# /brief -- Reify an objective into dispatch-ready tasks

Assemble workflow templates and prepare tasks for cold execution. The brief transfers intent, constraints, and criteria; the executor chooses implementation method.

## Instructions

0. **Task initialization**: If no task ID was provided, create one via `/q` using the provided description.
1. **Verify premises**: Re-verify world claims (paths, schemas, runtime states) before cementing them into constraints. Halt if a premise is invalid.
2. **Assemble workflow**: Select relevant templates across project (`$CWD/.agents/templates/`), universal (`../workflow-library/workflows/`, resolved relative to this skill's own directory), and PKB (`type: template`) tiers. Halt if a required process component is missing.
3. **Determine task boundaries**: one node type -- tasks nest. A leaf (no children) is what gets dispatched: one worker, one go. A parent is never dispatched.
   - Default to a single dispatchable leaf, embedding workflow steps as internal checklist items.
   - Cut into separate leaves only when independent sessions are strictly required (e.g. forks, loops, independent reviews).
   - Wire `depends_on` edges only where one unit genuinely requires another's output. Mint multi-task cuts using `pkb.decompose_task`.
   - **Any obligation that must not run in the session that did the work becomes its own sibling leaf**, wired `depends_on` the work it checks -- review, visual assessment, independent verification, merge. A worker cannot be trusted to check its own output in the same pass, so the ordering belongs on the graph, not in a prompt. Steps the same worker performs in one session stay checklist items on the body.
   - **Name the obligation and its evidence, never the agent**: "get this visually assessed and show me proof", not "marsha reviews it". Which lens the worker invokes to satisfy the criterion is the worker's choice.
4. **Idempotency**: Search before creating new tasks. Update existing tasks with new criteria rather than minting duplicates.
5. **Write the brief**:
   Draft the body (budget 150-400 words) using this structure:

   ```markdown
   ## Goal -- numbered end-state outcomes

   ## Context -- user ask, unfetchable facts, exact identifiers

   ## Deliverable -- target artifact and destination path

   ## Acceptance criteria -- 3-7 observable, checkable end-states

   ## Scope -- boundaries and explicit exclusions

   ## Constraints -- fixed decisions and external requirements

   ## Assumptions / Decisions -- recorded calls and open trade-offs

   ## Required reading -- [[id]] references with functional rationale
   ```

6. **Finalize**: Ensure all dependency edges are connected and set task status to `ready`.

## Exclusions

- Omit execution methods, command scripts, or implementation hints.
- Omit summaries of linked notes; reference documents by pointer.
- Omit provenance, changelogs, session narratives, and perishable counts or SHAs.
- Do not create standalone decision tasks or file questions as tasks.
- Do not dispatch workers or begin execution.
