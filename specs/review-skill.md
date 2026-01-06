---
title: Review Skill Specification
type: spec
category: spec
permalink: review-skill
description: Specification for the agentic review skill, distinguishing support from judgment.
tags:
  - skill
  - supervision
  - review
---

# Review Skill Specification

**Date**: 2026-01-05
**Status**: Active

## Problem Statement

Reviewing academic drafts requires a distinction between **structural support** (preparation, checking references, identifying gaps) and **critical judgment** (nuance, tone, evaluation). Agents often conflate these, offering "corrections" based on training data that override the user's specific academic expertise.

We need a skill that explicitly acts as a **Research Assistant**, clearing the path for the user to make judgments, rather than a **Co-Author** trying to fix the text.

## Core Axiom: Support vs. Judgment

-   **Support (Agent Role)**: "Here is where the author mentions X. Here is the list of speakers at the conference they asked about."
-   **Judgment (User Role)**: "This argument is weak because..."

## Scope

### In Scope
-   **Preparation**: Converting inputs to Markdown, ensuring line-number addressability.
-   **Guidance**: Creating `reading_notes` that map user questions to text locations.
-   **Scribing**: Drafting responses based on user's rough notes/dictation.
-   **Logistics**: Checking external links (conferences, cited papers) for basic facts.

### Out of Scope
-   **Critique**: The agent should not offer qualitative feedback (e.g., "This is well written") unless explicitly asked to simulate a specific persona.
-   **Editing**: No direct edits to the author's draft unless instructed to "fix typos".

## Workflow Structure

1.  **Assemble**: Ensure `${ACA_DATA}/reviews/[author]/` contains search-ready Markdown patterns.
2.  **Map**: Create `YYYYMMDD_reading_notes.md` mapping the author's anxieties/questions to specific lines.
3.  **Scribe**: Iterate on the task file `YYYYMMDD_task.md` to draft the response.
4.  **Finalize**: Append response to task, mark complete, move to review folder.

## Success Criteria

-   **User Cognitive Load**: The user does not need to "search" for the relevant section; they are directed straight to it.
-   **Voice Preservation**: The final output sounds exactly like the user (authoritative, specific), not like an LLM (generic, overly polite).
-   **Artifact Hygiene**: Inbox is clear; review history is preserved in the author's folder.
