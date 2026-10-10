---
title: Code task base
type: template
description: Alternative foundation for code-change tasks executed via /ida:pull -- build (test-first for code that executes), push and PR, then a fresh worker's strategic review ending in a verdict on the PR.
tags: [base, task, code, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.

## Stages

1. **Build** -- implement the acceptance criteria, full suite green at the end. Code that executes is built test-first: each behaviour's failing test captured before its code. Agent-facing instruction text -- e.g. an agent definition, skill, workflow template, rule, axiom, AGENTS.md or CLAUDE.md, or slash command -- is proved by a fresh agent's run that follows it, judged against the acceptance criteria, never by a test that asserts its wording. A spec is checked by review.
2. **Push and file the PR** -- push the branch and open a pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: tests, commits, or a run. Record the PR URL on the task and release it as `done`.
3. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
   - **Rejected** -- the approach is wrong, the PR is out of proportion to what the task asks (see the `proportionate` axiom), or it cannot be salvaged: close the PR with the review as the closing comment, and set the implementation task to `cancelled` with the reason.
   - **Extensive revisions** -- the PR is sound in direction but needs more than in-place fixes: file a fix follow-up task that names each required change and `depends_on` the review task, leave the PR open, and link the follow-up from the review.
   - **Handoff for review** -- the reviewer pushed fixes or modified code on the PR: post the review and changes to the PR, file an independent QA follow-up task that `depends_on` this review task so a fresh independent reviewer verifies the modified PR, leave the PR open, and release this review task as `partial`. A reviewer that changes code or pushes fixes must never merge or mark merge-ready.
   - **Mergeable** -- the review is clean with no reviewer code changes, checks are green, and GitHub reports the PR mergeable: post a merge recommendation on the PR citing the green checks and the review, and release the review task as `merge_ready`. Do not merge.

## Composition

Cut the chain after stage 2: stages 1--2 form one task; stage 3 is a second task that `depends_on` the first, so a fresh worker picks it up with no shared context.

## Output contract

- Stage 1--2 task: for code, tests with their red failure traces; for instruction text, the run that followed it; a green full-suite run, and the open PR with its URL on the task record.
- Stage 3 task: the review posted on the PR, any in-place fix commits, and one verdict carried out -- PR closed and implementation task `cancelled`, a fix follow-up task filed, a handoff follow-up task filed with the review task released as `partial`, or a merge recommendation posted with the review task released as `merge_ready`.

## When to include

Any task whose deliverable is a code change to a repository. Use in place of the general task base when the work should arrive as a reviewed PR rather than a finished artifact.
