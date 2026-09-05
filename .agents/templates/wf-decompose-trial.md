---
title: Trial /decompose against its own spec
type: template
category: process
description: Run one blind iteration of /decompose and critique what comes back — the subject-specific half of "test the decompose skill", composed with wf-trial-critique; select when trialling or iterating /decompose itself, not when using it to plan real work and not when changing it
tags: [decompose, trial, dogfood, iteration]
---

## wf-decompose-trial -- run and critique one iteration of /decompose

The subject-specific half of "test X" where X is `/decompose`. It names the
yardsticks, what each iteration must clear, and how the loop closes.
[[wf-trial-critique]] supplies the run-and-critique method; this template
supplies the subject. Compose both or neither.

## When to select this

An iteration is due: a changed wording in the skill, or the next turn of the
loop after a critique. Do not select this when `/decompose` is being used to
plan real work rather than being tested, or when the ask is to change the skill,
which is a change and follows a change's process.

## How much care

One level, and it is the level below. Effort is not a parameter on `/decompose`
and no run of this template sets one: how much rigour a piece of work gets is
already decided by which templates and gates `brief` composes for it, per
`aops-composable-workflow-system` §3. A proposal to fix review depth in a table
rather than compose it per task is settled ground and the settlement was against.

The care this template obliges: two runs, blind, with the executor's verbatim
prompt and raw output kept; every load-bearing claim in the output checked at
its source; the carried defects below checked by name; and the result put in
front of the user, who decides whether it is sufficient rather than being asked
to pick from options.

## Yardsticks

Both pre-exist and neither is authored for the run:

- `plugins/aops/skills/decompose/SKILL.md` -- graph integrity: the SURFACE and
  DECIDE/DEFER rules of step 4, the wiring rules of step 5, the body shape of
  step 6.
- `.agents/skills/dogfood/references/decomposition-eval.md` -- whether the
  critical-thinking dimensions surface at all, and its method constraints, which
  bind this loop as much as they bind the output.

## Carried defects

Open against the last run and unfixed. Each is a wiring or premise fault, not a
gold-standard mismatch, so checking them by name contaminates nothing. A run
that reproduces one has not improved on its predecessor whatever else it did:

1. **A parameter table where composition already decides.** The last run
   answered "let me set the standard and the effort" by inventing two settings
   scales expressed as node counts (`Max 4 tasks total`, `Produce 6-12
   components`). Counts make a run stop short of step 3's limit of reliable
   inference or pad to reach it, so the number decides the shape instead of the
   objective; and fixing depth in a table is ground already settled the other
   way. The correct answer to that ask is which templates and gates get composed.
2. **A fork whose branches are not exclusive.** A CLI wrapper was forked against
   a skill extension and declared mutually exclusive, but adopting either leaves
   the other still worth building. Step 4 SURFACE admits only options where
   choosing one cancels the competing one; anything else is a DECIDE or two
   ordinary siblings.
3. **A name that collides.** `seedling` was reused for an effort level, though
   `specs/workflows/research-decomposition.md:39` already binds it to research
   programme maturity on a different axis -- while citing that very file as a
   known fragment.
4. **A probe hard-blocking work its own assumptions table rates High.** Prompt
   authoring was gated on a mid-tier probe. Step 5's test decides hard from
   soft: if the probe never lands, prompt authoring is less informed, not
   impossible, so the edge is `soft_depends_on`; and step 4 forbids
   manufacturing a roadblock where minimal effort settles the question.
5. **A scoring node with no successor.** The convergence node emitted rubric
   scores that nothing consumed, and excluded remediation in its own
   `## Not included`. Step 5 requires judgment-only work be wired forward to an
   explicit follow-up node or owner.

## Loop constraints

These bind the iteration rather than the output:

- **Keep the pair out of reach.** The prompt and the prior output go in a
  scratch file outside the PKB and outside the executor's workspace. Stored
  where the next executor can search, they cost the next run its blindness.
- **Two runs per iteration.** One run cannot separate a wording change's effect
  from agent variance, so a single run is never evidence that an edit worked.
- **Show the user the output.** Each turn ends by putting what the runs produced
  in front of the user for a sufficiency judgment. The loop continues or stops
  on that judgment, not on this template's reading of it.

## Exit

Two blind runs happened with their prompts and raw outputs kept outside the PKB;
every load-bearing claim in the outputs is verified, falsified or marked
unverified; all five carried defects are checked and each is cleared or recorded
as reproduced with the obligation it breaches; and the user has the produced
output in front of them and has said whether it is sufficient.
