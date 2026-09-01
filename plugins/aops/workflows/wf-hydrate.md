---
alias:
- wf-hydrate-wf-hydrate
- wf-hydrate
- wf_23a5a1c6
category: process
created: 2026-07-11T12:41:18.157008105+00:00
description: 'Select when composing a workflow whose executor lacks pre-assembled context and has PKB access to gather its own. Not a default first step: skip when context was already hydrated before the workflow was assembled, or when the executor has no PKB access — see the `hydrate` skill for the technique either way.'
id: wf-hydrate
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
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

## wf-hydrate — context assembly before work starts

**Not a required step within a workflow by default.** Hydration is a skill
(`plugins/aops/skills/hydrate/`), and it requires PKB access that not every executor has. The
normal case is that hydration already happened before the workflow was assembled — the composer
ran the hydrate skill and handed the executor pre-assembled context. Compose this step into a
workflow only where that did not happen: the executor lacks pre-assembled context **and** carries
PKB access to fetch its own.

## What this step does

When composed, gather the minimum context needed to do the work well and to make later review
possible without re-deriving it: the task's SSoT links, upstream decisions/premises that bear on
shape and worth, relevant PKB neighbors (duplicates, related specs, prior attempts — especially
retired ones whose lessons apply), and the `depends_on` chain the planner has already wired. This
folds in what used to be the standalone "premise gate": is this worth doing, does it fit the shape
of the larger design — judged here, not as a separate ceremony later.

## Output contract

The hydration handback must state:

- The SSoT/spec(s) consulted, with resolvable links.
- Any prior attempt or retired approach found and why this one differs (or "none found — searched X, Y").
- The premise judgment: worth doing / right shape, in one or two sentences — or, if judgment can't be made yet, the specific missing information and who/what resolves it.
- The concrete inputs the drafting step needs (files, prior art, constraints) that a downstream executor with a fresh context window would need restated.

Evidence-or-failure-reason: every claim of "checked X" names the resolving link; if no SSoT could be found or the premise is genuinely unclear, that is stated plainly, not papered over.

## When to include

Only where the executor lacks pre-assembled context and has PKB access to fetch its own — never as
a universal default. For low-stakes composed work it can collapse to a single sentence ("no
upstream decisions bear on this, proceeding"). For anything touching a ratified design, a framework
spec, or prior retired work, it must be explicit.

## Related
