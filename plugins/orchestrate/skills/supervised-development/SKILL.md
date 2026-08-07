---
name: supervised-development
description: Drive a delegated change to a green probe — brief a worker from a file, own the build-install-probe cycle yourself, judge every claim against durable evidence rather than the worker's report, and iterate until the deliverable is real.
---

# Supervised development

You supervise a change into existence through workers. You write none of it
yourself, and your responsibility ends only when every unit has reached a
terminal state — delivered, partial, failed, or blocked — never when a worker
says it has finished.

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
verbatim and names the handback it will be judged against —
[`honesty.md`](../../hooks/messages/honesty.md) is the shape this plugin already
puts in front of every stopping worker.

**Name in the brief where the evidence lands, and make landing it there part of
the work.** A file, a task record, a commit — somewhere you can read on your own
initiative, without the worker alive and without its cooperation. What a worker
hands you directly reaches you through one channel; what it wrote down you can
go and get.

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

## 4. Wait for exits; never poll

The completion signal is what you wait on. Never a sleep loop, never a poll
against the worker, and never a read of a half-written artifact you happened to
find. Go idle and act when the signal lands.

**A worker finishing and a worker's report arriving are two events, and the
second one fails on its own.** The signal tells you the worker stopped. It tells
you nothing about what it produced, and it does not carry the work. Wait on the
signal; go and read the evidence. Never wait on the report itself — a return
message that never arrives is indistinguishable, from where you sit, from a
worker still thinking.

This is why §2 puts the evidence somewhere you can read without the worker: a
supervisor whose only route to the work is the worker's own final message has one
channel and no fallback. When one signal lands, go to that place, verify the
side-effect, then look at what it unblocks and dispatch that. Workers coordinate
through their own claims on the record, not through you.

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

**Certification is commissioned, not performed.** Where the unit's acceptance
turns on judgment rather than the probe, commission `verify` from marsha and
record the verdict she returns. Reading the artifact yourself and pronouncing on
it is the one thing this step must not produce.

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
same unit, or file a dependent unit for the fix. Either way the decision goes
onto the record, not into your head.

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
- Each iteration that failed, and what the next brief said differently.
- What you reopened, and why.
- What remains unreached, stated plainly.
