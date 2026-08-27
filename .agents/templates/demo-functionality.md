---
title: Live framework demonstration
type: template
kind: process
category: framework
description: Show a named part of the framework actually working, on live state, narrating each step and displaying real output — select when the ask is "show me how X works"; not for explaining X, and not for changing it
tags: [demo, dogfood, framework, walkthrough, read-only]
---

# Demonstrate a framework mechanism, live

## When to select this

The ask is to **see a mechanism work**, not to read about it: "show me how X
works", "demonstrate the dispatch path", "walk me through composition". The
deliverable is a narrated run against real state plus whatever the run exposed.

**Do not select this when:**

- The ask is answerable in prose — that is `simple-question`. A demo that could
  have been a paragraph wastes the reader's attention, which is the scarcest
  input here.
- The ask is to change the mechanism — that is `framework-gate`, then whatever
  it routes to. A demo may *precede* a change; it never substitutes for one.
- The mechanism cannot be run for real right now. Say so and stop. A narrated
  walkthrough of what *would* happen is the failure mode this template exists
  to prevent, and it is indistinguishable from a real run in the transcript.

## What this process obliges

1. **Name the target before starting.** One mechanism, stated as a claim that
   can fail — "composition resolves project ≻ PKB ≻ universal", not "the
   workflow library". A demo without a falsifiable target cannot fail, and a
   demonstration that cannot fail is not evidence.

2. **Run it live. Every step is executed, none is narrated from memory.**
   Every command, tool call, node id and file path shown must have actually
   been issued in this session. No illustrative output, no reconstructed
   examples, no "it would return something like".

3. **Cite the source of each behaviour shown**, as `file:line`, a node id, or a
   tier name. The reader must be able to check the demo without re-running it.

4. **Narrate in three beats per step: what is about to happen and why → the
   action → the observed result.** State the expectation *before* the result is
   visible. Retro-fitting a prediction to an outcome is the cheapest way to make
   a broken mechanism look correct.

5. **Show at least one boundary.** Something the mechanism does *not* do, or a
   case where it declines. A demo made only of confirmations teaches the shape
   of the happy path and nothing about where it ends — and cannot detect drift,
   because drift lives at the edges.

6. **Read-only by default.** Announce any write before it happens, name what it
   touches, and prefer a reversible one. State whether the demo ran against live
   state or a copy — a mechanism demonstrated on a container clone has been
   demonstrated on a copy, and for anything whose point is live state that is a
   different claim.

7. **A discrepancy is the primary find, not an interruption.** Where observed
   behaviour differs from documented behaviour, that gap is the most valuable
   output of the run. Show it, do not smooth it, and file it as its own node
   before reporting.

## Exit criteria

- Every step shown was executed, and its output is the real output.
- The stated target claim was tested and its verdict — held, failed, or could
  not be tested — is stated plainly.
- At least one boundary or negative case was exercised.
- The reader can state the mechanism's inputs, its decision rule, and one thing
  it will not do.
- Any discrepancy found exists as a filed node, not only as prose in the
  transcript. A demo whose findings live only in chat has no re-surface path.

## Must not

- Present example, expected, or reconstructed output as observed output.
- Skip a step and describe it, however mechanical it looks. The skipped step is
  where the drift is.
- Repair the mechanism mid-demo. Finding a defect ends the demo's read-only
  contract; file it and route it, do not fix it in place.
- Leave the demonstration as the sole record of anything it discovered.
