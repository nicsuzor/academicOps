---
id: ida-supervision-migration-spec
title: Migrating Supervision Capability into Ida
type: spec
status: draft
tier: core
depends_on: [supervisor-spec]
tags: [spec, agents, ida, supervision, autonomy, trust]
---

# Migrating Supervision Capability into Ida

The end state this design serves: a supervisor runs a whole day-long delegated build to a terminal state while the user is away, and the user's involvement falls to the decisions only they can make. `ida` is the only agent that talks to the user, so if supervision is to survive a day-long absence, some of it has to be hers.

**Nothing here has been built.** The tree is at stage 0, both stage-1 preconditions are unmet, and the central claim is conditional on a quantity nobody has measured — see "The unmeasured premise". This document stays `draft` until that probe is green.

## What supervision decomposes into

Four separable things travel under the one word, and they have different homes.

| Capability       | What it is                                                                                            | Where it sits                                                                                                                                                       |
| ---------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **The standard** | What counts as evidence, what a halt means, that ambition is never traded away to make something pass | `.agents/skills/dogfood/SKILL.md` § "Supervising a trial" — a skill, so any identity can hold it                                                                    |
| **Adjudication** | Judging one returned unit against criteria fixed before it ran                                        | The identity holding the user's intent                                                                                                                              |
| **Driving**      | Getting a worker onto a surface, and the loop around that call                                        | `plugins/aops/skills/polecat/SKILL.md` owns mode, image freshness, and launch; `.agents/skills/debug/SKILL.md` is the project-local half; orchestrate owns the loop |
| **Continuation** | Deciding, without a user turn, that the loop goes round again                                         | Contested — this spec is about this row                                                                                                                             |

The standard is invocable by ida already. Driving is orchestrate's and stays there. The migration is entirely about adjudication and continuation.

## The split

### Migrates to ida — adjudication and continuation

**Adjudication.** Ida already evaluates the logical completeness of returned reports and already refuses hearsay. The increment is temporal, not categorical: pre-registering a unit's acceptance criteria before it is dispatched, and holding that unit open against those criteria across hours in which the user is absent. Judging a deliverable against the user's intent rather than against the brief it was written from is a thing only ida can do, because ida is the only layer holding that intent.

**Continuation.** Today ida returns control after every step. During an absence that is not caution but a stall — nobody is there to receive the control. What is worth moving is precisely the narrowing of _when ida must hold_: re-dispatching an already-approved unit against unchanged, already-approved criteria is not a new decision, and holding for it spends the user's working memory on a question already answered.

### Stays with orchestrate — everything that touches a worker

Surface selection, image freshness, the build-install-probe cycle, waiting on exit signals, reopening a unit whose record claims a delivery that is absent, commissioning certification from marsha: all of it stays, for three reasons.

1. **Context.** Driving reads everything adjudication reads and then more — the transcript, the probe output, the diff, the container logs. The _ordering_ is therefore analytic: driving cannot cost ida less than adjudicating, and that alone keeps driving out of the agent whose defining constraint is staying light enough to keep pace with a user working in parallel.
2. **Auditability.** Ida reaches the graph only by commissioning `aops:pauli`, and workers only through `orchestrate:pc`; she is not a writer to the store. That chokepoint is what makes "what can this agent do?" answerable from one file. Granting ida spawn or write authority dissolves it, at exactly the moment nobody is watching.
3. **Latency.** An agent that may be blocked on a forty-minute build cannot also be the agent that answers the user within a turn.

None of the three weakens as trust grows. They are properties of the role, not of the confidence placed in it.

### The principle

> **Ida may judge what has been brought back to her. She may not go and get it.**

Adjudication sits entirely on the first side: it is a judgment over the handback — does the claim answer the question it was dispatched against, is it supported to the scope it asserts, does the attached evidence resolve — which is what ida is already told to do, extended in time rather than in kind. Driving sits entirely on the second.

## Trust checkpoints

Each stage names the authority it adds, the measurement that licenses it, and the observation that revokes it.

**The measurement never comes from ida.** A supervisor scoring its own supervision is the failure mode the framework is built against, so every gate is scored from the durable record — the task record's verdict, the probe output, the committed diff — by an identity that did not make the call being scored.

**The three quantities.**

- **False accept** — a unit ida accepted that an independent check later found undelivered, unbuilt, or failing its own pre-registered probe. This is the only failure that matters; a false reject costs compute and nothing else.
- **Disagreement rate** — over a window of units, the proportion where ida's accept/reject call differs from the independent verdict recorded on the same task.
- **Out-of-brief event** — an autonomous run that changed something the standing brief did not cover, whether or not the change was good.

| Stage                               | Authority added                                                                                                                                                                        | Gate to enter                                                                                                                                       | Gate to leave                                |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **0 — Standard held**               | Ida holds the supervision standard; orchestrate drives and adjudicates. This is where the tree is.                                                                                     | None.                                                                                                                                               | —                                            |
| **1 — Adjudication transfers**      | Ida makes the accept/reject call on each returned unit, against criteria she fixed before dispatch, and may hold a unit open across an absence. Every call is independently re-scored. | Ida's authority envelope is both declared and enforced. Nothing else gates it, because at this stage her call is advisory.                          | One false accept, or one out-of-brief event. |
| **2 — Silent re-dispatch**          | Ida's call decides alone for accept. She may have an already-approved unit re-run against unchanged criteria without a user turn, to a declared retry budget.                          | A window at stage 1 with zero false accepts, **and** at least one recorded instance of the independent channel catching a planted undelivered unit. | One false accept, or one out-of-brief event. |
| **3 — Wave continuation**           | Ida may let a pre-approved sequence proceed from one unit to the next without a user turn.                                                                                             | A window at stage 2 with zero false accepts **and** a disagreement rate below a threshold set from the stage-2 data.                                | One false accept, or one out-of-brief event. |
| **4 — Standing day-long authority** | The standing brief covers a day's work; the user is engaged only at the permanent gates below.                                                                                         | A window at stage 3 with zero false accepts, plus at least one recorded instance of ida _correctly refusing_ to continue.                           | One false accept, or one out-of-brief event. |

**A failure drops the stage by one immediately, and re-entry requires the full window again.** Trust that only ratchets upward is not trust, it is drift.

**Two discrimination tests, not one.** Stage 4 asks for evidence that ida's judgment discriminates rather than approves; stage 2 asks the same of the independent channel, for the same reason. A channel that has never caught anything cannot license a gate — without that test, every window measures agreement between two things that might both be wrong and calls the agreement truth.

**The window size is not established.** The framework's floor is that evidence is recurrence rather than salience — three cited recurrences justify a mechanism — and that a blind instruction test needs at least two runs per condition or it measures agent variance instead of the change. Those are a floor, not a validated value. _Probe:_ run stage 1 for a fixed window and record the disagreement rate; if it is already zero at the floor, the gate is too loose to be informative.

**Stage 3's threshold cannot be set in advance,** because its whole content is "low enough that the independent check is confirming rather than correcting", and where that sits depends on a base rate the stage-2 window is what measures. What this spec fixes is the procedure: the threshold is set once from the observed stage-2 distribution, recorded on the same record as the window it came from, and never adjusted afterwards to admit a run that missed it. A threshold chosen after seeing the run it judges is not a gate.

## Gate policy

### What stays human-approved at every stage, including stage 4

Autonomy scales what ida decides between these gates. It never consumes one.

- **Anything externally visible.** Nothing reaches outside the workspace without explicit sign-off — publication, submission, sending, a merge to a protected branch.
- **Methodological choices.** Where implementation needs a methodological call nobody made, ida halts and asks. An unattended run is exactly the condition under which a methodological shortcut goes unnoticed, so absence makes this more binding, not less.
- **Anything touching research data.** Research data is immutable; work that would modify, reformat, or convert a dataset never enters an autonomous stage at all.
- **Enabling a new runtime mechanism**, which requires a dogfood pre-registration with promote and kill criteria.
- **Any instruction or remedy edit.** Ida files the evidence record and never fixes the framework inline; proposing the remedy is not hers either, and the edit needs express approval whoever authors it. An autonomous supervisor that may rewrite the instructions it is judged against is not supervised.
- **Widening the standing brief.** The brief is the boundary of the autonomy, so it can only be widened from outside.

### Containment — the autonomy ceiling is the revert horizon

**Ida's autonomy may never exceed what one revert can undo.** Every stage operates only where the artifact is a branch or a draft pull request and the rollback for a whole bad day is deleting it. This is what makes the stages safe to attempt, and it is why data-touching work is excluded outright: an overwritten dataset has no revert horizon, so no accumulated trust buys authority over it.

### What rolls back when a run goes wrong

Three distinct things, and conflating them is how a bad run gets recorded as a good one.

1. **The deliverable** — branch or draft pull request, deleted or reverted. Nothing was merged, so there is nothing to unmerge.
2. **The record** — a unit whose deliverable is absent returns to in-progress _before_ anything else is decided. Reopening is repair, not judgment. It is a graph write, so it goes to `aops:pauli` as a whole question; the migration does not give ida the pen and does not widen the set of agents she reaches.
3. **The trust** — the stage drops. This is the only one about ida rather than about the work, and the one most easily skipped.

The user learns of a failed autonomous run in the same register as a successful one. What scales with autonomy is the disclosure's content and surface, never whether it fires: a returned autonomous run is surfaced as a concise disclosure the user can revise, correct, or reject before the work is treated as settled, never as a sealed report of a decision already closed.

## What must not migrate

**Spawning and adjudicating workers.** Not because ida would do it badly, but because doing it at all makes her something else. A capability requiring a worker's transcript in context sits badly in the agent whose scarce resource is context and whose job is to be responsive.

**Writing to the graph.** The single-writer property is what makes the graph correctable. An agent that both makes a call and records it has no independent account of what it decided.

**Certifying its own work.** Certification is commissioned, not performed: where acceptance turns on judgment rather than a probe, the verdict comes from marsha via `plugins/orchestrate/skills/verify/SKILL.md` and is recorded. Ida adjudicating a unit is not ida certifying it, and stage 4 does not merge them. Most sharply, **ida can never be the channel that scores ida** — every gate above is void if the measurement comes from ida's own account.

**The user's authority to end the conversation.** Artifacts landing is the floor, not the finish. Autonomy shortens the list of things the user is asked and never the list of things they are told.

**The disclosure into silence.** A quieter autonomous run is the whole point; a silent one is a different system. Scale the content, never suppress it.

## What blocks stage 1

### The authority envelope is neither declared nor enforced

`plugins/aops/agents/ida.md` frontmatter declares `name`, `description`, and `color` alone — no `tools`, no `subagents`, no `skills`. Her routing discipline is carried entirely in prose. Prose is enough for a co-worked session, where a user is present to notice a violation within a turn; it is not enough for a day-long unattended run, which is the exact condition under which nobody notices.

Both halves are required, and declaration alone does not buy it. They are separable — restoring the frontmatter is a repair to this repository, making the declaration bind is an upstream harness matter — but they are not alternatives. A declared envelope that does not bind is untrustworthy, so treating declaration as sufficient would gate stage 1 on something known not to work. The enforcement half is demonstrated, not assumed: a spawned ida offered a tool outside its declaration cannot call it, shown in a recorded trial scored from the tool-call record rather than from ida's account of its own capabilities.

### No hook fires the disclosure at ida's turn boundary

The `aops` `Stop`/`SubagentStop` gate is not built, and ida is explicitly excluded from the `SubagentStart` honesty reminder that reaches every other agent ([`../ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md), [`../ARCHITECTURE.md`](../ARCHITECTURE.md)). The obligation named non-negotiable in "What must not migrate" is therefore held by ida's own body and by nothing else. That is tolerable while a user is present for every turn; reconnecting it is a precondition for stage 2, where ida's call first decides alone.

## The unmeasured premise

One quantity carries the whole split and has not been measured: **that adjudicating a returned unit costs ida little enough in context to be worth moving to her.**

The ordering is safe — driving reads everything adjudication reads and more, so driving is strictly the more expensive. But "cheaper than driving" is not "cheap", and only the second claim licenses the migration. If a handback turns out to be adjudicable only by opening the diff and re-reading the transcript, the work is on the far side of the principle above and this spec's central claim fails.

**The fallback is not a degraded design; it is this spec being wrong.** What survives is stage 0, where the tree already is: ida holding the standard, orchestrate driving and adjudicating, ida receiving the verdict. Continuation does not survive on its own — re-dispatching a unit ida did not judge is not the capability described here, it is orchestrate's loop with an extra hop.

_Probe, one cheap run:_ measure ida's context growth per adjudicated unit across a multi-unit run.

## Open forks

**Where the standing brief lives** — on the task graph, or in ida's conversation? The graph makes the run resumable by a successor holding none of ida's context, which the supervision loop already requires; the conversation is where the user's intent actually is, and the graph has historically lost it. _Probe:_ give a fresh ida session only the task record for an adjudicated unit and see whether it reaches the same accept/reject call. If not, the brief is not on the graph however much of it was written there.

**Whether the right variable is being measured.** The end state is trust in _the framework_ growing, but every checkpoint measures _ida's_ judgment, and the two come apart: ida can be a reliable judge of unreliable evidence. _Probe:_ seed a run with a deliberately undelivered unit whose task record claims delivery, and see whether the independent channel catches it. This fork is wired into the table as stage 2's second entry condition rather than left as a caveat.

**Whether stage 4 is reachable at all, or only approachable.** Nothing here establishes that a day-long unattended run has a stable terminal state; the stages assume the failure rate falls with trust rather than compounding with run length. _Probe:_ the first stage-3 window long enough to observe whether errors are independent or correlated across units.

## Relationship to the surrounding design

This spec does not reopen [`sara.md`](sara.md). The four supervisor concerns and the four evaluation outcomes are that spec's, and the delegate-and-verify loop remains orchestrate's, invoked and never hand-rolled. What changes across the stages here is only _which identity decides_ the Evaluate concern's outcome without a user turn, and whose absence the loop must survive.

The evidence shape every claim in an autonomous run carries is [`../enforcement/evidence-contract.md`](../enforcement/evidence-contract.md); the release-scale approval the permanent gates instantiate is [`../enforcement/sign-off.md`](../enforcement/sign-off.md). Neither is restated here.
