# Delegation Brief — fill-in shape

This is a shape to write prose into, not a form to fill mechanically. Each element below is a
paragraph or a short set of sentences — not a checklist, not a step list. Copy the headings; write
the content the way you'd explain the assignment to a capable colleague who is about to walk in cold
and won't get to ask you a follow-up question.

Append this under the subtask's existing task body (which already carries decompose's one-line
scope, dependencies, and door-type — don't repeat those verbatim, build on them).

---

## Intent

State the end-state in one or two sentences, and _why it matters_ — how this subtask serves the
parent epic's goal. The why is what lets the executor improvise correctly when they hit a fact you
didn't anticipate. "Fix the login bug" is not intent; "users on the mobile app currently can't
authenticate at all, which blocks the whole onboarding funnel this epic exists to unblock" is.

## Scoped context

List the specific things the executor needs to open to start cold — spot-checkable: task ids, spec
sections, prior-decision node ids, the two or three files most likely relevant (marked as a
starting guess, not a verified code path — see Constraints below). This is a short list, not a
literature review. Deliberately leave out the epic's broader strategic reasoning, competing options
that were considered and rejected, and political/organisational context — none of that sharpens the
executor's tactical judgment on this specific piece of work, and including it invites second-guessing
of decisions that are already settled.

If you had to refresh hydration before writing this section, say what changed since the last bundle
in one sentence — that's itself useful context for the executor.

## Constraints (left/right limits)

Say what must not change and what's explicitly out of bounds — the boundary of the sandbox, not the
path through it. If you name a file or function as the likely code path, mark it unverified
("confirm this is actually what runs before editing it") rather than asserting it — over-specifying
an implementation anchors the executor on a mental model that may be wrong and masks the real
problem when it diverges.

## Autonomy + non-goals

Name what the executor decides on their own authority (implementation approach, which of several
reasonable fixes to apply, how to structure the change) and what is explicitly not theirs to decide
or do (e.g. "don't touch the auth config — that's a separate one-way-door subtask", "don't merge —
that's the regime's job"). Non-goals prevent scope creep into adjacent, already-owned territory.

## Done + acceptance criteria

Observable, set now — not left for the executor to infer at hand-in time. Lead with the outcome to
verify ("after your fix, X should behave like Y, confirmed by doing Z") rather than the edit you
imagine produces it. Name the concrete check the executor runs against the real surface (a test, a
screenshot, a before/after diff) so "done" means observed-changed, not merely edited. Never a
step-by-step script — the one exception is a strict READ-DO sequence, and only when the work is
genuinely order-critical or dangerous (irreversible operations, sequencing that matters for
correctness, not just habit).

## Emit for evaluation

Three things the executor must hand back, so a separate evaluator can reach a verdict from the
emitted evidence alone, without re-investigating:

- **Quality rubric** — what "good" looks like for this deliverable, beyond mere AC compliance
  (matches the door-type's stakes: a two-way-door draft needs less than a one-way-door release).
- **Claim-provenance rule** — the executor must keep "observed this session" separate from
  "inferred"; a claim without a citable check (a command run, a file read, a test executed) is not
  evidence.
- **Procedural record** — which regime steps (from decompose's composed process) were actually
  followed, so compliance review doesn't require re-deriving what should have happened.

Missing or thin evidence here is itself a FAIL condition for the evaluator — say so if the stakes
warrant spelling it out explicitly.

## Effort budget + door-type

Carry forward the door-type decompose already assigned to this subtask (`one-way` / `two-way`) —
don't reclassify unless something you learned while briefing changed the reversibility call, and if
you do reclassify, say what changed and why. Give a rough size (single session vs. needs its own
internal team) so the executor calibrates ambition correctly — this should already roughly match
decompose's "session-sized" cut; flag it if briefing revealed the cut was wrong-sized, rather than
silently absorbing the mismatch.
