---
title: Doc task base
type: template
description: Foundation for tasks that change instruction text, docs or specs in a repository, executed via /ida:pull -- write the change with no tests, prove instruction text by a fresh agent's run and specs and docs by review, push and PR, then a fresh worker's review ending in a verdict on the PR.
tags: [base, task, docs, instructions, spec, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.

## Stages

1. **Write and prove** -- make the change to meet the acceptance criteria. Write no tests for it, and never a test that asserts its wording. Agent-facing instruction text -- e.g. an agent definition, skill, workflow template, rule, axiom, AGENTS.md or CLAUDE.md, or slash command -- is proved by a fresh agent's run that follows it, judged against the acceptance criteria. A spec or doc is checked by review against the project's own standard for it.
2. **Push and file the PR** -- push the branch and open or update the pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: the run, the review, or the commit. If the PR was opened as a draft, mark it ready for review as soon as its code step completes, without waiting for approval. Record the PR URL on the task and release it as `done`.
3. **Review and verdict** -- in a separate task, by a fresh worker that did not write the change. The review task draws its brief from the shared review briefing in `wf-review` (quoting the originating request verbatim with its source ID before the PR). Review the PR against the acceptance criteria and the project's rules, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict: **rejected** (close the PR with the review, set the task `cancelled` with the reason, and release the review task as `failed`); **revisions needed** (the review fails, criteria are unmet, or the PR needs more than in-place fixes: post the review to the PR, do not file fix tasks or follow-up tasks, and release the review task as `failed` with documented root cause; the reconcile pass notes failed tasks and decides next actions from the parent epic); **handoff for review** (the reviewer changed the PR: leave the PR open, release this one as `partial` with explanation on record; reviewers never file follow-up tasks); or **reviewed / ready for decision** (clean review, no reviewer changes, checks green: post a merge recommendation with the link to the posted review and CI status receipts, and release as `done`; mergeability against base is not required before approval). Do not merge.

## Composition

Structure documentation and instruction workflows per the follow-up placement invariant: as a single task with internal subtasks when executable by the same agent in one session, or as a dedicated epic with child tasks (Child 1: Stages 1--2 Drafting and Proof, Child 2: Stage 3 Review, with `needs: [<child_1_id>]`), never as loose siblings under an external parent. A minor docs repair or trivial chore omits stage 3.

Where the same change also alters code that executes, that code is built and tested on its own terms, and both parts arrive in one PR.

## Output contract

- Stage 1--2 task: for instruction text, the run that followed it; for a spec or doc, the review; and the open PR with its URL on the task record.
- Stage 3 task: the review posted on the PR, any in-place fix commits, and one verdict carried out.

## When to include

Any task whose deliverable is a change to instruction text, docs or specs in a repository, arriving as a reviewed PR.
