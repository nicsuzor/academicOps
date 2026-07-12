# Cutting Seams — detail and worked example

Full doctrine: [[two-layer-decomposition]] Layer 1. This file is the how; `SKILL.md` Step 1 is the
contract.

## Why this order, not another

Cutting on **responsibility boundaries first** means the DAG's shape follows who's accountable, not
an arbitrary task-size heuristic — an author subtask and its reviewer subtask are structurally
distinct even if they'd fit in one session together, because self-review doesn't bind
(evaluator-optimizer bias). Only once boundaries are drawn does **session-sizing** apply within each
boundary — merge micro-steps a single owner would just relay, split anything too large for one
sitting. **Dependencies** come last and are read off the boundaries already drawn, not invented
independently — if two subtasks have no true data dependency, they're parallel even if one "feels"
like it should come first.

## Rolling-wave in practice

Pass 1 is not "plan the whole tree, then execute." Detail the wave that's about to become
actionable (the parts with no unresolved `requires`); leave everything downstream of it as a single
coarse placeholder node with a one-line scope and a `depends_on` back to what must land first. When
that wave completes and a placeholder becomes the front of the queue, decompose runs again on it —
same skill, same discipline, informed by what the earlier wave actually produced. Never spend pass-1
budget detailing a wave 3+ steps away; the information to cut it well doesn't exist yet.

## Owner ≠ solo actor

"One owner" means one accountable identity for the DONE/BLOCKED/NEEDS-REDISPATCH contract on that
node — the owner may spawn its own internal team to execute (a supervisor pattern nested one level
down). What makes a cut wrong is not "more than one agent touches this," it's "the orchestrator
above this DAG has to reach inside the node to know what's happening." If you're tempted to add
`depends_on` edges _within_ what should be one subtask just to track its internal sequencing, that's
a sign that work belongs to the subtask's own supervisor, not to this DAG.

## Worked mini-example (shape, not a template to copy)

An epic that spans a librarian pass, a strategist pass, and three parallel author-owned build steps,
gated once before merge:

| id | subtask          | scope (one line)                                      | door        | depends_on |
| -- | ---------------- | ----------------------------------------------------- | ----------- | ---------- |
| A1 | Gather context   | One-line scope naming the deliverable                 | two-way     | —          |
| A2 | Build part X     | Owner-assignable, session-sized                       | two-way     | A1         |
| A3 | Build part Y     | Owner-assignable, session-sized, no data dep on A2    | two-way     | A1         |
| A4 | **GATE: review** | Distinct evaluator judges A2+A3 against the epic's AC | two-way     | A2, A3     |
| A5 | Merge            | Irreversible — human authorisation required           | **one-way** | A4         |

Note what makes this a correct cut: A2/A3 are parallel because neither's _start_ needs the other's
_output_ (only true data dependencies sequence); the gate is a node, not a bullet in A5's body; A5
is flagged one-way because merge is irreversible, and its gate (A4) sits before it, not folded into
it. A full worked specimen at epic scale — with an earn-its-keep record and a composed regime
alongside the DAG — is [[aops_d6ae35af]] §Pass-1 decomposition; read it for the reasoning, not as a
row-by-row script.

## The return contract this cut must support

Every DAG node the orchestrator wires must be able to return exactly one of:

- **DONE** + deliverable + evidence
- **BLOCKED** + what's missing
- **NEEDS-REDISPATCH** + what changed

If a proposed subtask can't cleanly emit one of these three without the orchestrator reaching into
its internals to figure out which applies, the boundary is drawn wrong — usually because it bundles
two responsibility boundaries or skips a true dependency. Re-cut before persisting.
