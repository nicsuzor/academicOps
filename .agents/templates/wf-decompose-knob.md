---
title: Trial the /decompose reconnaissance knob
type: template
category: process
description: Run and critique one iteration of the /decompose effort knob — the subject-specific half of "test the decompose knob", composed with wf-trial-critique; select when trialling or iterating the knob, not when trialling /decompose without it and not when implementing the knob for real
tags: [decompose, knob, trial, dogfood, iteration]
---

## wf-decompose-knob -- trial one iteration of the /decompose effort knob

The subject-specific half of "test X" where X is `/decompose` carrying an effort
knob. It names what is under test, which yardsticks it is judged against, and
what each iteration must clear. [[wf-trial-critique]] supplies the run-and-
critique method; this template supplies the subject. Compose both or neither.

## When to select this

An iteration of the knob is due: a new candidate wording, a changed setting
scale, or the next turn of the loop after a critique. Do not select this when
the ask is to trial `/decompose` as it stands with no knob (that is
[[wf-trial-critique]] against `plugins/aops/skills/decompose/SKILL.md` alone),
or to implement the knob in the shipped skill, which is a change and follows a
change's process.

## What is under test

**One knob, on one axis: how far from the prompt the expansion reads before it
expands.** It bounds step 1 reconnaissance, and every other rigour behaviour is
a consequence of that bound, never a second setting. Three settings, each a
superset of the one below:

- `glance` -- read only what the prompt names.
- `survey` -- read what the prompt names and its immediate neighbours; verify
  the load-bearing world-claims.
- `canvass` -- the full parallel fan-out step 1 already describes, across
  codebase, graph, history and runtime; verify every world-claim against
  reality.

What scales with the setting: whether alternatives are forked or decided, whether
a component splits into its decision and its validation, whether an unknown mints
a probe or is settled in a bullet, and how densely the expansion wikilinks what
it confirmed by opening.

**No node counts, at any setting.** Not a cap, not a floor, not a range, not a
depth limit. Step 3 already bounds the expansion at the limit of reliable
inference; a count makes the run stop short of that limit or pad to reach it,
and either way the number, not the objective, decides the shape.

**The setting is inferred, never required.** The run reads the prompt, picks the
setting the ask implies, and states which it picked and why before any expansion
appears, so an unset value still works and a wrong inference can be interrupted.
An explicitly supplied setting overrides the inference. The statement goes in
the reply to the caller, never into a task body.

## Yardsticks

Both pre-exist and neither is authored for the run:

- `plugins/aops/skills/decompose/SKILL.md` -- graph integrity: the SURFACE and
  DECIDE/DEFER rules of step 4, the wiring rules of step 5, the body shape of
  step 6.
- `.agents/skills/dogfood/references/decomposition-eval.md` -- whether the
  critical-thinking dimensions surface at all, and its method constraints, which
  bind this loop as much as the output.

## Carried defects

Open against the no-knob baseline and unfixed. Each is a wiring fault, not a
gold-standard mismatch, so checking them contaminates nothing. A run that
reproduces one has not improved on the baseline whatever else it did:

1. **A fork whose branches are not exclusive.** The baseline forked a CLI
   wrapper against a skill extension and declared them mutually exclusive, but
   adopting either leaves the other still worth building. Step 4 SURFACE admits
   only options where choosing one cancels the competing one; anything else is a
   DECIDE or two ordinary siblings.
2. **A setting name that collides.** The baseline reused `seedling`, which
   `specs/workflows/research-decomposition.md:39` already binds to research
   programme maturity on a different axis, while citing that very file as a
   known fragment.
3. **A probe hard-blocking work its own assumptions table rates High.** The
   baseline gated prompt authoring on a mid-tier probe. Step 5's test decides
   hard from soft: if the probe never lands, prompt authoring is less informed,
   not impossible, so the edge is `soft_depends_on`, and step 4 forbids
   manufacturing a roadblock where minimal effort settles the question.
4. **A scoring node with no successor.** The baseline's convergence node emits
   rubric scores that nothing consumes, and excludes remediation in its own
   `## Not included`. Step 5 requires judgment-only work be wired forward to an
   explicit follow-up node or owner.

## Loop constraints

These bind the iteration, not the output, and the baseline loop breaks both:

- **Keep the prior attempt out of reach.** Storing a run's output beside its
  prompt where the next executor can search costs the next run its blindness.
  The prompt-and-output pair lives somewhere the executor cannot read, per the
  rubric's fresh-pairs rule.
- **Two runs per condition, minimum.** One run per iteration cannot separate the
  knob's effect from agent variance, so no single run is evidence that a change
  to the wording worked.

## Exit

The setting scale under test is stated and collides with nothing; the run
announced its inferred setting before expanding; no output at any setting names
a node count; all four carried defects are checked and each is cleared or
recorded as reproduced with the obligation it breaches; both loop constraints
held; and the smallest set of changes for the next iteration is in front of the
user as choices, with the loop's own continuation among them.
