---
title: Capture Intake -- Mobile and Webhook Pickup into the PKB
type: spec
category: workflow
status: draft
tags: [spec, workflow, capture, intake, pkb, daily]
---

# Capture Intake

Capture front ends record raw notes into the knowledge base with no processing at capture time.
This specification defines the standing daily-run triage route that picks up captures waiting in
the intake directory, classifies each capture, and routes or disposes of it in place.

## User stories

### US-1 Autonomous daily triage of landed captures

As a knowledge base user capturing thoughts across mobile devices and front ends, I want unprocessed
captures triaged during the daily note run, so that incoming thoughts are classified and actionable
items reach my agenda without manual sorting.

- **AC-1.1** Given unprocessed capture files in `notes/mobile-captures/`, when the daily triage process
  runs, then every capture leaves the intake directory via in-place conversion or deletion.
- **AC-1.2** Given an empty capture intake directory, when the daily triage process runs, then the run
  completes cleanly with zero noise or warning.
- **AC-1.3** Given an actionable request capture, when triaged as a task, then the document is retyped
  and relocated into active tasks in place, retaining its original identifier and revision history.
- **AC-1.4** Given a capture folded into an existing note or task, when the destination write fails,
  then the source capture remains untouched in the intake directory.
- **AC-1.5** Given a capture triaged as a reference note, when the destination note write is confirmed,
  then the source capture note is deleted.

### US-2 Handling captures with unreadable or ambiguous intent

As a user dictating thoughts on the move, I want unreadable or ambiguous captures handled safely
during unattended daily runs, so that accidental noise is discarded while genuine thoughts are
preserved for clarification without stalling headless execution.

- **AC-2.1** Given a capture containing only transcription noise, empty input, or accidental fragments,
  when daily triage runs, then the capture is deleted.
- **AC-2.2** Given a capture containing substantive text whose actionability, parent, or destination
  cannot be resolved autonomously, when daily triage runs, then the capture is converted in place into
  an inbox probe task documenting the ambiguity, without halting execution for interactive prompts.
- **AC-2.3** Given voice-dictated captures, when phonetic or homophone transcription inaccuracies exist,
  then interpretation resolves meaning in context before evaluating for ambiguity.

## Design

### Placement and grain

The triage process runs as an autonomous step during daily note generation, executing early in the run
prior to agenda assembly, graph reconciliation, and state assembly. Running early ensures newly
converted tasks and probe items are indexed and available for downstream agenda synthesis and
reconciliation in the same run.

One capture note constitutes one unit of judgment.

### The unprocessed marker

A capture is unprocessed if and only if its file is in `notes/mobile-captures/`. There is no
`processed` metadata flag: front ends do not write one, and triage neither reads nor writes one.
A routed capture always leaves the intake directory by one of two moves:

- **In-place conversion:** The capture's file becomes the destination task or probe node, moved out of
  `notes/mobile-captures/` into the tasks directory while preserving its identifier.
- **Deletion:** The capture is deleted after its substantive content is placed in a destination topic
  note or task, or when judged not worth keeping (discard).

Every run processes all capture files present in the intake directory. When the directory is empty,
the step exits immediately without modifying documents or outputting log entries.

### Per-capture routing dispositions

Every capture is evaluated and routed to one of four dispositions:

- **Task:** An actionable request or project task. The document is converted in place into an active
  task: the file is moved out of the intake directory into the tasks directory, retyped as a task, and
  assigned an imperative title, concise body, parent container, and intake valuation edges. Its
  unique identifier and git history are preserved. When deduplication identifies an existing open task
  already carrying the ask, the capture's content is synthesized into that existing task, and the
  source capture is deleted under the deletion gate.
- **Note:** A durable reference, observation, or non-actionable insight. Content is synthesized into an
  existing canonical topic note or written as a new topic note. Once the destination write is
  verified, the source capture is deleted under the deletion gate.
- **Expand:** Substantive content whose requirements, scope, or actionability need investigation or
  clarification before becoming an active task or note. Converted in place into an inbox probe task
  carrying a probe classification and documenting the captured text and open questions. When expanding
  an existing note directly, content is synthesized into that note and the source capture deleted under
  the deletion gate.
- **Discard:** Noise, accidental dictations, or uninterpretable fragments with no discernible
  substantive value. Deleted outright.

### Handling captures whose intent cannot be read

The daily note generation workflow executes headlessly and cannot pause for interactive user prompts.
When the triage process cannot autonomously determine the intent or destination of a capture:

- **Uninterpretable noise or accidental input:** Captures consisting of empty dictations, pocket noise,
  transcription gibberish, or meaningless fragments with no substantive content are routed to
  **Discard** and deleted outright.
- **Substantive text with ambiguous or unreadable intent:** Captures containing substantive text whose
  actionability, parent, or destination cannot be determined autonomously are routed to **Expand**
  with a probe classification. The document is converted in place into an inbox probe task documenting
  the raw capture and specific ambiguities requiring clarification. This ensures no genuine idea is
  lost or discarded, avoids stalling headless runs, and places the clarification onto the graph as an
  inspectable probe task.
- **Tool or infrastructure errors:** When a document conversion, update, or deletion fails, the affected
  capture remains untouched in the intake directory to fail loud and retry on the subsequent daily run.
  No partial mutations or silent fallbacks occur.

### Deletion gate

Before deleting any capture that is folded into another node (a topic note or an existing task), the
destination write must succeed and any external references must be updated. Only then is the source
capture note deleted. A failed destination write halts processing on that capture and leaves it intact
in the intake directory.

### Invariant and output constraints

- **ID and history preservation:** Converted tasks and probe nodes retain their original capture
  identifier and version history via in-place retyping and relocation. No duplicate replacement files
  are minted.
- **Log cleanliness:** The triage step outputs no execution logs, file manifests, or heartbeat
  breadcrumbs into the daily note body, adhering to daily note scannability and log-ban invariants.
