---
alias:
- wf-hydrate-wf-hydrate
- wf-hydrate
created: 2026-07-11T12:41:18.157008105+00:00
id: wf_23a5a1c6
last_modified: 2026-07-28T03:01:21.921103855+00:00
modified: 2026-07-28T03:01:21.921102002+00:00
permalink: wf-hydrate
tags:
- wf-template
- v0.4
- module-f
- workflow
- planner-data
title: wf-hydrate
type: template
---

## wf-hydrate — step: context assembly before work starts

**Sequence position**: step 1. Everything downstream depends on this being done honestly.

## What this step does

Before an executor drafts anything, gather the minimum context needed to do the work well and to make later review possible without re-deriving it: the task's SSoT links, upstream decisions/premises that bear on shape and worth, relevant PKB neighbors (duplicates, related specs, prior attempts — especially retired ones whose lessons apply), and the `depends_on` chain the planner has already wired. This folds in what used to be the standalone "premise gate": is this worth doing, does it fit the shape of the larger design — judged at planning/decomposition time, not as a separate ceremony later (see [[note_296e5520]] §2, pauli lens).

## Output contract

The hydration handback must state:

- The SSoT/spec(s) consulted, with resolvable links.
- Any prior attempt or retired approach found and why this one differs (or "none found — searched X, Y").
- The premise judgment: worth doing / right shape, in one or two sentences — or, if judgment can't be made yet, the specific missing information and who/what resolves it.
- The concrete inputs the drafting step needs (files, prior art, constraints) that a downstream executor with a fresh context window would need restated.

Evidence-or-failure-reason: every claim of "checked X" names the resolving link; if no SSoT could be found or the premise is genuinely unclear, that is stated plainly, not papered over.

## When to include

Always — this is the cheapest step and every other step depends on it being done honestly. For trivial low-stakes work (a one-line email reply, a routine data refresh) it can collapse to a single sentence ("no upstream decisions bear on this, proceeding"). For anything touching a ratified design, a framework spec, or prior retired work, it must be explicit.

## Related

- [[note_296e5520]] — SSoT, §2 (pauli premise lens folded into decomposition)
- [[wf_635eab64]] — next step, consumes this step's inputs
