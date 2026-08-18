---
id: enforcement-318d578e
title: Enforcement Architecture
type: spec
status: ready
tier: core
depends_on: []
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

Why enforcement is shaped this way. What is currently switched on, and what each
mechanism obliges, is the register: [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).
Nothing here restates it.

## Governing principle — agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on
quality or process**. Hooks, server contracts, and config are **delivery
channels** — they remind, route, and make things visible; they never decide
whether work is good or whether a rule was followed. Every verdict is an agent's
judgment, and the bar every reviewing agent applies is world-leading, not
technically-acceptable.

The only **mechanical** enforcement is **structural prevention**: credential and
workspace isolation, delivery guards, model pins. Prevention by construction —
never reactive detection, never content-sniffing, never a deterministic pass/fail
on the substance of an agent's work.

## The four levers

Enforcement is risk-reduction; compliance is not guaranteed, and a hard block is
often not the best available move.

1. **Norms** — the agent's internalised alignment with intent: prompt directives,
   agent and skill instructions, rules.
2. **Cost** — the token, time, and friction cost of complying against the
   incentive to bypass.
3. **Defaults** — whether the compliant path is mechanically the path of least
   resistance rather than something the agent must remember to invoke.
4. **Likelihood** — the probability a violation is detected, times its
   consequence. Severity moves this lever and no other.

Before escalating severity, establish that the failure is not a cost or defaults
problem. Repeated stale-state assertions are not a norms failure — agents know
the rule — so the fix is cheaper search and injected results, not a heavier gate.

## Where enforcement sits

Five bands, in descending order of how much they depend on an agent's
cooperation. The register lists every mechanism in each.

- **Structural prevention** — holds without cooperation. Container and credential
  isolation, the delivery and seed guards, no-defaults config, model pins.
- **Instructions** — agent personas and skills. The largest band by far, and the
  one the design principles below say to reach for first (including bounded capture floors for routine maintenance, e.g. Pauli's 0/1 write rate, 0-create constraint, and suppression against hydrate's shortlist).
- **The rule channel** — axioms, project rules, and user rules, in three layers
  where a later one may only add obligations and never weakens the floor. Three
  independent delivery paths carry them, and any rule can be on one and off the
  others: each client's **native rule mechanism**, fed at build time; the **cope**
  hook, which asks a local evaluator about each tool call; and the **rbg stop
  check**, which obliges the stopping agent to judge its own session against the
  rules and produce checkable evidence. Overlapping by design — which works
  better is an open question, so all three ship and none is built as though it
  were the gate. They differ in when they fire, what they cost, and what they can
  see: the first two judge an action before it happens and know nothing of the
  work as a whole; the third sees a finished turn and nothing else.
- **The task-graph boundary** — `claim_task` in, `release_task` out. The primary
  accountability point, because it binds to the claim act rather than to session
  mechanics. Contract: [task-contract.md](task-contract.md); the claim-evidence
  shape every boundary reads: [evidence-contract.md](evidence-contract.md).
- **Review** — three judgment registers applied at a task or workflow boundary:
  **pauli** (is the premise sound and aligned), **rbg** (were the rules
  followed), **marsha** (does it work, and is it excellent). Which of these a
  given unit runs is composed by [`brief`](../../plugins/pkb/skills/brief/SKILL.md)
  from the workflow-template namespace, not hardcoded — a fixed set carried in a
  skill's own text is a process the user could never override. An empty composed
  set is a library gap `brief` halts on, not a pass. Shape:
  [workflow.md](workflow.md); the PR-stage instantiation:
  [sign-off.md](sign-off.md).

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition: who
the agent is and what standard it holds. An **agent skill** defines a procedure:
how a job gets done.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can
  execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for
  exactly two reasons: **earmarking** (the skill depends on that personality's
  judgment register) or **permission control** (grants restricted to force a
  workflow split, keeping reviewer ≠ executor).
- The three review registers above name **lenses a review must apply**, not
  exclusive executors. Which agent carries a lens is a dispatch decision.

## Hook channel constraints

Every plugin hook shares one runtime, `lib/hooks/dispatch.py`, injected at build
time. The mechanics — which events honour a block, the once-per-stop-chain guard,
how a plugin's handlers merge — belong to that runtime and are stated in
[`ARCHITECTURE.md`](../ARCHITECTURE.md), Hooks. What binds here:

- **No hook produces a verdict.** A hook may oblige a check; it never reads the
  transcript, and it never grades what the agent did with the turn it was given.
- **A block withholds a stop, never a tool call.** It is legal only where the
  question is a fact about the session — did the check happen — rather than a
  model's reading of a rule. Honoured only on Claude Code on `BLOCKABLE_EVENTS`
  (`Stop`, `SubagentStop`); no handler is permitted to emit a blocking disposition on `agy`.
- **Injection budget scales inversely with firing frequency.** Per-tool-call and
  per-turn events get a line or two; stop events, guarded to once per chain, can
  afford a full instruction.
- **Every agent-visible string comes from a markdown file beside the handler**
  (`hooks/messages/`), editable without touching code.
- **Degradation is distinguished from legitimate absence** by the handlers
  themselves: no evaluator configured, `$ACA_DATA` unset, and no project rules
  directory are all valid states and clean no-ops. A fault is never a gate.
- **A degraded check is legible to the log and not to the person who could fix
  it.** Handler self-reports go to stderr and no further. Known gap in the
  channel, not a property of it.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in
   the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent
   complexity and a new place for the framework to fail.
3. **Measure before changing.** The evidence loop below is the authority for
   adding or escalating a mechanism. Authorial intuition is not evidence.
4. **Show, don't tell.** Where compliance is claimed, require information that
   demonstrates it.
5. **Never guess.** With no evidence either way, current placement holds.

## Evidence loop — how the framework learns

Two flows, deliberately separated as witness and judge, so the volume and
direction of framework change is governed by cross-incident pattern rather than
by the salience of the most recent failure.

1. **Diagnose and route** ([`learn`](../../plugins/pkb/skills/learn/SKILL.md)) — an
   agent that hits friction traces it to the structural cause and routes the
   lesson to the one destination its scope claims. It proposes no fix to anything
   governing future sessions; writing a standing rule needs the user to have asked.
2. **Improve the framework** (the [`triage`](../../.agents/skills/triage/SKILL.md)
   skill's sweep mode) — a detached pass over the accumulated issue queue on a
   cadence the user sets, proposing a mechanism only where recurrence or explicit
   direction justifies it.

A single incident that is a **bug** is fixed immediately from one report. A single
incident that is an **escalation proposal** is logged and waits for the pattern.

## Restoring enforcement

The rule roster and the permission surface are both dark, deliberately: every
mechanism returns one rule at a time against observed failure, rather than as an
undifferentiated block. The register records what each was, which is what makes
re-arming one thing possible.

Three properties any restoration holds to:

- **Off must be a stated state, not an unmarked one.** A parked rule and a rule
  nobody remembered to mark are different facts, and only one is worth reporting.
- **Dark must stay distinguishable from degraded.** A channel with nothing in it
  says so; it does not go quiet.
- **A rule comes back on one path at a time.** The three paths differ in cost and
  in what they can see, so turning a rule on everywhere at once forfeits the only
  question worth asking about it: which delivery was doing the work.

Whether the paths need separate switches is a question the first few rules
answer, not one to settle before them.

## Sibling documents

- [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) — the current-state register.
- [task-contract.md](task-contract.md) — the work-unit contract.
- [workflow.md](workflow.md) — the workflow shape and the review-depth call.
- [sign-off.md](sign-off.md) — workflow-level review, instantiated as the PR pipeline.
- [evidence-contract.md](evidence-contract.md) — the universal claim-evidence shape.
- [auto-mode-classifier.md](auto-mode-classifier.md) — the harness's own per-action classifier.
- [agent-authority.md](../agents/agent-authority.md) — the frontmatter permission schema the grants above are expressed in, and the harness defect that forces four core agents to omit `tools` rather than lose MCP access.
