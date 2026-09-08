---
name: brief
description: Reify an expanded objective into dispatch-ready tasks by assembling workflow templates, defining task boundaries, and writing observable acceptance criteria. Never executes or dispatches.
---

# /brief -- Reify an objective into dispatch-ready tasks

Assemble workflow templates and prepare tasks for cold execution. The brief transfers intent, constraints, and criteria; the executor chooses implementation method.

## Instructions

0. **Task initialization**: If no task ID was provided, create one via `/q` using the provided description.
1. **Verify premises**: Re-verify world claims (paths, schemas, runtime states) before cementing them into constraints. Halt if a premise is invalid.
2. **Assemble workflow**: Select relevant templates across project (`$CWD/.agents/templates/`), universal (`./workflows/`), and PKB (`type: template`) tiers.
   - Read the templates and combine their steps into a logical order (e.g., failing tests first, implementation, then QA).
   - Base the assembly only on what is explicitly requested. Do not investigate, guess at scope, or ad-lib extra requirements. If the request is ambiguous, the brief must preserve that ambiguity.
3. **Determine task boundaries**:
   - Default to a single dispatchable unit for a single session, laying out the assembled workflow steps as a linear checklist.
   - Cut into separate tasks only when independent sessions are strictly required (e.g. forks, loops, independent reviews).
   - Wire `depends_on` edges only where one unit genuinely requires another's output. Mint multi-task cuts using `pkb__decompose_task`.
4. **Idempotency**: Search before creating new tasks. Update existing tasks with new criteria rather than minting duplicates.
5. **Write the brief**:
   Draft the body (budget 150-400 words) using this structure:

   ```markdown
   ## Goal -- numbered end-state outcomes

   ## Context -- user ask, unfetchable facts, exact identifiers

   ## Deliverable -- target artifact and destination path

   ## Scope -- boundaries and explicit exclusions

   ## Constraints -- fixed decisions and external requirements

   ## Acceptance criteria -- 3-7 observable, checkable end-states

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
