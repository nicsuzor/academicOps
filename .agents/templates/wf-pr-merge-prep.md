---
id: wf-pr-merge-prep
title: "wf-pr-merge-prep"
type: template
category: process
description: Prepare an already-open PR for someone else's merge decision -- review it fully, fix what needs fixing, confirm it is actually green and mergeable, and write an honest summary into its own body. Select when a PR exists and needs readying for a principal's merge call. Not for authoring the PR's changes, not for a PR whose only reviewer is also its sole author (that is self-review, not this), and not a licence to merge it yourself.
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

1. **Review the diff in full.** Read what changed, not the PR's account of what
   changed. Note every concern -- correctness, scope creep, missed cases,
   anything that would surprise the principal later.

2. **Address what the review found.** Fix what can be fixed inside the PR's own
   diff. What can't be fixed here -- or shouldn't be, because it needs a call
   only the principal can make -- gets named, not silently dropped.

3. **Confirm green and mergeable, against the world.** Query CI and merge
   status directly (e.g. `gh pr checks`, `gh pr view --json
   mergeable,mergeStateStatus`) -- a claim that it's green from an earlier
   pass, another node, or the PR author is not this. Where it isn't, that is
   itself a finding, not something to wait out.

4. **Write an honest summary into the PR's own body.** Use the repo's PR
   template if it has one (fetch it, don't recall it); fill every section with
   real content. A summary is a defect report if the diff and the words
   disagree.

## Exit: hand it to the sign-off gate

This template ends where [[wf-signoff-loop]] begins. Merging is a ship-type
act -- compose that gate to carry the review's findings and a recommendation
to the principal. This template never merges the PR itself; producing
material for someone else's decision is the deliverable, not the decision.

## Not for

- Writing the PR's changes -- this starts once a PR already exists.
- A PR where the reviewer is also its sole author. Route to whoever can review
  it independently, or say plainly that no independent reviewer exists.
- Skipping the sign-off gate because CI is green. Green is one of four
  obligations here, not a substitute for the other three.
