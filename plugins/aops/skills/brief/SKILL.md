---
name: brief
description: Reification -- work out the process a task runs under, cut it into dispatchable units, and write the brief and acceptance criteria that a cold executor is judged against. Never dispatches, never executes.
---

# /brief -- Reify an expanded objective into dispatch-ready tasks

Take the components an objective was expanded into, work out the process they run under, and materialise the result: a flat set of tasks a cold executor can act on and be judged against.

**A brief transfers only what the dispatcher has and the executor lacks.** You hold intent and strategic context; the executor holds method. Anything the executor can fetch, derive, or decide better itself stays out.

## Workflow

1. **Re-verify every premise you are about to write down.**
   The record is a claim, not a fact. Claims about intent do not decay; claims about the world -- paths, schemas, deployed states, every negative claim -- decay silently. Re-verify each one the brief will lean on **against the world, not another node**, before it becomes a constraint, criterion, or pointer. If a load-bearing premise is dead, the unit is not briefable: record what is no longer true and stop.

   Name the standard the unit will be judged against and where it lives. Record any requirement it reaches that the unit does not cover as a named gap -- never absorb it silently, never soften a criterion to fit.

2. **Work out the process this task runs under.**
   Enumerate the workflow components available -- project-local (`$CWD/.agents/templates/*.md`), plugin (`plugins/aops/workflows/*.md`), and personal knowledge base (`type: template`). Enumerate by running the command; never from memory, and never from an index alone.

   Read the ones that look relevant and work out how they go together for this task. Weight the process against real consequence: heavier is theatre, lighter is unmitigated risk. Where the work needs something no component supplies, name the gap and stop rather than freelancing a process.

3. **Sort the obligations by who discharges them.**
   Steps the executor performs become the task checklist. Anything that must block acceptance, and is discharged by someone other than the executor, becomes an acceptance criterion on the task body.

4. **Cut only at forks and boundaries.**
   Default: no cut. The dispatchable unit is the largest chunk containing no unresolved fork. Cut only where an unresolved fork sits inside the chunk, or the chunk spans a responsibility boundary -- a different owner, authority, or evaluator. **Never cut on size or feel.**

   Every cut carries its own owner and return contract: DONE with deliverable and evidence, BLOCKED with what is missing, NEEDS-REDISPATCH with what changed, or partial with a handback. A cut that cannot support that contract is cut wrong -- re-cut. Wire `depends_on` only where one unit's start genuinely needs another's output; everything else runs parallel.

   **Idempotency & Cleanup:** Before minting a new cut, check if a dispatchable unit covering the work already exists. If it does, **do not duplicate it**. Update the existing task with any necessary new information (like new acceptance criteria) and return the existing task. If you encounter any disorganisation, duplication, or structural graph issues, immediately consolidate (keep it DRY) and kick off to a structural cleanup skill like `reconcile` if appropriate.

   Where new cuts are genuinely needed, mint the cut with `pkb__decompose_task(parent_id=..., subtasks=[...])`, which writes it in one operation and resolves sibling dependencies by positional reference (`$1`, `$2`). Use slugged, human-readable IDs. An epic's child units ship together on one branch and one pull request, never scattered.

5. **Write the brief.**
   Rewrite the body to exactly this shape, deleting event logs, prior drafts, and inconsistent directions. Frontmatter, edges, and intake-stage valuation are preserved, not rewritten.

   ```markdown
   ## Goal -- every outcome the task must produce, numbered where there is more than one; the end state, never the method. Test: could a reviewer judge from this alone whether the result is the right kind of thing?

   ## Context -- the user's verbatim ask where its wording carries constraints or tolerances; unfetchable facts only, plus exact load-bearing values (an id, path, gate name) where a fetch error would be silent

   ## Deliverable -- one line: the artifact and where it lands

   ## Scope -- what is in; what adjacent thing is out (one clause per real collision risk, no rationale)

   ## Constraints -- decisions already taken, phrased as outcomes, each citing its home

   ## Acceptance criteria -- 3–7 observable end-states, each naming an artifact and a condition checkable by a stranger who never watched the work; only work THIS executor will do

   ## Assumptions / Decisions -- calls already made, and open calls awaiting the user; where non-empty

   ## Pointers -- [[id]] of a note or document the executor must open + ≤1 clause saying why ("the method", "precedent -- do not redo", "do-not-touch"), never what it says, never a task
   ```

   **Budget: 150–400 words; ~500 for a campaign plan. One screen.**

   Invoke the `craft` skill for the standard the brief must meet.

6. **Set the status and stop.**
   - Once a brief is written, change the task's status to **`briefed`**.
   - Any dependencies should be wired up fully at this stage. Ensure all edges are correct, including any blockers or dependencies that were discovered during the briefing process.

## Excluded from every brief

- **Method.** No instructions about the changes to make; the brief must not require or even suggest how the deliverable is achieved. Litmus: a line checkable only by watching the executor work is method -- delete it, or convert it to the end-state it was trying to guarantee.
- **Summaries of linked content.** Incorporate by reference, never by transcription.
- **Provenance, supersession narrative, session diary.** History lives in audit logs and commits.
- **Restated doctrine** the executor loads anyway.
- **Perishable facts** -- counts, SHAs, dates-as-state, other nodes' statuses. State the threshold; let the executor measure.
- **Meta-commentary** whose subject is the task itself -- how it was scoped, which stage it sits at, what it is not to be mistaken for, why it is worded this way.
- **Links to other tasks, and any prose about how this task relates to one.** That structure is already carried by the graph edges; a prose copy is a second source of truth that goes stale while the edge stays correct.
- **Pre-completed acceptance criteria.** The list is exactly what this executor is on the hook for.

Deletion test, per sentence: if this line vanished, would the executor act differently, or success be judged differently? If neither, delete it.

Your verification notes, the components you used and why, and the cut rationale go in your reply to the caller -- never in a task body.

## Must NOT

- Do not resolve a fork the work uncovers, or improvise a step to cover a gap.
- Do not originate `intent` or `priority` bands; strategic importance travels on `contributes_to` edges.
- Do not emit speculative review or sign-off nodes. Acceptance gates live in the criteria and at the merge boundary.
- Do not dispatch, and do not begin the work.
