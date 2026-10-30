---
title: Capture Intake -- Mobile/Webhook Pickup into the PKB
type: spec
category: workflow
status: draft
tags: [spec, workflow, capture, intake, pkb, daily]
---

# Capture Intake

Capture front ends commit raw notes into the PKB with no processing at capture time -- they are
supplied by the installer, and not this spec's concern. What
has no owner is pickup: turning a landed capture into a graph node. This spec defines the standing
daily-run triage route that picks up captures in `notes/mobile-captures/`, classifies each capture, and converts
or disposes of captures in place.

## Coverage

| Piece | State |
| - | - |
| Capture front ends land raw notes in `notes/mobile-captures/` (`type: note`) | Installer-supplied |
| Daily-run triage step (Task / Note / Expand / Discard) in daily note workflow | Designed (this spec; pending template implementation) |
| PKB write that moves, renames and retypes a document while keeping its ID (`convert_document`) | Built in `mem#659` / PKB MCP |

## The unprocessed marker

**A capture is unprocessed if and only if its file is still in `notes/mobile-captures/`.** There
is no `processed` flag: front ends do not write one, and triage neither reads nor writes one. A
routed capture always leaves the directory, by one of two moves:

- **Task or Expand:** the capture's own file becomes the task -- moved out of the directory into
  the task location (see Routing procedure).
- **Note or Discard:** the capture is deleted after its content is placed (Note) or judged not
  worth keeping (Discard) -- the same "no tombstone, git holds the history" doctrine reconcile
  applies to harvested tasks.

Every run processes whatever is in the directory. Nothing is skipped because a previous run missed
it: a previous run either routed it (it is no longer there) or left it (it is still there,
unambiguously pending). There is no window to track.

## Daily-run triage step

**Placement:** Sits within the daily note generation workflow (Step 1.5, immediately following user
ask ingestion and preceding verbatim request situating). Running early ensures newly converted tasks
are indexed and available for downstream agenda, reconcile, and graph state assembly in the same run.

**Grain:** One capture note is one unit of judgment, matching reconcile's per-task grain.

**Dictation and homophones:** Mobile captures are frequently dictated by voice. Before judging a
capture's meaning or treating it as ambiguous, read it for phonetic or homophone transcription
errors in context.

**Per-capture disposition (the four routes):**

- **Task.** An actionable request or task. The capture becomes the task in place: the same file and
  the same ID, moved out of `notes/mobile-captures/` into `tasks/`, renamed to a task filename, and
  given task frontmatter (`type: task`, `status: ready` or `status: inbox`, `parent`, `project`, `links`).
  Invoke `convert_document(id=<capture-id>, type="task", status="ready"|"inbox")` to retype and
  relocate the document while pinning its ID, then invoke `update_task` and `update_body` to set a
  verb-led imperative `title`, minimal task body, parent container, and intake valuation edges.
  No second file is created and no note is left behind in `notes/mobile-captures/`. If search-and-adopt
  finds an existing open task that already carries the ask, fold the capture into that task
  (`update_body`) and delete the capture under the deletion gate below.
- **Note.** A durable reference, observation, or non-actionable insight. Resolve a destination:
  synthesize into an existing canonical topic note (`update_body`) or create a new topic note
  (`create(type="knowledge", ...)`), never leaving an unparented capture. Once the destination write
  is confirmed, delete the source capture under the deletion gate below.
- **Expand.** Substantive content whose scope, actionability, or requirements need elaboration,
  investigation, or clarification before becoming an active task or note. Maps to the Task path with
  `classification: probe` (`convert_document` followed by `update_task(classification="probe", ...)`
  and `update_body`), reusing the framework's standard uncertainty classification rather than
  inventing a new one. When expanding an existing note directly, synthesize into that note
  (`update_body`) and delete the capture under the deletion gate below.
- **Discard.** Neither an actionable ask nor a durable proposition. Outright deleted via
  `delete(id=<capture-id>)`. This is the one disposition that skips the deletion gate below, as there
  is no written artifact elsewhere to protect.

**Handling captures whose intent cannot be read:**
When the daily runner cannot autonomously determine the intent or destination of a capture:

- **Uninterpretable noise or accidental input:** Captures consisting of empty dictations, pocket
  noise, transcription gibberish, or meaningless fragments with no discernible substantive content
  are routed to **Discard** and deleted outright.
- **Substantive text with ambiguous or unreadable intent:** Captures containing substantive text
  whose specific actionability, parent, or destination cannot be resolved autonomously are routed
  to **Expand** with `classification: probe`. The document is converted in place via
  `convert_document(id=<capture-id>, type="task", status="inbox")`, assigned `classification: probe`,
  and given a body documenting the raw capture and the specific ambiguities requiring clarification.
  This ensures no genuine idea or request is lost or discarded, avoids halting headless execution
  with interactive prompts, and places the clarification onto the graph as an inspectable probe task.
- **Write failure / tool error:** If any tool call (`convert_document`, `update_body`, `delete`)
  fails during triage, the capture remains untouched in `notes/mobile-captures/` to fail loud and
  retry on the next daily run; it is never partially mutated or discarded.

**Deletion gate:**
Before deleting a capture folded into another node (Note, or Task folded into an existing task),
the destination write must succeed and any external references are reparented. Only then invoke
`delete` on the source capture note. A failed destination write halts on that capture and leaves
it in place in `notes/mobile-captures/` -- never attempting a silent fallback or retry against a
different destination in the same pass.

## Outcome-level build criteria

The daily-run triage step implementation must satisfy the following verifiable criteria:

1. **Exhaustive directory processing:** The step examines all files in `notes/mobile-captures/`.
   When the directory is empty, the step completes cleanly with zero noise or warning.
2. **Deterministic exit from capture directory:** Every processed capture leaves
   `notes/mobile-captures/` -- either by relocation and retyping in place via `convert_document`
   (Task, Expand) or by deletion following successful destination placement or discard (Note, Discard).
3. **ID and history preservation:** Converted tasks and probe items retain the original capture's
   ID and git revision history via `convert_document`; no duplicate replacement files are minted.
4. **Verifiable routing of unreadable intent:** Pure noise is deleted (Discard); substantive but
   unreadable or ambiguous captures are converted in place to probe tasks (`classification: probe`)
   under Expand, preserving content on the graph without blocking headless runs.
5. **Pre-deletion destination verification:** No capture note is deleted when folded into another
   document unless the destination write (`update_body` or `create`) has succeeded.
6. **Fail-fast integrity on tool errors:** If `convert_document` or destination updates encounter
   an error, the affected capture remains untouched in `notes/mobile-captures/` and an error is surfaced;
   no fallback file operations or silent swallows occur.
7. **Cleanliness and no log pollution:** The triage step outputs no execution logs, file manifests,
   or heartbeat breadcrumbs into the daily note body, adhering to daily note scannability and
   log-ban invariants.

## In-place conversion primitive (`convert_document`)

The Task and Expand dispositions use `convert_document` (`mem#659` / PKB MCP) to convert an existing
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

## Out of scope

- The capture front ends themselves and their frontmatter shape.
- Legacy capture notes still carrying a `processed` key, and files carrying `tags: [Array]` --
  pre-existing data-quality debt, not a backfill this route performs.
- Surfacing anything to the user beyond what the daily note and reconcile already render.

## Landing milestones

- **M0 -- PKB in-place conversion (`mem#659` / PKB MCP).** `convert_document` moves, renames, and
  retypes a capture in place while keeping its ID.
- **M1 -- Daily triage step design in `capture-intake.md` (Stage 1 PR).** Design specification and
  outcome-level build criteria defined.
- **M2 -- Daily triage step implementation in daily template and step registry (Stage 2).** Update
  daily note template and step documentation in the PKB.
- **M3 -- Live run verification against waiting mobile captures (Stage 3 QA).** Verification of
  triage execution against actual waiting captures in the brain repository.
