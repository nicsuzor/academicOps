---
id: human-approval
kind: gate
category: quality-assurance
description: One-way-door gate requiring a distinct, named human authorisation before crossing — the terminal gate for anything irreversible
door-type: one-way
stakes: An irreversible or highly consequential action (merge to a protected branch/production, external send, spending, deleting durable data, a legal/compliance commitment) executes on agent judgment alone, with no independent human sign-off.
skip-when: The action is two-way-door (cheaply reversible), or it is already covered by a standing, on-record authorisation for this exact class of action (cite the authorisation — don't infer one).
requires: []
pairs-with: [qa, outbound-review]
recommends: [decision-briefing]
conflicts: []
version: 1.0.0
permalink: workflows-gates-human-approval
---

# Gate: Human Approval

**Status**: newly authored — this gate was a flagged gap in the migrated
library (no template previously named the one-way-door human-authorisation
obligation as a reusable unit; it existed only as ad hoc language scattered
across [[outbound-review]] step 4, `base-handover`, and various "always ask
first" rules). Model consumers (e.g. human-gated merge) compose this directly.

## Core Principle

**Agent judgment crosses two-way doors. Only a named human crosses a one-way
one.** This gate exists to make that crossing legible and auditable — not to
gatekeep every action, only the ones that can't be undone by a subsequent
agent turn.

## Pattern

1. **Identify the door.** State explicitly what is about to become irreversible
   (production deploy, sent email, deleted record, signed commitment) and why
   it can't be cheaply undone.
2. **Package the ask**, not a wall of context: what's being authorised, the
   evidence that it's ready (pointers to the [[qa]] / [[outbound-review]]
   verdicts that preceded this gate), and the specific consequence of saying
   yes. If there are real options rather than a single yes/no, compose
   [[decision-briefing]] to frame them instead of assuming one path.
3. **Wait for an explicit, on-record authorisation** from the named human —
   not an inferred green light from earlier, unrelated approval, and not a
   default in the absence of a reply. Silence is not consent.
4. **Record the authorisation** (who, when, what was authorised) alongside the
   action it gates, so the crossing is traceable after the fact.
5. **Cross once, for the stated scope only.** A single approval authorises the
   named action; it does not stand as blanket cover for adjacent one-way
   actions later in the same session.

## Declared stakes

**Door-type**: one-way, by definition — this is the gate door-type policy
selects _into_ when the action itself is irreversible. **Conditions**: applies
to actions a competent principal would want to personally sign off on given
the downside of getting it wrong (not to every action a human happens to be
present for). **Skip-conditions**: two-way-door work should never route here —
composing this gate on reversible work is itself a miscalibration (disproportionate
process, not caution). A prior standing authorisation for this exact class of
action (e.g. "you may always merge green CI on docs-only PRs") also skips —
but the authorisation must be named and on record, not assumed.

## Anti-patterns

- Treating a green [[qa]] verdict as sufficient — QA judges correctness, this
  gate judges _who bears the consequence_ of being wrong.
- Batching multiple one-way actions under a single approval ask ("approve
  these five deploys") when they don't share the same risk profile.
- Re-using an old approval as cover for a new, similar-looking action.
