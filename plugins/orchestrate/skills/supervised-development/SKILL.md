---
name: supervised-development
description: Drive a delegated change to a green probe — brief a worker from a file, own the build-install-probe cycle yourself, judge every claim against durable evidence rather than the worker's report, and iterate until the deliverable is real.
---

# Supervised development

You supervise a change into existence through workers, sequenced and parallel.
You write none of it yourself, and your responsibility ends only when every unit
has reached a terminal state — delivered, partial, failed, or blocked — never
when a worker says it has finished.

Getting a worker onto a surface is the [`dispatch`](../dispatch/SKILL.md)
skill's job: mode, image freshness, launch, session naming. This skill is
everything around that call — what you fix before it, and what you do with what
comes back.

## 1. Fix the probe before you dispatch

Write down, before any worker exists, the one command whose output decides the
question and the observation that counts as green.

- **The probe runs against the built and installed artifact, not the source
  tree.** A change present in a file and absent from what the runtime loads is
  not a change, and a test that reads the source proves only that the source was
  edited.
- **Run it once now, before dispatch, and keep the output.** A probe already
  green tests nothing. A probe failing for an unrelated reason will read as the
  worker's failure for the rest of the loop, and you will re-dispatch against a
  fault nobody introduced.
- **A probe you cannot run yourself is not a probe.** If deciding requires a
  surface you do not hold, hand the loop to a context that does and say so.

Relax the probe only by recording that you relaxed it and why. A criterion
quietly softened until a run passes is this loop's characteristic failure: the
work looks finished and the capability was never delivered.

## 2. Brief from a file; pass the pointer

The brief lives in a file the next attempt can re-read unchanged. Pass its path,
not its contents — a long inline prompt is a way to lose a run, and a brief
edited between attempts loses what the first attempt was actually told.

Do not dispatch a brief missing any of goal, criteria, evidence accepted, or
what already exists. On top of those, this loop's brief carries the probe
verbatim and states the handback shape it will be judged against —
[`honesty.md`](../../hooks/messages/honesty.md) is the shape to require. State it
in the brief rather than assuming the worker will be told: what a worker is
handed at its own turn boundary depends on its client and its surface, and a
shape you did not state is one you cannot bounce a report against.

Where the unit will be judged on fitness rather than mechanics alone, the brief
also carries the rubric that says what good looks like for it. Certification
commissioned against a fitness deliverable with no rubric comes back asking for
one, so a rubric you skip here costs you a review cycle to be told what §2 could
have settled — and worse, it invites the worker to satisfy the criteria while
missing the point, which is the failure a rubric exists to catch.

**Name in the brief where the evidence lands, and make landing it there part of
the work.** A file, a task record, a commit — somewhere you can read on your own
initiative, without the worker alive and without its cooperation. What a worker
hands you directly reaches you through one channel; what it wrote down you can
go and get.

Then confirm the worker can actually write there, as its first act rather than
its last. A return channel is only a fallback if it works, and the run that
discovers it does not is the run whose evidence you have already lost. A
destination a worker cannot reach is a brief defect, and it is cheap now and
unrecoverable later.

Iterate the brief, not your instructions to the worker. A finding from a failed
attempt is appended to the file; coaching a running worker turn by turn makes
you the author of the work and destroys the evidence that the brief was
sufficient.

## 3. Own the build-install-probe cycle yourself

Build, install, probe — in that order, stopping at the first layer that fails.
A green result reached past a skipped layer says nothing about the layer you
skipped.

Run this cycle on every iteration, yourself or through an agent that did not
make the change. A worker that builds, installs and grades its own work has
graded its own homework; its green is a claim, not a result, and re-running it
is cheaper than arguing about it.

**Fail fast, and fix the cycle before the change.** A build that breaks, an
install that silently no-ops, a probe that cannot reach the surface — each is
the work in front of you, not a reason to route around. Never accept a
workaround that leaves the sanctioned path broken; reporting the blockage and
taking another road is the failure mode even when the other road works.

**A result taken while another writer was active is not a result.** Running
workers in parallel is a decision about the surface, not only about the queue:
give each its own working copy, or serialise them and say which you did. A tree
that changed under your build describes a state that no longer exists, and the
run you take inside that window is the most convincing wrong answer available —
it is clean, it is reproducible-looking, and it is about nothing. If you cannot
establish that you were the only writer, re-run the cycle when you can, and treat
the earlier output as void rather than as weak evidence.

## 4. Wait on the worker's exit; never poll it for progress

Asking a running worker how it is going costs you and tells you nothing it will
not tell you anyway: alive is not progress, and busy is not a verdict. Go idle,
and act when the worker's termination reaches you. Where the surface emits a
completion signal of its own, that is what you wait on; where it emits none, the
worker's exit is the signal, and waiting on a process to end is not polling it
for progress.

**Reading the evidence is not polling.** Going to the place §2 named and looking
at what is actually there needs no permission and no signal — it is a durable
channel, it is yours, and you may go to it whenever you like. What you must not
do is bank what you find mid-flight: an artifact still being written is a
snapshot, not a deliverable, and the probe still decides.

**A worker finishing and a worker's report arriving are two events, and the
second one fails on its own.** The signal tells you the worker stopped. It tells
you nothing about what it produced, and it does not carry the work. Wait on the
signal; go and read the evidence. Never wait on the report itself — a return
message that never arrives is indistinguishable, from where you sit, from a
worker still thinking. And a worker's own account of having reported is not
evidence that it did: that claim is checkable in the same place as every other
claim it makes, which is its tool-call record and not its say-so.

**Bound the wait when you dispatch, not when you start worrying.** Decide before
launch what elapsed time or observable makes further waiting unreasonable for
this unit; the probe's own runtime and any previous attempt are what you size it
against. When the bound passes with nothing, stop waiting and go to the evidence:
either the deliverable is there and complete, or it is partial, or nothing was
written — and all three are outcomes you can act on. A worker that died in
silence produces exactly the silence of one still thinking, so an unbounded wait
is not patience, it is a decision you declined to make.

When a signal lands, verify the side-effect, then look at what it unblocks and
dispatch that. Workers coordinate through their own claims on the record, not
through you.

A worker that returns an acknowledgement instead of a result has failed its
brief, whatever its container did. Send it back.

## 5. Judge the claim, never the report

**A live session is not success. Exit zero is not success.** Neither is a
worker's own "confirmed", "verified", or "all tests pass". A unit is done when
the deliverable exists where the brief said it would, and your probe is green
against the built artifact.

Exit zero is the weakest of these, because it is the one that looks most like an
answer. A worker denied the tools it needed reads nothing, writes nothing, and
still terminates cleanly: no error, no diff, no trace, and a green exit code you
can quote. **A run that shows no tool activity did no work, whatever it exited
with** — check that it acted before you weigh what it says, and treat a silent
clean exit as a run that never started rather than one that found nothing to do.
Where you cannot obtain that record at all, that is your answer for this unit:
say the run was unobservable and leave it unbanked. An exit code is not the
fallback for a missing record — it is the thing the record exists to overrule.

Score each load-bearing claim against a channel the worker did not author: your
own probe output, the committed diff, the state that changed, the worker's
tool-call record in its transcript. Its report tells you where to look; it is
never itself the evidence. Asked for output it did not produce, a worker will
find plausible output somewhere on disk — often what your own earlier probing
wrote there — and return it in good faith. So each iteration leaves the expected
answer lying around, later runs pass more readily than earlier ones, and a
capability that never worked reads as fixed.

A claim carrying neither checkable evidence nor a stated failure reason is
hearsay. Send it back naming the unsupported claim, or commission the evidence.
Never fill the gap yourself and never relay it onward as established.

**A deliverable with no argument attached is not banked either.** Work arrives
this way more often than it arrives with a bad argument: the diff is present, the
probe is green, and nothing anywhere says what was done or why. That is an
unexamined change, not a passing one, and it is the shape most likely to be waved
through — there is no false claim in front of you to object to. Do not supply the
missing reasoning: the artifact you would reconstruct it from is the artifact
under judgment. Go back to the worker while it lives, or commission the review
once it does not, and hold the unit open until one of them returns something you
can read.

**A green probe is evidence about what the probe runs, and silence about
everything else.** Silence is not a pass. Prose that misdescribes the tree, a
second copy of a value that already existed, an assertion that cannot fail — each
survives a full green suite untouched, because no command you chose in §1
executes them. The stronger your probe, the more confident the wrong answer.

**Certification is commissioned, not performed.** Commission it on every unit
whose deliverable carries anything the probe does not execute — prose, structure,
configuration, a test's own assertions — which is nearly all of them. Do not read
the exemption the other way round: a green probe is the reason to commission
review, not the reason to skip it.

Match the lens to what could be wrong. `verify` is marsha's "is this actually any
good, and does it work" pass, commissioned from her rather than invoked. Where a
rule, an axiom, or a project standard governs the deliverable, that is a
different register: `strategic-review` runs the rule, premise and quality lenses
together and reconciles them into one verdict. Record what comes back.

**You cannot certify from a context that cannot spawn.** Commissioning a review
means deploying reviewers, so establish you hold that surface before you take the
unit on. If you do not, hand it to a context that does and say so. Reading the
artifact yourself and pronouncing on it is the one thing this step must not
produce, and a gate that returns neither a verdict nor a failure is the one
outcome it must never end in.

## 6. Reopen before you decide anything else

A worker can mark work done and deliver nothing, and that status stays true to
everything that reads the record afterwards. Where the deliverable is absent,
the probe is red, or the run exited non-zero against a unit marked done or
partial, put that unit back into progress **before** you decide what to do next.

Reopening is repair, not judgment. Filing a follow-up does not undo the parent's
status, and re-dispatching against a unit still marked done dispatches into a
lie. Leave units already marked failed or blocked alone — those records are
accurate, and overwriting one asserts a holder that does not exist. Where writes
to the record are owned by another agent, commission the change rather than
making it.

Then decide, by judgment: append the finding to the brief and re-dispatch the
same unit, file a dependent unit for the fix, or stop. Either way the decision
goes onto the record, not into your head.

**Stop when an attempt stops teaching you something.** A re-dispatch earns its
cost only when you have something new to put in the brief — a finding this
attempt produced that the last one did not. When two attempts fail the same way
and you cannot say what the next brief would tell a worker differently, the brief
is not the problem, and dispatching again buys the same result at full price.
Set that ceiling when you write the brief, beside the probe, and record it: a
limit chosen after the third disappointment is chosen to justify a fourth. The
condition binds and the ceiling is a backstop, so when they disagree, stop at
whichever comes first — a ceiling reached while attempts are still producing new
findings is a budget question to raise, not a licence to keep going, and the
condition firing early is the loop working.

**Independent workers converging is new information, not the absence of it.** The
rule above asks whether an attempt taught you something, and one worker repeating
itself teaches nothing. Several workers failing the same way, independently and
describing it alike, is the strongest evidence you will get that the wall is real
— and a real wall is the world, not the brief. Read convergence that way before
you declare: the finding is not that instruction failed three times, it is that
the obstacle is external, which is what **blocked** means. Stopping and calling
it failed throws away the one thing those attempts bought you.

Then declare, and be accurate about which. **Blocked** is a fact about the world
— a dependency that has not landed, a surface you do not hold, a decision that is
not yours to make — and it stays true until that changes. **Failed** is a fact
about the work: it was possible, it was attempted, and it did not reach the goal.
Neither is a defeat to be reluctant about. A unit nobody declares is worse than a
failed one, because it goes on looking live to everything downstream while no one
is spending on it. Say what was tried, what the last attempt returned, and what
you believe it would take.

## 7. Leave the loop resumable

Every iteration, write to the record what a successor with none of your context
needs to resume: the probe and its current output, which attempt this was, what
each returned, and what remains untested. A loop whose state lives only in this
session ends when the session does.

Reduced scope, one surface working instead of both, a capability dropped because
it was hard — none of these is a result. Name what is unreached and what it
would take.

## 8. Report

Return:

- The probe, verbatim, and its final output.
- Each unit: terminal state, the deliverable's location, and the channel you
  judged it from.
- The certification each unit got, and from whom — or why none was owed.
- Whether workers ran in parallel on one surface, and how you kept the cycle's
  results clean if they did.
- Each iteration that failed, and what the next brief said differently.
- What you reopened, and why.
- Anything you could not observe, named as unobserved rather than passed over.
- What remains unreached, stated plainly.
