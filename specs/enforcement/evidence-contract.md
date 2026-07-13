---
id: enforcement-evidence-contract
title: Enforcement — The Evidence Contract (Universal Task-Boundary Contract)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, evidence-contract]
---

# Enforcement — The Evidence Contract

> **Numbering note.** This file is not a fifth `Layer` in the module-boundary
> layer model ([task-contract.md](task-contract.md), [workflow.md](workflow.md),
> [sign-off.md](sign-off.md)). It is the single contract those layers each
> instantiate at their own boundary — `release_task` (Layer 2), the
> boundary-check and QA-around steps of a workflow (Layer 3), and the
> principal sign-off brief (Layer 4) all read the same rule defined here,
> rather than each layer inventing its own evidence format. The supervisor's
> per-tick worker handback ([`specs/polecat/supervisor.md`](../polecat/supervisor.md))
> is the same contract again, instantiated for orchestration rather than a
> PKB task boundary.

## The contract

Every load-bearing claim made at a module boundary carries one of two things:

1. **Checkable evidence** — a command and its observed output, a `file:line`
   pointer, a resolving URL, or a quoted source — such that a downstream agent
   can validate the claim without reading the originating transcript. Or:
2. **A stated failure reason.**

There is no third option. A claim with neither is not load-bearing — it is
noise, and a boundary check that lets it through has failed.

**Honest failure is always a legal exit.** This is carried forward verbatim
from [task-contract.md](task-contract.md)'s Layer-2 evidence contract and
binds identically at every layer: an agent that could not complete the work,
could not verify a claim, or ran out of budget has not violated the contract
by saying so — clearly, with the reason stated — and stopping. The contract is
violated by silence, by a claim with no evidence, or by evidence that does not
actually support the claim. It is never violated by an honest "I could not do
X, because Y."

This generalises the six-field structured handback the supervisor skill has
used for its own worker briefs (VERDICT/CLAIM/GATE/EVIDENCE/CONFIDENCE/CONFOUND
CHECK — see below) into the universal shape every module boundary in the
framework uses: PKB `release_task`, a workflow's boundary-check and QA-around
steps, and a principal sign-off brief.

## Substance over form

The reviewer at any boundary — `release_task`'s evidence gate, a workflow's
boundary-check or QA-around step, sign-off, or a supervisor reading a worker's
handback — is checking that the **actual criterion named in the task's
acceptance gate was met**, not that the prescribed rhetorical form is present.

Concretely:

- A filled-in `EVIDENCE: file:line` field is necessary but not sufficient. The
  reviewer opens the file at that line and confirms it says what the claim
  asserts. A citation that doesn't support the claim it's attached to is the
  same violation as no citation.
- A `VERDICT: PASS` next to a `CONFIDENCE`/`CONFOUND CHECK` block that recites
  the right field names but was never actually exercised — the confound was
  never isolated, the command was never run, the file was never opened — is a
  contract violation, not a technicality. See `CONFOUND CHECK: NOT RUN` below.
- **A self-graded ritual does not satisfy this contract.** A worker asserting
  its own success in the prescribed format, unread by an independent reviewer,
  is not a boundary check — it is the worker completing a form. The point of
  the six-field shape is to make a claim _cheap to verify_, not to make
  verification optional. Presence of the form is what makes the check fast;
  it is never a substitute for the check itself.
- This is the operative meaning of "boundary check" and "QA-around" in
  [workflow.md](workflow.md#the-five-step-shape): each is a distinct agent
  independently confirming the _thing claimed is actually true_, not a second
  agent confirming the first agent filled in the right headings.

Detecting rhetorical-form-only compliance — a plausible-sounding VERDICT block
whose claims don't survive a spot check — is exactly what the boundary-check
and QA-around steps exist to catch. A reviewer who checks only that the fields
are present has not performed either step.

## The canonical structured-handback format

This section is the single source of truth for the six-field handback shape.
Every other surface that uses it — [`specs/polecat/supervisor.md`](../polecat/supervisor.md)
and any task brief that asks for a handback — links here rather than
restating the field definitions.

```
VERDICT: <PASS | FAIL | BLOCKED | NEEDS-PRINCIPAL>
CLAIM: <one sentence — the conclusion>
GATE: <the acceptance criterion tested, and the observed result against it>
EVIDENCE: <pointers — command+output, file:line, resolving URL, quoted source — NOT pasted dumps>
CONFIDENCE: <high|med|low> + <what single check would falsify this>
CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
```

- `CONFOUND CHECK` is mandatory whenever the verdict blames anything outside
  the agent's own change. `NOT RUN` means the claim is not relayed as
  established until the control is run — this rule generalises past the
  supervisor context: any agent relaying a "not our bug" claim without a
  control is relaying an unverified claim.
- **CLAIM/EVIDENCE is a set of claim+evidence-pointer pairs, not a bare
  assertion.** If a handback asserts more than one substantive fact, itemize
  each on its own line, and pair each with its own evidence pointer — one
  `EVIDENCE` line does not silently cover several unrelated claims.
- Every itemized claim carries the **Observed/Reported label** — the
  canonical definition of that register lives in
  [`head-role-charter.md`
  §Fitness Criteria & Anti-Patterns](../interactive-experience/head-role-charter.md#fitness-criteria--anti-patterns)
  and is not restated here (same SSoT discipline: one definition, every
  other surface cross-references it). In short: **Observed** — the agent saw
  the primary evidence itself, this session, and cites it. **Reported** — a
  subagent, transcript, or document said it; attribute the source and state
  its verification status, or fall back to the literal tag `UNVERIFIED` if no
  evidence pointer exists.

This format is deliberately markdown prose, not a JSON or YAML schema —
consistent with the framework-wide constraint that inter-agent contracts stay
prose, never structured data formats agents must parse exactly (D2, module-d
binding decision). Any harness or gate that wants to check for the format's
presence mechanically may do so as a cheap, non-authoritative hint; it is
never the verdict. The verdict is always an agent reading the content and
judging whether the claim holds — never a regex over the field names (see Substance over form above, and the
governing principle in [enforcement.md](enforcement.md#governing-principle--agents-all-the-way-down):
no programmatic, deterministic, or mechanical enforcement of quality, ever).

## Where this binds

- **Layer 2 — `release_task`/`complete_task`** ([task-contract.md](task-contract.md)).
  The completion claim itself must satisfy this contract; task-contract.md's
  evidence-contract mechanism is this file's Layer-2 instantiation.
- **Layer 3 — workflow boundary-check and QA-around**
  ([workflow.md](workflow.md#the-five-step-shape)). Both steps read a
  handback in this shape; the reviewer applies Substance over form above.
- **Layer 4 — principal sign-off** ([sign-off.md](sign-off.md)). The one-page
  prose brief to the principal is this contract at release-unit scale: every
  delivered/checked claim in it carries a resolvable pointer or a stated
  failure reason, exactly as at Layer 2.
- **Supervisor per-tick handback** ([`specs/polecat/supervisor.md`](../polecat/supervisor.md)).
  Same contract, applied to a background worker reporting to its supervisor
  rather than a task boundary reporting to a reviewer.

## Cutover / grandfather policy

This spec formalises a contract that was previously stated informally (a
prose reminder in the exit-reflection hook and a mechanism bullet in
[task-contract.md](task-contract.md)); it does not yet have a mechanical
gate enforcing it beyond `release_task`'s existing evidence-or-failure-reason
check (H7). A strengthened release gate that checks handback _content_ — not
just presence — is tracked separately (`epic_17aa5821`).

**Tasks created before that strengthened gate ships are grandfathered.**
Concretely: the gate, when it lands, evaluates a task's `created` frontmatter
timestamp against its own ship date. Tasks created before that date are not
retroactively held to a stricter mechanical check than existed when they were
claimed — the agentic/prose obligation in this file binds immediately and
universally (it always did, informally), but the _mechanical_ gate epic_17aa5821
builds is forward-only. This uses the existing `created` field; it introduces
no new frontmatter field (D2: ≤1 new frontmatter field framework-wide for this
module, and zero is simpler than one).
