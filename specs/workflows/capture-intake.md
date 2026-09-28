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
route that picks pickup up automatically, and the one PKB write capability it needs that does not
exist yet: converting a capture into a task in place.

## Coverage

| Piece                                                                        | State                                                  |
| ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| Capture front ends land raw notes in `notes/mobile-captures/` (`type: note`) | Built -- `quick-babf1cd6`                              |
| Manual triage (Task / Note / Expand / Discard) at `/daily` step 1.5          | Built -- remains the fallback this route defers to     |
| Standing, automated pickup sharing the `/reconcile` trigger                  | **Not built -- this spec's target shape**              |
| PKB write that moves, renames and retypes a document while keeping its ID    | **Not built -- blocks the Task disposition (see Gap)** |

## The unprocessed marker

**A capture is unprocessed if and only if its file is still in `notes/mobile-captures/`.** There
is no `processed` flag: front ends do not write one, and triage neither reads nor writes one. A
routed capture always leaves the directory, by one of two moves:

- **Task or Expand:** the capture's own file becomes the task -- moved out of the directory into
  the task location (see Routing procedure).
- **Note or Discard:** the capture is deleted after its content is placed (Note) or judged not
  worth keeping (Discard) -- the same "no tombstone, git holds the history" doctrine `/reconcile`
  applies to harvested tasks (`kb_graph_hygiene_rules`, Rule Set 2).

Every run processes whatever is in the directory. Nothing is skipped because a previous run missed
it: a previous run either routed it (it is no longer there) or left it (it is still there,
unambiguously pending). There is no window to track. `/daily` step 1.5 triages by the same rule --
whatever is in the directory -- and finds fewer captures because this route has already cleared the
confident ones.

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

- **Task.** The capture becomes the task in place: the same file and the same ID, moved out of
  `notes/mobile-captures/` into the task location, renamed to a task filename, and given task
  frontmatter (`type: task`, status, parent). `/q` then parents, densifies and values it at intake
  as it would a task it created. No new file is created and no note is left behind. If
  search-and-adopt finds an existing task that already carries the ask, the capture is folded into
  that task (`pkb__update_body`) and deleted under the gate below, as with Note.
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

**Before deleting a capture folded into another node** (Note, or Task folded into an existing
task), run the same Pre-Deletion Verification Gate
`/reconcile` already applies (`kb_graph_hygiene_rules`, Rule Set 2 §2.2): confirm the destination
resolves, its `modified` timestamp is fresh, the content reads back, and any external references
are reparented. Only then `pkb__delete` the source capture note. A gate failure halts on that
capture and leaves it in place -- same abort semantics as the hygiene route, never a retry against
a different destination in the same pass.

## Gap: no PKB write converts a document in place

The Task disposition needs one PKB write that, on an existing document ID, does all of: move the
file to another directory, rename it, and replace its frontmatter type -- keeping the ID and
reindexing. No tool on the PKB MCP surface does this. Of its 35 tools, only `pkb_create` takes a
placement parameter (`dir`: "Override subdirectory placement"), and only at creation. No update
tool (`pkb_update_task`, `pkb_batch_update`, `pkb_apply_consolidation_batch`, `pkb_update_body`,
`pkb_edit_body`) takes a path, directory or filename. `pkb_batch_merge` keeps a canonical ID but
archives the source file, so it cannot turn a capture into a task either. Whether
`pkb_update_task` accepts a `type` key has not been tested, and it would leave the file in
`notes/mobile-captures/` -- still reading as unprocessed -- if it did.

Triage does not work around this with raw git or filesystem edits of the brain repo, and does not
fall back to creating a new task and deleting the capture. Until the PKB tool exists, a capture
classified as Task or Expand stays in `notes/mobile-captures/`; Note and Discard proceed.

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
- Legacy capture notes still carrying a `processed` key, and the 17 files carrying
  `tags: [Array]` -- pre-existing data-quality debt tracked on `brain_7c711ec4`, not a backfill
  this route performs.
- Surfacing anything to Nic beyond what `/daily` step 1.5 already renders -- `aops_surface_updates_to_nic`'s
  concern if a gap remains once this lands, not assumed here.

## Landing milestones

- **M0 -- PKB in-place conversion.** The PKB service gains the write described under Gap.
- **M1 -- `/q` gains the Automated pickup context.** Documented in `plugins/ida/skills/q/SKILL.md`
  as an invocation-contexts table on the pattern above; falls through instead of asking.
- **M2 -- Wired to the trigger.** `scripts/systemd-user/aops-reconcile-run.sh` Step 2's placeholder
  becomes a real `claude -p` invocation of the new context.
- **M3 -- First live run confirms real writes.** Same discipline `aops_reconcile_trigger` set for
  reconcile's first write: before the timer is trusted unattended, one manual run must be confirmed
  to have converted a real capture into a task in place (same ID, file now outside
  `notes/mobile-captures/`) and to have exercised `pkb__delete` on a real capture, not only reads.
