---
status: draft
tier: 2
type: spec
title: Reconciled review verdict — orchestrator client split
tags: [agents, review, rbg, pauli, polecat, mcp]
created: 2026-08-15
---

# Reconciled review verdict — orchestrator client split

Reviewing [orchestrator-client-split.md](orchestrator-client-split.md).
Reviewers: rbg (rule compliance), pauli (strategic). marsha was commissioned and
returned nothing, so runtime-quality review is missing from this verdict.

**Verdict: PROCEED except Section D.** Sections B, C, F and G survive. Section A
proceeds only with its build change and tests. Section E proceeds only behind its
probe. Section D is blocked on prerequisites neither reviewer could resolve.

## Absorbed into the design — no longer open

These findings were accepted and are now stated in the design itself. They are
listed only so a reader does not re-litigate them:

- The `james`/`jim` split, and with it the reference sweep across ~50 surfaces,
  is cancelled. One `james` remains, so every reference stays correct.
- `dispatch.sh` is cut. Its rationale was "an instruction to pass a flag is
  droppable" — an instruction to call `dispatch.sh` is exactly as droppable, and
  it had no shipping path (`lib/polecat/` reaches plugins through explicit
  `[[shared]]` blocks; there is no equivalent for `lib/agy/`). Section B closes
  the class properly, because no instruction is involved.
- A commented "ready to enable" `allowedTools` block cannot ship: the adapters
  round-trip frontmatter through YAML (design C8). rbg's stronger claim that
  `allowedTools` is absent from the agent schema has since been overtaken —
  `specs/agents/agent-authority.md` now documents it as the approval rule set,
  distinct from `tools` and from `subagents` (design C7). The design records the
  distinction rather than the original objection.
- `--agent none` was a magic value over a namespace we do not own; the paired
  `--agent` / `--no-agent` boolean shipped instead.
- Section B is new work, not the verification of a prior decision. A dispatched
  worker today boots as no agent at all.
- Cross-plugin MCP naming is permitted, conditionally (design C9).
- The stale `dist/` hazard, `pc`'s under-scoped `Bash` grant, and the claim that
  section A needs no build change (false for the playwright grant) are all
  corrected in the design.

## Open — Section D blocks

**The gate may not bind.** `specs/agents/agent-authority.md:163-176` records that
a spawned `ida`'s actual top-level tool set was `Agent, Artifact, Bash, Edit,
Read, Skill, ToolSearch, Write` plus the full PKB MCP namespace — "none of which
its frontmatter grants and four of which it explicitly denies." A lockdown
expressed in frontmatter alone may pay the full cost of the rewrite and buy
nothing. Establish that some declared surface binds at runtime before attempting
Section D.

**`Agent(pc)` may not be a resolvable address.** `aops_ba33ec32` (status `ready`,
tag `measured`, reproducible across three runs) records bare `pc`/`pauli`
resolving to "Agent type not found"; the working forms are plugin-namespaced.
Today a wrong guess costs 12–20s and `ida` retries. Section D leaves nothing to
retry onto, so `aops_ba33ec32` must land first.

**It contradicts a `done` node and an unreviewed spec.** `aops_e39b6b9d`
explicitly excludes from `ida` both "spawning and adjudicating workers" and
"writing to the graph — single-writer is what makes it correctable", and it
delivered `specs/agents/ida-supervision-migration.md`, still an unreviewed draft
in PR #2446. That spec holds that "no stage past 0 is entered while the envelope
is neither declared nor enforced" — and Section D is exactly such a stage change.
The design moves in a third direction that no recorded decision supports.
Reconcile against the node and the PR before implementing.

**`ida.md`'s current state may be a regression, not a design choice.** Its grant
of `Agent(pauli)` and its instruction to call `pauli` to hydrate contradicted both
`aops_e39b6b9d`'s recorded observation and the supervision split. Establish
whether that drift was intended before revoking it as though it were.

## Open — settle before implementing

- **Section E** rests on an unrecorded fact: whether agy merges per-plugin MCP
  configs into one namespace. Settle it by live call before writing any grant.
- **Section F** codifies a test over a surface three sources describe
  differently. Reconcile the registration drift first, or the test freezes
  whichever description happened to be read.
- **Section A**'s build change is the only thing standing between the suffixed
  filenames and a silent no-op. Its four failure cases must all be tested, not
  just the happy path.

## Where the reviewers were working from stale information

Both flagged #2387 (`agy --agent` strips MCP tools) as blocking, and rbg called it
"two independent sources on the same defect". It was refuted end to end in commit
`250921f8d`. Direct observation beats a stale doc, so the blocker does not stand.

That both reviewers reached it independently is the strongest argument for
Section G: the stale records are misdirecting competent readers, and they nearly
halted this design.

One thing survives from that finding regardless: **Section B's verification must
be a tool count plus a live PKB call from inside the container, compared against
the same container with no `--agent`.** A resolving agent name proves nothing.
