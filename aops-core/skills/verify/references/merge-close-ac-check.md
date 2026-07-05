# AC-Verification Step (merge_ready → done)

The verification surface that sits on the `merge_ready → done` transition. Source: nicsuzor/academicOps#1426 — before this step existed, every auto-close path confirmed only that a PR _corresponds_ to a task ("is this the right PR?"), never that the task's **acceptance criteria are actually satisfied by the merged artifact**. Judgment-laden criteria — taste, "is X genuinely good", "does this serve the user" — passed the correspondence check and shipped to `done` silently.

This step closes that gap. It is invoked by every surface that auto-closes a task on a merged PR (`/daily` Task Completion Sweep, `/sleep` PR-state sweep). It does **not** define a new lifecycle state and does **not** introduce a blocking gate — per framework doctrine it _surfaces_ unverified criteria rather than halting the pipeline.

## Precondition

Run this **after** PR↔task correspondence is confirmed (the candidate PR genuinely belongs to this task) and **before** calling `complete_task`. Correspondence answers "is this the right PR?"; this step answers "are the task's acceptance criteria met by what actually merged?". Both must hold to auto-close.

## The step

1. **Re-read the task's acceptance criteria.** Take the AC list from the task body verbatim — not the PR description's self-report of what it did. If the task has no explicit AC, fall back to the task's stated intent/deliverable.

2. **Read the merged artifact.** The merged PR diff (or final file state on the default branch) is the evidence, not the PR's prose summary. A PR that _claims_ to satisfy an AC is not evidence the AC is satisfied — see [[../SKILL.md#data-pipeline-verification]] ("is this the RIGHT data?", not "does data appear?").

3. **Classify each criterion** (reuse the bar classification from [[../SKILL.md]] "Classify the bar before you start"):
   - **Mechanical AC** — verifiable from the diff/artifact without taste (a file exists, a test was added, a function was renamed at all callsites, a flag was removed). Judge it directly against the merged code.
   - **Judgment-laden AC** — fitness-for-purpose language: adjectives of experience ("intuitive", "clear", "robust"), "is X _actually_ satisfied", "serves the user", anything where two reasonable reviewers could disagree on PASS/FAIL with the same diff in front of them.

4. **Judge each criterion against the artifact and route on the result:**

   | Result                                                   | Action                                                                                                                                                                                                  |
   | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | All ACs mechanical **and** all clearly met by the diff   | Auto-close: `complete_task` with the PR URL + merge timestamp as evidence.                                                                                                                              |
   | One or more **mechanical** ACs not evidenced in the diff | Do **not** auto-close. Surface to "Needs your call" naming the unmet AC.                                                                                                                                |
   | One or more **judgment-laden** ACs                       | Do **not** silently auto-close on them. Surface to "Needs your call" naming each judgment-laden AC and quoting it verbatim, so a human (or an explicit `/verify` dispatch) renders the fitness verdict. |

5. **Surface, do not block.** Surfacing means recording the task under "Needs your call" in the daily note / cycle summary with the PR link and the specific criterion text. The task stays in `merge_ready` (work is merged; only the _verification_ is outstanding). Nothing in the merge pipeline is halted, no CI is failed, no gate is added. The human decides: accept-and-close, or open follow-up work.

## Why surface and not block

Doctrine forbids a new blocking gate on this transition (#1426 explicitly: "without adding a new blocking gate where doctrine forbids it"). The merged work is already on the default branch — blocking the _status_ transition would not un-merge anything; it would only strand the task. The honest move is to let the work land and make the **unverified judgment-laden criterion visible** to the person who can judge it, instead of laundering it into `done` on the strength of a correspondence match.

## What this is not

- Not a re-run of pre-merge review (rbg/marsha on the open PR). That already happened upstream. This is the **post-merge** check that the _task's own ACs_ — which the pre-merge review may never have read — are satisfied by what landed.
- Not a CI check, not a hook, not a script. It is agent judgment at the close surface, consistent with the "trust agents, no bespoke closure scripts" stance of the reconcile spec.
- Not a completeness audit of verification _subtasks_ (that is `/sleep` Activity 4b). This judges the **content** ACs against the **artifact**.
