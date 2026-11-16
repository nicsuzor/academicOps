---
id: wf-pr-merge-prep
title: "wf-pr-merge-prep"
type: template
category: process
description: Prepare an already-open PR for someone else's merge decision -- review it fully, fix what needs fixing, confirm it is actually green and reviewed, and write an honest summary into its own body. Select when a PR exists and needs readying for a principal's merge call. Not for authoring the PR's changes, not for a PR whose only reviewer is also its sole author (that is self-review, not this), and not a licence to merge it yourself.
tags:
  - wf-template
  - process
  - pr
  - release
  - aops
---

## What this covers

Getting one open PR from "exists" to "a principal can decide on it in one look" --
without deciding for them. Four obligations, run in order, on the PR as it
actually stands, not as it was last checked.

## Steps

1. **Review the constituent diff or consolidated description.** On a constituent `polecat/*` branch or standalone PR, read the full diff and run the three-lens review (strategic fit, compliance, quality); when a constituent branch targeting a shared feature branch (`bundle/<slug>`) passes, merge it directly into `bundle/<slug>` and immediately close any superseded donor PR with a link to the consolidated PR. On a consolidated feature-branch PR (`bundle/<slug>` -> `dev`) whose constituent branches already passed three-lens diff review, pre-approval review is a compliance description-only check ("is this stupid?") posting `## RBG Review: PASS` without re-reviewing every line of constituent code pre-approval; the full three-lens combined-diff review runs after the principal approves and the branch is rebased onto `dev`.

2. **Address what the review found.** Fix what can be fixed inside the branch's own
   diff or PR description (including scrubbing any internal IDs or trailers under `data-boundaries` and closing any straggler donor PRs). What can't be fixed here -- or shouldn't be, because it needs a call
   only the principal can make -- gets named, not silently dropped.

3. **Confirm green, against the world.** Query CI status directly (e.g.
   `gh pr checks`) -- a claim that it's green from an earlier
   pass, another node, or the PR author is not this. Where it isn't, that is
   itself a finding, not something to wait out. A draft PR is marked ready for
   review (`gh pr ready`) only after the independent check passes and its
   required pre-approval review (`## RBG Review: PASS` description check on a consolidated PR, or three-lens diff review on a standalone PR) is posted to the PR thread.
   Mergeability is not required before approval: do not rebase or resolve
   conflicts here; bringing the PR up to date with its base (`dev`), resolving
   conflicts, and running the full three-lens combined-diff review happens after the principal approves, just before merge.

4. **Write an honest summary into the PR's own body and prepare the one-at-a-time run-down.** Use the repo's PR
   template if it has one (fetch it, don't recall it); fill every section (`## Summary`, `## Approach`, `## Trade-offs`, `## Constituent Changes & Review Receipts`, `## Test Receipt`) with
   real content so the interactive agent can present ready PRs to the principal one at a time covering what it does, how it does it, and what to pay attention to. A summary is a defect report if the diff and the words
   disagree.

## Exit: hand it to the sign-off gate

Merging is a ship-type act -- carry the independent agent review findings and a
reasoned recommendation to the principal. A review by independent agents is
required and a proportionate review is selected, with verdicts posted to the PR.
This template never merges the PR itself; producing
material for someone else's decision is the deliverable, not the decision.

## Not for

- Writing the PR's changes -- this starts once a PR already exists.
- A PR where the reviewer is also its sole author. Route to whoever can review
  it independently, or say plainly that no independent reviewer exists.
- Skipping the sign-off gate because CI is green. Green is one of four
  obligations here, not a substitute for the other three.
