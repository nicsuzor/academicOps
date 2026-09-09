---
name: deep-research
description: Author deep-research prompts (Gemini, ChatGPT Pro, Perplexity) and capture outputs into the PKB with figure extraction, local vision transcription, frontmatter, and task wikilinks.
---

# Deep Research

Structure prompts for deep research tools and ingest outputs into the PKB.

## Routing

- **Authoring prompts**: User needs to formulate an investigation spike. Route to [[prompt-authoring]].
- **Capturing outputs**: User provides a Google Doc URL or ID from an external run. Route to [[pkb-capture]].

## Lifecycle Overview

1. **Frame spike task**: Create a PKB spike task containing the crafted prompt.
2. **Execute externally**: Run the prompt in Gemini Deep Research, ChatGPT Pro, or Perplexity.
3. **Capture**: Download document, transcribe rasterized equations/diagrams, and store as a knowledge note.
4. **Complete task**: Update sourcing task with `research_output` linking to the knowledge note.

## Prerequisites & Guardrails

- Require `rclone` configured with a `gdrive` remote (`rclone lsd gdrive:`).
- Preserve raw outputs and Works Cited blocks verbatim without summarisation.
- Transcribe diagrams and rasterized math via local vision; never send images to external OCR services.
- Present transcription maps for user confirmation before final note creation.

## Verification

1. Note exists under `knowledge/<topic>/` with valid frontmatter and wikilinks to sourcing tasks.
2. Every embedded figure has descriptive alt-text and exists at `figures/<note-id>/`.
3. Sourcing task has `research_output` pointing to note ID and status set to `done`.
