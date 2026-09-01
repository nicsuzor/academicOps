---
alias:
- wf-refine-loop
- wf-refine-loop-wf-refine-loop
- wf_refine_6ef85da2
category: process
created: 2026-07-11T12:41:48.354403488+00:00
description: Generic outer-loop contract — iterate a body of work as separately dispatched tasks until a stated exit condition holds, with the checker owning the go-again decision. Select when work must repeat with a fresh workspace each round and someone must judge whether another round is needed. Not for a single build-then-check pass, and not standalone — compose it with a wf-loop-<type> sub-template that supplies the body and the condition.
id: wf-loop
last_modified: 2026-09-01T00:00:00.000000000+00:00
modified: 2026-09-01T00:00:00.000000000+00:00
permalink: wf-loop
status: ready
tags:
- wf-template
- workflow
- module-f
- loop
- process
- outer-loop
title: wf-loop
type: template
---

# wf-loop — generic outer loop

**Sequence position**: composable outer wrapper. Holds two open slots — a body and a checker — filled by a `wf-loop-<type>` sub-template.

## What this step does

Repeats a body of work until a stated condition is satisfied. This template owns the loop and nothing else: how iterations are created, how the exit is decided, and who decides it. What the body produces and what "good" means are supplied by the sub-template that composes it.

## Obligations

### 1. The body runs as separate tasks, never inline

Every unit of work inside the loop is created as its own task with its own assignee and its own fresh workspace. The agent running the loop creates tasks and reads their results; it performs no body work itself, in any iteration.

Iteration N+1 starts cold. State crosses between rounds only through the artifact and the checker's recorded findings, so each round is judged on what the artifact actually says rather than on context held by an agent that already argued for it.

### 2. The exit condition is stated at composition time

A loop is not composable until whoever composes it writes down, in the loop's own task:

- **The acceptance requirements** the checker evaluates each iteration.
- **The exit condition** — what makes the answer "stop", stated so a cold checker can decide it without asking.
- **The bound** — an iteration cap and what happens on reaching it, which is escalation to a human with the unresolved question named, never a silent pass.

A loop composed without all three is incomplete; return it for the missing condition rather than improvising one.

### 3. The checker owns the branch

The final task of each iteration is a check against the stated acceptance requirements. The agent holding that task is responsible for acting on its own verdict, not merely reporting it:

- **Exit** — record the verdict, satisfied acceptance requirements cited, and close the loop.
- **Go again** — reset the status of the prior step that must be redone, and create a new check task that `depends_on` that reset step. The checker's findings are attached to the reset step so the next executor inherits them.

The checker creates the next round or the loop ends. No other agent restarts it, and a "needs work" verdict that leaves no reset step and no new check task is an incomplete handback.

## Handback contract

The loop's handback states: iterations run, the verdict that ended it, the exit condition or bound that was hit, and — if escalating — the specific unresolved question.

## Identity separation

Body and check are held by distinct assignees, wired at decomposition (`depends_on` from the check back to the body step) and attested by the checker each round. No mechanical gate enforces this; verdicts are agent judgment. If one agent is filling both roles because no second is available, the handback says so — an honest gap beats a fake pass.

## Sub-templates

Specific loop types are separate templates named `wf-loop-<type>`, each supplying a body, a checker, and acceptance requirements that slot into the contract above. A sub-template inherits every obligation here and may add to them; it may not relax them. Candidates include a drafter↔reviewer refine cycle (reviewer raises the highest-priority concern with a proposed fix, drafter resolves or overrides with a stated reason) and a visual screenshot→judge→revise cycle.

## When to include

Include when the work may need more than one pass and something must judge whether to go again. Skip it when a single build-then-check pass settles the question, or when the executor's own revise-and-resubmit is enough — wrapping low-stakes work in a loop costs a task graph and buys nothing.

## Related

- [[wf-qa]], [[wf-fact-check]] — checks that commonly fill the checker slot
- [[wf-qa-visual]], [[wf-tdd]] — existing loop-shaped workflows this contract generalises
- [[wf-signoff]] — where an exiting loop hands off
