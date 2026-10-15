---
title: Capture Intake -- Mobile/Webhook Pickup into the PKB
type: spec
category: workflow
status: draft
tags: [spec, workflow, capture, intake, pkb, q]
---

# Capture Intake

Capture front ends commit raw notes into the PKB with no processing at capture time -- they are
supplied by the installer, and not this spec's concern. What
has no owner is pickup: turning a landed capture into a graph node. This spec defines the standing
route that picks up captures in `notes/mobile-captures/`, classifies each capture, and converts
task-like captures into tasks in place.

## Coverage

| Piece                                                                                          | State                                                               |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Capture front ends land raw notes in `notes/mobile-captures/` (`type: note`)                   | Installer-supplied                                                  |
| Manual triage (Task / Note / Expand / Discard) at `/daily` step 1.5                            | Built -- remains the fallback this route defers to                  |
| Standing, automated pickup context in `/q`                                                     | Built (`plugins/ida/skills/q/SKILL.md`)                             |
| PKB write that moves, renames and retypes a document while keeping its ID (`convert_document`) | Built in `nicsuzor/mem#659` (requires MCP `tools/list` publication) |

## The unprocessed marker

**A capture is unprocessed if and only if its file is still in `notes/mobile-captures/`.** There
is no `processed` flag: front ends do not write one, and triage neither reads nor writes one. A
routed capture always leaves the directory, by one of two moves:

- **Task or Expand:** the capture's own file becomes the task -- moved out of the directory into
  the task location (see Routing procedure).
- **Note or Discard:** the capture is deleted after its content is placed (Note) or judged not
  worth keeping (Discard) -- the same "no tombstone, git holds the history" doctrine `/reconcile`
  applies to harvested tasks.

Every run processes whatever is in the directory. Nothing is skipped because a previous run missed
it: a previous run either routed it (it is no longer there) or left it (it is still there,
unambiguously pending). There is no window to track. `/daily` step 1.5 triages by the same rule --
whatever is in the directory -- and finds fewer captures because this route has already cleared the
confident ones.

## Routing procedure

**Grain:** one capture note is one unit of judgment, matching `/reconcile`'s per-task grain.

**Owner:** `ida:q` -- the Stage 1 Intake & Capture skill (`plugins/ida/skills/q/SKILL.md`) owns
capture intake (classify, parent, search-and-adopt, densify, value at intake per [R1](graph-valuation.md#3-r1----placement-at-intake-q)). This route
invokes it; it does not reimplement classification, parenting, or valuation logic. One canonical
owner, per the same constraint `/reconcile`'s spec states for closure-loop logic.

**Dictation and homophones:** Mobile captures are often dictated by voice (`[[quick-babf1cd6]]`).
Before judging a capture's meaning or treating it as ambiguous, read it for phonetic or homophone
transcription errors in context.

**The interactive/headless gap.** Interactive `/q` disambiguates unclear classification or an
ambiguous parent with `AskUserQuestion`. A capture note picked up headlessly has nobody watching,
so `/q` exposes two invocation contexts on the same pattern `/reconcile` uses (input subset changes,
procedure does not):

| Context          | Owner | Behaviour when classification/parenting is unclear                           |
| ---------------- | ----- | ---------------------------------------------------------------------------- |
| Interactive      | `/q`  | Asks, via `AskUserQuestion`.                                                 |
| Automated pickup | `/q`  | Does not guess. Leaves the capture note untouched and moves to the next one. |

This is the answer to "what does the step do when a capture cannot be routed": nothing forced. The
note stays put, `/daily` step 1.5's existing manual triage is still there for it. No
`needs_user_call` event, no new surfacing mechanism -- the surface already exists and this route
defers to it rather than duplicating it.

**Per-capture disposition**, once classification is confident enough to proceed without asking:

- **Task.** The capture becomes the task in place: the same file and the same ID, moved out of
  `notes/mobile-captures/` into `tasks/`, renamed to a task filename, and given task frontmatter
  (`type: task`, `status`, `parent`, `project`, `links`). Invoke
  `convert_document(id=<capture-id>, type="task", status="ready"|"inbox")` to retype and relocate
  the document while pinning its ID, then invoke `update_task` and `update_body` to set a verb-led
  imperative `title`, minimal task body, parent container, and R1 valuation edges
  ([R1](graph-valuation.md#3-r1----placement-at-intake-q)). No second file is created and no note
  is left behind in `notes/mobile-captures/`. If search-and-adopt finds an existing task that
  already carries the ask, fold the capture into that task (`update_body`) and delete the capture
  under the gate below, as with Note.
- **Note.** Not an actionable ask -- resolve a destination: an existing canonical topic
  note (synthesize in via
  `update_body`) or a new one (`create(type="knowledge", ...)`), never left as an
  unparented capture.
- **Expand.** Not a fourth destination type -- maps to the Task path with
  `classification: probe` (`convert_document` followed by `update_task(classification="probe", ...)`
  and `update_body`), reusing `/q`'s existing uncertainty classification rather than inventing a new
  one. When expanding an existing note directly, synthesize into that note (`update_body`) and
  delete the capture under the gate below.
- **Discard.** Neither an actionable ask nor a durable proposition. No destination to write or
  verify -- delete outright via `delete`. This is the one disposition that skips the gate below,
  because there is nothing written elsewhere for it to protect.

**Before deleting a capture folded into another node** (Note, or Task folded into an existing
task), the destination write has succeeded and any external references are reparented. Only then
`delete` the source capture note. A failed destination write halts on that capture and leaves
it in place -- same abort semantics as the hygiene route, never a retry against a different
destination in the same pass.

## In-place conversion primitive (`convert_document`)

The Task and Expand dispositions use `convert_document` (`nicsuzor/mem#659`) to convert an existing
capture ID in place:

1. Pin the existing document `id` explicitly in frontmatter so renaming the file preserves identity.
2. Replace `type` with `"task"` (and set initial `status`, defaulting to `"inbox"` or `"ready"`).
3. Move and rename the file out of `notes/mobile-captures/` into `tasks/<id>-<slug>.md` (and on a
   subsequent `update_task(title=...)`, keep the filename slug aligned with the task title).
4. Re-index the node in the PKB graph under the same ID.

Triage does not work around an unavailable or failing `convert_document` tool with raw git or
filesystem edits of the PKB repo, and does not fall back to creating a new task and deleting the
capture. If `convert_document` is unavailable or returns an error, any capture classified as Task
or Expand stays untouched in `notes/mobile-captures/`.

## Trigger

Invoked as `/q`'s headless capture-intake context: routing a capture is judgment work belonging to `ida:q`.

## Out of scope

- The capture front ends themselves and their frontmatter shape.
- Legacy capture notes still carrying a `processed` key, and files carrying `tags: [Array]` --
  pre-existing data-quality debt, not a backfill this route performs.
- Surfacing anything to the user beyond what `/daily` step 1.5 already renders -- the update-surfacing task's
  concern if a gap remains once this lands, not assumed here.

## Landing milestones

- **M0 -- PKB in-place conversion (`nicsuzor/mem#659`).** `convert_document` moves, renames, and
  retypes a capture in place while keeping its ID.
- **M1 -- `/q` gains the Automated pickup context (`plugins/ida/skills/q/SKILL.md`).** Classifies
  each capture, converts task-like captures in place via `convert_document` + `update_task` /
  `update_body`, and leaves uncertain captures untouched instead of asking.
- **M2 -- Wired to automated pickup.** Standing invocation of the automated pickup context.
- **M3 -- First live run confirms real writes.** Before automated pickup is trusted unattended, one
  run must confirm a real capture converted into a task in place (same ID, file now outside
  `notes/mobile-captures/`) and `delete` exercised on a real capture.
