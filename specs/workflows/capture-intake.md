---
id: workflows-capture-intake
title: Capture Intake — Mobile/Webhook Pickup into the PKB
type: spec
category: workflow
status: draft
tags: [spec, workflow, capture, intake, pkb, q]
related:
  - workflows-reconcile
  - quick-capture
  - graph-hygiene
---

# Capture Intake

Nic's two capture front ends (VSCode task, iOS Shortcut) already commit raw notes into the PKB
with no processing at capture time -- built, and not this spec's concern (`quick-babf1cd6`). What
has no owner is pickup: turning a landed capture into a graph node. Today that only happens by
hand, at `/daily` step 1.5, when a `/daily` run happens to occur. This spec designs the standing
route that picks pickup up automatically, and states why it needs no new PKB write capability to
do it.

## Coverage

| Piece                                                               | State                                              |
| ------------------------------------------------------------------- | -------------------------------------------------- |
| Capture front ends land raw notes as PKB documents (`type: note`)   | Built -- `quick-babf1cd6`                          |
| Manual triage (Task / Note / Expand / Discard) at `/daily` step 1.5 | Built -- remains the fallback this route defers to |
| Standing, automated pickup sharing the `/reconcile` trigger         | **Not built -- this spec's target shape**          |

## The completion-marker problem, and why it dissolves

`processed: true` cannot be written through the PKB MCP surface: `update_task` rejects unknown
frontmatter keys, and the write tools available to an agent expose only status, priority, project,
assignee, and tags. Extending the write surface to accept an arbitrary `processed` boolean is a
service-side change outside a skill's reach, and it would duplicate state the graph can already
express for free.

**Decision: deletion is the completion signal, not a frontmatter flag.** A capture note's
existence in the PKB _is_ "pending." Once it is routed -- folded into a task, folded into a note,
or judged not worth keeping -- it is deleted outright, the same "no tombstone, git holds the
history" doctrine `/reconcile` already applies to harvested tasks (`kb_graph_hygiene_rules`,
Rule Set 2). This needs zero new PKB write capability: `pkb__delete` already exists and already
does this job for the analogous case. It also drops the query problem reconcile's PR sweep has to
solve with a windowed event log -- there is no window to track. Every run simply processes whatever
capture notes currently exist; nothing is skipped because a previous run missed it, because a
previous run either routed it (and it no longer exists) or left it (and it is still there,
unambiguously pending).

This supersedes `quick-babf1cd6`'s description of `processed: true` as the completion marker for
anything this route reaches. `/daily` step 1.5 is unaffected in mechanism -- it still triages
whatever capture notes it finds -- it simply finds fewer of them, because this route already
cleared the confident cases.

## Routing procedure (target shape)

**Grain:** one capture note is one unit of judgment, matching `/reconcile`'s per-task grain.

**Owner:** `pkb:q` -- the existing Stage 1 Intake & Capture skill already does exactly this job for
a natural-language ask (classify, parent, search-and-adopt, densify, value at intake). This route
invokes it; it does not reimplement classification, parenting, or valuation logic. One canonical
owner, per the same constraint `/reconcile`'s spec states for closure-loop logic.

**The interactive/headless gap.** `/q` assumes a user is present to disambiguate: unclear
classification or an ambiguous parent is worked out with `AskUserQuestion`. A capture note picked
up on the `/reconcile` timer has nobody watching -- that call would hang. `/q` needs a second
invocation context for this, alongside its implicit interactive one, on the same pattern
`/reconcile` already uses for its three contexts (input subset changes, procedure does not):

| Context                | Owner | Behaviour when classification/parenting is unclear                           |
| ---------------------- | ----- | ---------------------------------------------------------------------------- |
| Interactive (today)    | `/q`  | Asks, via `AskUserQuestion`.                                                 |
| Automated pickup (new) | `/q`  | Does not guess. Leaves the capture note untouched and moves to the next one. |

This is the answer to "what does the step do when a capture cannot be routed": nothing forced. The
note stays put, `/daily` step 1.5's existing manual triage is still there for it. No
`needs_user_call` event, no new surfacing mechanism -- the surface already exists and this route
defers to it rather than duplicating it.

**Per-capture disposition**, once classification is confident enough to proceed without asking:

- **Task.** `/q`'s normal path: search-and-adopt or create, parent, densify, value at intake.
- **Note.** Not an actionable ask -- resolve a destination via the Destination Rule
  (`kb_graph_hygiene_rules`, Rule Set 2 §2.1): an existing canonical topic note (synthesize in via
  `pkb__update_body`) or a new one (`pkb__create(type="knowledge", ...)`), never left as an
  unparented capture.
- **Expand.** Not a fourth destination type -- maps to the Task path with
  `classification: probe`, reusing `/q`'s existing uncertainty classification rather than inventing
  a new one.
- **Discard.** Neither an actionable ask nor a durable proposition. No destination to write or
  verify -- delete outright. This is the one disposition that skips the gate below, because there
  is nothing written elsewhere for it to protect.

**Before deleting a routed (non-discarded) capture**, run the same Pre-Deletion Verification Gate
`/reconcile` already applies (`kb_graph_hygiene_rules`, Rule Set 2 §2.2): confirm the destination
resolves, its `modified` timestamp is fresh, the content reads back, and any external references
are reparented. Only then `pkb__delete` the source capture note. A gate failure halts on that
capture and leaves it in place -- same abort semantics as the hygiene route, never a retry against
a different destination in the same pass.

## Trigger

Shares `/reconcile`'s trigger as a separate step, already recorded in
[`specs/workflows/reconcile.md`](reconcile.md#trigger) and stubbed as Step 2 of
`scripts/systemd-user/aops-reconcile-run.sh`: reconcile maintains truth about existing claims and
must not invent scope, while routing a capture is judgment work. Sharing the trigger shares the
cost of the read; sharing the pass would not. This spec does not re-litigate that decision
(`aops_reconcile_trigger`) or wire the entrypoint's placeholder line -- that lands with whichever
task builds `/q`'s Automated pickup context, since there is nothing to invoke before it exists.

## Out of scope

- The capture front ends themselves and their frontmatter shape (`quick-babf1cd6`).
- Legacy capture notes already sitting `processed`/undeleted, and the 17 files carrying
  `tags: [Array]` -- pre-existing data-quality debt tracked on `brain_7c711ec4`, not a backfill
  this route performs.
- Surfacing anything to Nic beyond what `/daily` step 1.5 already renders -- `aops_surface_updates_to_nic`'s
  concern if a gap remains once this lands, not assumed here.

## Landing milestones

- **M1 -- `/q` gains the Automated pickup context.** Documented in `plugins/pkb/skills/q/SKILL.md`
  as an invocation-contexts table on the pattern above; falls through instead of asking.
- **M2 -- Wired to the trigger.** `scripts/systemd-user/aops-reconcile-run.sh` Step 2's placeholder
  becomes a real `claude -p` invocation of the new context.
- **M3 -- First live run confirms a real delete.** Same discipline `aops_reconcile_trigger` set for
  reconcile's first write: before the timer is trusted unattended, one manual run must be confirmed
  to have exercised `pkb__delete` on a real capture note, not only reads.
