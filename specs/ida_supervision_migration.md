---
id: ida-supervision-migration-spec
title: Migrating Supervision Capability into Ida
type: spec
status: draft
tier: core
depends_on: [supervision-split-spec, supervisor-spec, agent-authority-spec]
tags: [spec, agents, ida, supervision, autonomy, trust]
---

# Migrating Supervision Capability into Ida

The end state this design serves: a supervisor runs a whole day-long delegated
build to a terminal state while the user is away, and the user's involvement
falls to the decisions only they can make. `ida` is the only agent that talks to
the user, so if supervision is to survive a day-long absence at all, some of it
has to be hers.

The question is which part. `rex` is a project-local persona that ships in no
plugin, and its charter has already been taken apart:
[`agents/supervision-split.md`](agents/supervision-split.md) records where each
half went — the standard held while scoring someone else's run to
`.agents/skills/dogfood/SKILL.md` § "Supervising a trial", the material for
driving a run to `.agents/skills/debug/SKILL.md`. The delegate-and-verify loop
itself is now a shipped skill,
`plugins/orchestrate/skills/supervised-development/SKILL.md`, which
[`polecat/supervisor.md`](polecat/supervisor.md) mandates any orchestrator
invoke rather than hand-roll.

So the remaining question is narrow and answerable: **of what is left, which
capabilities move to ida, on what evidence, and what never moves.**

## What "supervision capability" decomposes into

Four separable things travel under the one word. They have different homes.

| Capability       | What it is                                                                                               | Where it sits                                                                                                             |
| ---------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **The standard** | What counts as evidence, what a halt means, that an ambition is never traded away to make something pass | `.agents/skills/dogfood/SKILL.md` § "Supervising a trial" — invocable by any identity, which is why it was put in a skill |
| **Adjudication** | Judging one returned unit against criteria fixed before it ran                                           | The identity holding the user's intent                                                                                    |
| **Driving**      | Surface choice, dispatch, the build-install-probe cycle, waiting on exits, reopening a record that lies  | `plugins/orchestrate/skills/supervised-development/SKILL.md`, run by james                                                |
| **Continuation** | Deciding, without a user turn, that the loop goes round again                                            | Contested. This spec is about this row.                                                                                   |

The first is already ida's: `plugins/ida/agents/ida.md` § "Dogfood duty" names
the skill and says holding the standard is hers while driving the run is not.
The third is already james's and stays there. The migration is entirely about
the second and fourth.

## The split, and why it falls there

### Migrates to ida — adjudication and continuation

**Adjudication.** Ida already evaluates the logical completeness of returned
reports and already refuses hearsay. The increment is temporal, not
categorical: pre-registering a unit's acceptance criteria before it is
dispatched, and holding that unit open against those criteria across hours in
which the user is absent. Judging a deliverable against the user's intent rather
than against the brief it was written from is a thing only ida can do, because
ida is the only layer holding that intent.

**Continuation.** Today ida returns control after every step. During an absence
that is not caution, it is a stall: nobody is there to receive the control. The
capability worth moving is precisely the narrowing of _when ida must hold_ — a
re-dispatch of an already-approved unit against unchanged, already-approved
criteria is not a new decision, and holding for it spends the user's working
memory on a question that has already been answered.

Both are judgment about evidence. Neither requires spawning anything.

### Stays with james and orchestrate — everything that touches a worker

Surface selection, image freshness, the build-install-probe cycle, waiting on
exit signals, reopening a unit whose record claims a delivery that is absent,
commissioning certification from marsha: all of it stays. Three reasons, in
descending order of how hard they are to argue with.

1. **Context.** Ida's delegate-heavy-work discipline is not a stylistic
   preference; it is what lets her keep pace with a user who is multitasking
   across background work. Supervision's driving half is the context-hungriest
   work in the framework — transcripts, probe output, diffs, container logs.
   Moving it into the one agent that must stay light inverts the exact property
   the interactive design was built to protect. This is the decisive argument
   and it is sufficient on its own.
2. **Auditability.** Ida reaches the graph only by commissioning pauli, and
   reaches workers only through james. That chokepoint is what makes "what can
   this agent do?" answerable from one file, per the authority-non-transit rule
   in [`agents/agent-authority.md`](agents/agent-authority.md). Granting ida
   spawn or write authority dissolves the chokepoint; the autonomy then has no
   auditable boundary at exactly the moment it stops being watched.
3. **Latency.** An agent that may be blocked on a forty-minute build cannot also
   be the agent that answers the user within a turn.

The inline-versus-delegate rule already settled in the interactive-mode design
decides this without any new principle: ida acts inline when the user is
watching _this_ step, when the work is read-only, or when it is the durable
write the step was asked to complete; she delegates work that is describable and
async. **A supervision step taken during a user absence is by definition not
co-worked.** The existing rule sends the driving half to a worker on its own
terms. Only judgment is left on the table, which is the split above.

## Trust checkpoints

"As trust grows" is not a plan until it names what is measured, by whom, and
what result moves the gate. Five stages. Each one names the authority it adds,
the measurement that licenses it, and the observation that revokes it.

**The measurement never comes from ida.** A supervisor scoring its own
supervision is the failure mode the whole framework is built against; proof has
to come from a channel the subject cannot author. Every gate below is scored
from the durable record — the task record's verdict, the probe output, the
committed diff — by an identity that did not make the call being scored.

**The three quantities.**

- **False accept** — a unit ida accepted that an independent check later found
  undelivered, unbuilt, or failing its own pre-registered probe. This is the
  only failure that matters. A false reject costs compute and nothing else.
- **Disagreement rate** — over a window of units, the proportion where ida's
  accept/reject call differs from the independent verdict recorded on the same
  task.
- **Out-of-brief event** — an autonomous run that changed something the standing
  brief did not cover, whether or not the change was good.

| Stage                               | Authority added                                                                                                                                   | Gate to enter                                                                                                                                                                        | Gate to leave                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| **0 — Standard held**               | Ida holds the supervision standard; james drives and adjudicates. This is where the tree is.                                                      | None.                                                                                                                                                                                | —                                            |
| **1 — Standing brief**              | Ida may fix a unit's acceptance criteria before dispatch and hold the unit open across an absence, returning one checkpoint on the user's return. | The enforcement substrate below exists.                                                                                                                                              | Any out-of-brief event.                      |
| **2 — Silent re-dispatch**          | Ida may have an already-approved unit re-run against unchanged criteria, without a user turn, to a declared retry budget.                         | A window of units at stage 1 with zero false accepts, independently scored.                                                                                                          | One false accept.                            |
| **3 — Wave continuation**           | Ida may let a pre-approved sequence proceed from one unit to the next without a user turn.                                                        | A window at stage 2 with zero false accepts **and** a disagreement rate low enough that the independent check is confirming rather than correcting.                                  | One false accept, or one out-of-brief event. |
| **4 — Standing day-long authority** | The standing brief covers a day's work; the user is engaged only at the permanent gates below.                                                    | A window at stage 3 with zero false accepts, plus at least one recorded instance of ida _correctly refusing_ to continue — evidence the judgment discriminates rather than approves. | One false accept.                            |

**A failure drops the stage by one, immediately, and re-entry requires the full
window again.** Trust that only ratchets upward is not trust, it is drift.

**On the window size.** The framework's own standard is that evidence is
recurrence rather than salience — one incident is a data point, three cited
recurrences justify a mechanism — and that a blind instruction test needs at
least two runs per condition or it measures agent variance instead of the
change. Those numbers are the floor for a window here, not a validated value for
it. **The right window size is not established.** The probe that settles it:
run stage 1 for a fixed window and record the disagreement rate. If it is
already zero at the floor, the gate is too loose to be informative and the
window is measuring nothing.

## Gate policy

### What stays human-approved at every stage, including stage 4

Autonomy scales what ida decides between these gates. It never consumes one.

- **Anything externally visible.** Nothing reaches outside the workspace without
  explicit sign-off — publication, submission, sending, a merge to a protected
  branch. Ida's own definition already carries this and it is not negotiable at
  any trust level.
- **Methodological choices.** Where implementation needs a methodological call
  nobody made, ida halts and asks. A day-long absence makes this _more_ binding,
  not less: an unattended run is exactly the condition under which a
  methodological shortcut goes unnoticed.
- **Anything touching research data.** Research data is immutable. Work that
  would modify, reformat, or convert a dataset never enters an autonomous stage
  at all — see the containment rule below for why.
- **Enabling a new runtime mechanism**, which requires a dogfood
  pre-registration with promote and kill criteria.
- **Any instruction or remedy edit.** Record first, then propose; no approval, no
  edit. An autonomous supervisor that may rewrite the instructions it is judged
  against is not supervised.
- **Widening the standing brief itself.** The brief is the boundary of the
  autonomy, so it can only be widened from outside.

### Containment — the autonomy ceiling is the revert horizon

**Ida's autonomy may never exceed what one revert can undo.** Every stage above
operates only where the artifact is a branch or a draft pull request, and the
rollback for a whole bad day is deleting it. This is what makes the stages safe
to attempt at all, and it is why data-touching work is excluded outright: an
overwritten dataset has no revert horizon, so no amount of accumulated trust
buys authority over it.

### Escalation, and what gets rolled back

When an autonomous run goes wrong, three distinct things roll back, and
conflating them is how a bad run is recorded as a good one.

1. **The deliverable** — branch or draft pull request, deleted or reverted.
   Nothing merged, so nothing to unmerge.
2. **The record** — a unit whose deliverable is absent goes back to in-progress
   _before_ anything else is decided, per
   `plugins/orchestrate/skills/supervised-development/SKILL.md` § 6.
   Reopening is repair, not judgment. It is a graph write, so ida commissions it
   from pauli; the migration does not give her the pen.
3. **The trust** — the stage drops, per the table above. This is the only one
   that is about ida rather than about the work, and it is the one most easily
   skipped.

The user learns of a failed autonomous run in the same register as a successful
one. The honesty disclosure fires in every register including held and
interactive turns — what scales with autonomy is the disclosure's content and
surface, never whether it fires. Concretely: a returned autonomous run is
surfaced as a concise disclosure the user can revise, correct, or reject before
the work is treated as settled. It is never a sealed report of a decision
already closed.

## What must not migrate

The strongest constraint in this design is the list of things no amount of trust
transfers.

**Spawning and adjudicating workers.** Not because ida would do it badly, but
because doing it at all makes her something else. The three arguments above —
context, auditability, latency — do not weaken as trust grows; they are
properties of the role, not of the confidence placed in it. A capability that
requires holding a worker's transcript in context sits badly in the agent whose
scarce resource is context and whose job is to be responsive.

**Writing to the graph.** The single-writer property is what makes the graph
correctable. An agent that both makes a call and records it has no independent
account of what it decided.

**Certifying its own work.** Certification is commissioned, not performed —
where acceptance turns on judgment rather than a probe, the verdict comes from
marsha via `plugins/orchestrate/skills/verify/SKILL.md` and is recorded. Ida
adjudicating a unit is not ida certifying it, and stage 4 does not merge those.
Most sharply: **ida can never be the channel that scores ida.** Every gate in
the table above is void if the measurement is taken from ida's own account.

**The user's authority to end the conversation.** Artifacts landing is the floor,
not the finish. Autonomy shortens the list of things the user is asked, and
never the list of things they are told.

**The disclosure into silence.** A quieter autonomous run is the whole point; a
silent one is a different system. Never suppress; only scale the content.

## What blocks stage 1 today

The design above rests on an agent's declared authority envelope being auditable
ground truth. In this tree it is not.

`plugins/ida/agents/ida.md` frontmatter declares `name`, `description`, `color`,
and `permissionMode` — and nothing else. It carries no `tools`, no `subagents`,
and no `skills` key.
[`agents/agent-authority.md`](agents/agent-authority.md) describes ida as
declaring an explicit `subagents` list and as keeping a declared `tools` list;
both claims have decayed against the file. That spec separately records an
observation that ida's declared tool restriction did not hold at runtime — an
allowlist ignored in favour of the parent session's broader set.

Ida's routing discipline is therefore carried entirely in prose: she is told
james is her only subagent and that she is not a writer to the graph. Prose is
enough for a co-worked session, where a user is present to notice a violation
within a turn. It is not enough for a day-long unattended run, which is the
exact condition under which nobody notices.

**No stage past 0 should be entered while the envelope is neither declared nor
enforced.** The two are separable and both are owed: restoring the frontmatter
declaration is a repair to this repository; making the declaration bind at
runtime is an upstream harness matter recorded in the authority spec. Until the
first lands, the whole of this design is a boundary nothing checks.

## Open forks, and the probe that settles each

This is a design over a genuinely open question. Four things are unsettled, and
the design would change materially depending on how they land.

**Where the standing brief lives.** On the task graph, or in ida's conversation?
The graph makes the run resumable by a successor with none of ida's context,
which the supervision loop already requires; the conversation is where the
user's intent actually is, and the graph has historically lost it. _Probe:_ give
a fresh ida session only the task record for an adjudicated unit and see whether
it reaches the same accept/reject call. If it does not, the brief is not on the
graph however much of it was written there.

**Whether adjudication is cheap enough in context.** The entire split rests on
the claim that judging a returned unit costs ida little while driving one costs
her a lot. That claim is asserted, not measured. _Probe:_ measure ida's context
growth per adjudicated unit across a multi-unit run. If adjudication turns out
to carry the transcript in with it, the split proposed here does not hold and
adjudication moves back to james with ida receiving only the verdict.

**Whether the right variable is being measured.** The end state is described as
trust in _the framework_ growing, but every checkpoint above measures _ida's_
judgment. These come apart: ida can be a reliable judge of unreliable evidence.
If the framework's probes do not catch what they claim to catch, a perfect
disagreement rate certifies nothing. _Probe:_ seed a run with a deliberately
undelivered unit whose task record claims delivery, and see whether the
independent channel catches it. A checkpoint regime that cannot detect a planted
failure is measuring agreement, not truth.

**Whether stage 4 is reachable at all, or only approachable.** Nothing here
establishes that a day-long unattended run has a stable terminal state; the
stages assume the failure rate falls with trust rather than compounding with run
length. _Probe:_ the first stage-3 window that runs long enough to observe
whether errors are independent or correlated across units.

## Relationship to the surrounding design

This spec resolves the gap left open by
[`agents/supervision-split.md`](agents/supervision-split.md), which recorded
that ida holds the supervision standard and delegates the run, and that whether
any further capability should move — and what would gate it — was undecided.
The answer here is: adjudication and continuation move, on the staged evidence
above; driving does not, at any stage.

It does not reopen [`polecat/supervisor.md`](polecat/supervisor.md). The four
supervisor concerns and the four evaluation outcomes are that spec's, and the
loop remains `plugins/orchestrate/skills/supervised-development/SKILL.md`,
invoked and never hand-rolled. What changes across the stages here is only
_which identity decides_ the Evaluate concern's outcome without a user turn, and
whose absence the loop must survive.

The evidence shape every claim in an autonomous run carries is
[`enforcement/evidence-contract.md`](enforcement/evidence-contract.md); the
release-scale approval the permanent gates instantiate is
[`enforcement/sign-off.md`](enforcement/sign-off.md). Neither is restated here.
