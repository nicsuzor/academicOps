---
title: Trial a capability and critique it against its spec
type: template
category: process
description: Run the thing under test headless in its own container, then critique what came back against that thing's own specified objectives — select when the ask is "test X" or "see how X performs"; not for proving X works to a pass/fail bar, and not for changing X
tags: [dogfood, trial, blind-run, critique, spec, fragment]
---

## wf-trial-critique -- step: trial a capability, critique the result against its spec

**This is a fragment.** It is one step inside a composed workflow — the generic
half of "test X", which `brief` weaves together with the workflow specific to
whatever X is. Never dispatch it standalone: on its own it has no X, no spec,
and no next iteration to feed.

## When to select this

The ask is to find out **how something actually performs** — "test the
decompose skill", "see what the classifier does with real prompts", "run a
baseline before we change this". The deliverable is what the run established
plus a critique of the gap between that and what the thing is supposed to do.

Do not select this when:

- The bar is binary and the criteria are authored for this run — that is
  [[wf-blind-proof]], whose dispatcher writes and locks acceptance criteria the
  executor never sees. Here the yardstick pre-exists and belongs to X.
- The ask is to change X. A trial may precede a change and never substitutes
  for one.
- No specification of X's objectives exists. See obligation 1: that is a halt,
  not a reason to invent the yardstick.

## What this step obliges

1. **Fix the yardstick before the run, from a source that is not the run.**
   Locate and read X's specified objectives — spec, skill body, acceptance
   criteria, whatever formally states what X is for — and record where they
   live. Where no such statement exists, stop and say so: a critique with no
   independent standard grades the output against the critic's taste, and
   authoring the standard after seeing the output is indistinguishable from
   grading to fit.

2. **Run X on its own surface, in its own container, and do none of the work.**
   Headless, isolated, no shared state with the dispatcher, no coaching turn, no
   edit to the subject's tree. The surface named in the ask is part of what is
   under test: reaching a different one measures that one instead. Archive the
   executor's verbatim prompt and its raw output at run time — a reconstruction
   afterwards is not evidence. Dispatch mechanics are the `dispatch` and `debug`
   skills' job, not this template's.

3. **Establish what the artifact in front of you actually is before judging it.**
   Name the condition it came from — baseline or iteration N, which knobs were
   set, which model, which surface, whether it is a proposal or an output.
   A critique aimed at the wrong artifact class is wasted work no matter how
   sharp it is: a first-run baseline read as a considered design gets attacked
   for choices nobody made. This is cheap and it is skipped by default.

4. **Verify the output's own load-bearing claims against reality, then critique
   against the spec.** Every path, quote, identifier and world-claim the output
   rests on gets checked at its source before any reasoning built on it is
   judged — an argument that is sound over false premises fails differently from
   one that is unsound, and the two need different fixes. Then name defects
   against the spec's stated obligations, one at a time, citing the obligation
   each violates. Neither a pass nor a defect is recorded from an absence: where
   nothing observed discriminates the alternatives, record it undetermined.

5. **Summarise to a decision.** What the run establishes, what it does not, and
   the smallest set of choices that would change the next run — put to the user
   as choices, not as a plan already made. A halt, a refusal, or a run that
   could not proceed is a result and is reported as one.

Findings that outlive this run — a defect in X's instructions, a gap where no
rule existed — leave as evidence records per the `dogfood` skill. A finding that
exists only in this step's summary has not been filed.

## Exit

The spec used is named and was read before the run; the executor's verbatim
prompt and raw output are archived; the artifact's condition is stated; every
load-bearing claim is either verified, falsified, or marked unverified; each
defect cites the obligation it breaches; and the user has an explicit decision
in front of them.
