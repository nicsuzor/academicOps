---
id: reference-letter
type: template
kind: process
category: academic
description: Draft, review, and finalize reference letters for students or colleagues (request → draft → review → send)
requires: [task-tracking]
pairs-with: [wf-handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-reference-letter
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Reference Letter

## 1. Request

Create a task. Gather materials from the applicant: current CV, position/
scholarship description, their own draft (if any), points to highlight. Store
in the applicant's data folder.

## 2. Drafting

Use a prior letter as a template where appropriate. Markdown format: date,
recipient info, salutation, justified body paragraphs, closing, signature-block
placeholder. Follow the letter style referenced by the PDF-generation skill.

## 3. Review & PDF Generation

Self-review for tone and accuracy. Insert the signature image reference
correctly. Generate the PDF via the PDF-generation skill.

## 4. Finalize & Send

Open and check the generated PDF for formatting issues. Send directly (draft
email with PDF attached) or upload to the relevant portal. Mark the task
`done`. Archive the markdown draft.

## NOT this template

- General review/feedback work → the `peer-review` skill
