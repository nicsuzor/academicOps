# Dispatch Rules

Universal dispatch rules for any orchestrator or coordinator. These rules apply whether the
dispatcher is the supervisor skill, Junior, or any other agent composing work briefs. Machine-
and host-specific invocation details belong in the PKB (see `remote-polecat-tmux-dispatch`),
not here.

## Dispatch Reflex — Expand Terse Instructions

When a principal gives a compressed coordination instruction (e.g. _"dispatch `<task-id>` in
parallel on a single PR"_), do **not** execute it literally and do **not** make them spell out
the mechanics. Two-step reflex:

1. **Recognise the gap.** Notice the instruction implies a coordination contract that may not have
   a standard procedure recorded — say so plainly if needed.
2. **Expand + deliver.** Turn the terse instruction into a full dispatch brief: identify what is
   parallel-able vs sequentially dependent, set the dependencies, and delegate each component.

The expansion is the orchestrator's job. The principal says one line and trusts the orchestrator
to produce the brief. This is a universal rule — it binds Junior, the supervisor, and any other
agent acting as coordinator.

## Pre-Dispatch Gates

All dispatches run through the pre-dispatch gates in
[[../instructions/worker-dispatch#mandatory-pre-dispatch-gates]]:

0. **Premise Gate** (hard refuse, runs first): Confirm the task body carries a genuine premise
   judgment before spending any compute.
1. **Pre-flight Confirmation Summary** (Code/Edit or Design/Spec/Research variant): 5-row table
   validating task ID, source repo, project field, chain position, and sanctioned mechanism.
2. **Existing PR check**: Is a PR already linked to this task?
3. **Critic Gate**: For high-blast-radius tasks — irreversible, production-scope, or
   disproportionate blast radius — gate with pauli before dispatch.

## Compose-then-Dispatch Separation

The agent authoring a brief must not dispatch against it. See
[[subagent-contracts#compose-then-dispatch-separation]] for the full protocol.

## Reviewer-Brief Neutrality — never pre-endorse an option to a reviewer

When the dispatch is a **review** (rbg / pauli / marsha / `/strategic-review`), the brief must
present the artifact and the question **without nominating a preferred answer**. Do not write
_"verify Option A (the recommended option)"_, _"confirm this is sound"_, or otherwise steer the
reviewer toward a conclusion — a leading brief degrades the independence the review exists to
provide. A pre-endorsed option re-frames the reviewer's job from _"is the premise sound?"_ to
_"audit the implementation of the option I already blessed,"_ and the premise sails through
unexamined. State the artifact, the decision under review, and the open question; let the
reviewer's own premise-test (step 0) fire on the **whole** premise, including the trigger and the
shape, not just the slice you flagged. If the upstream brief already carries a recommendation,
strip or neutralise it before handing the artifact to the reviewer.

## Dispatch Surfaces

The discipline is surface-independent. Implementation:

- **polecat surface**: bash invocation with `polecat run`. See
  [[cohesive-pr-epic#canonical-dispatch-command-polecat-surface]] for the template.
- **Agent-tool surface**: `Agent(subagent_type=…, run_in_background=True)`.
- **Jules surface**: `pkb task <task-id> | jules new --repo <owner>/<repo>`.

The capped handback contract (see [[subagent-contracts#worker-handback-format]]) applies on
all surfaces.
