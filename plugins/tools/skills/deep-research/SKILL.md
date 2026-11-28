---
name: deep-research
description: Author deep-research prompts (Gemini, ChatGPT Pro, Perplexity) and capture outputs with figure extraction, local vision transcription, frontmatter, and wikilinks where the composed workflow selects PKB capture.
---

# Deep Research

Structure prompts for deep research tools and ingest outputs into the PKB or the destination specified by the composed workflow.

## Routing

- **Authoring prompts**: Formulate an investigation probe via `procedures/prompt-authoring.md`.
- **Capturing outputs**: Ingest a Google Doc URL or ID from an external run via `procedures/pkb-capture.md`.

## Lifecycle Overview

1. **Frame probe**: Craft the prompt (and create or update a PKB probe task when the composed workflow directs task tracking).
2. **Execute externally**: Run the prompt in Gemini Deep Research, ChatGPT Pro, or Perplexity.
3. **Capture**: Download document, transcribe rasterized equations/diagrams, and store at the destination directed by the composed workflow and task (e.g., a PKB knowledge note).
4. **Update tracking**: When the composed workflow selects PKB capture and task tracking, update the sourcing task per workflow instructions (e.g., linking `research_output` to the knowledge note).

## Prerequisites & Guardrails

- Require `rclone` configured with a `gdrive` remote (`rclone lsd gdrive:`).
- Gemini Deep Research accepts at most 10 file attachments per run; keep any source bundle for a Gemini run to 10 files or fewer.
- Preserve raw outputs and Works Cited blocks verbatim without summarisation.
- Transcribe diagrams and rasterized math via local vision; never send images to external OCR services.
- In interactive workflows, present transcription maps for user confirmation before final note creation; in headless workflows, proceed per task instructions and flag unclear items.

## Verification

1. Output note exists at the location directed by the composed workflow and task (default `knowledge/<topic>/<slug>.md` when PKB capture is selected), with valid frontmatter and wikilinks to sourcing tasks when applicable.
2. Every embedded figure has descriptive alt-text and exists in the designated figure directory (default `figures/<note-id>/` under the topic note directory when PKB capture is selected).
3. When the composed workflow directs sourcing-task updates, the task records the output link (e.g., `research_output` pointing to note ID) and workflow-specified completion status (such as `done`).
