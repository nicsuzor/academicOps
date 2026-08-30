---
id: review-response
type: template
kind: process
category: academic
description: Reply to reviewer comments in a Word document, showing how each was addressed in the updated draft — threaded docx comment replies
requires: [task-tracking]
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-review-response
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Review Response

**When to invoke**: a collaborator returns a docx with reviewer comments; an
updated draft incorporates their feedback; the task is to confirm — via a
threaded Word reply — how each point was addressed.

## Phase 1: Unpack and Catalogue

Extract XML, all comments (id/author/text), the thread structure (which
comments reply to which), and anchor text for each comment — essential for
vague comments like "not sure what this means".

## Phase 2: Classify and Reply

| Type                   | Reply approach                                         |
| ---------------------- | ------------------------------------------------------ |
| Actionable suggestion  | Terse: "Done." / "Fixed."                              |
| Thread reply           | Skip — address in the parent reply                     |
| Confirm/verify         | Show, don't tell — extract and quote actual evidence   |
| Structural feedback    | Brief: state what changed                              |
| Future-work suggestion | "Noted in Future Work."                                |
| Clarification request  | Fix the text at the flagged location, say what changed |

**Anti-patterns**: don't duplicate replies to sub-comments; don't cop out on
clarification requests with a pointer elsewhere; don't parrot the new text
back; match the author's voice (terse collaborators get terse replies).

## Phase 3: Gather Evidence (verification-type comments)

Pull the actual data/text, filter to the referenced instances, quote the
pattern with a count ("5/5 instances show X"). This is the most important part
— reviewers asking to "confirm" want evidence, not an assertion.

## Phase 4: Build Reply Comments (docx XML)

Add reply comments and thread markers; use the document owner as reply author;
for 30+ comments, script it rather than editing by hand — build a
`{parent_id: reply_text}` map, then a single pass over the document.

## Phase 5: Pack and Validate

Repack the docx against the original; always open in Word to confirm comments
render as threaded replies.

## Lessons

Start from a fresh unpack on retry — don't layer edits on a failed attempt.
Escape XML special characters in reply text. Be brief; save length for
evidence-bearing replies.
