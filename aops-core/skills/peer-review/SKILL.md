---
name: peer-review
type: skill
description: >
  Peer review of research funding applications and academic submissions.
  Scheme-agnostic — fetches current criteria from the relevant handbook each
  round, since weights and language change. Covers Detailed Assessor and
  College-of-Experts / General Assessor roles, plus collegial draft review.
category: instruction
triggers:
  - "review this grant"
  - "review this application"
  - "future fellowship"
  - "DECRA"
  - "ARC assessment"
  - "ERC review"
  - "SNSF review"
  - "fellowship review"
  - "detailed assessor"
  - "general assessor"
  - "college of experts"
  - "process reviewer comments"
modifies_files: true
needs_task: true
mode: workflow
domain:
  - academic
allowed-tools: Read,Write,Edit,Grep,Glob,Bash
version: 2.0.0
permalink: skill-peer-review
---

# Peer Review Skill

Run peer reviews of research funding applications or academic submissions, matching the current round's scheme criteria and producing evidence-based feedback.

## Core Rules

- **Evidence-Based**: Every claim must cite the application (page, section, or quote).
- **Fetch Round Criteria**: Fetch current scheme guidelines (ARC, ERC, SNSF, NHMRC) for each round. Do not reuse prior criteria.
- **Conflict of Interest (CoI)**: Declare CoI immediately upon identifying institutional, personal, collaborator, supervisory, or financial relationships.
- **No AI-Text Policies**: Adhere to funding body policies (e.g., ARC) prohibiting AI-generated assessor text. Use the agent to organize, verify, and edit notes; the final text must reflect the user's voice.
- **No Integrity Allegations in Comments**: Route suspected research-integrity breaches to the scheme's integrity office separately.

## Workflow

### 1. Intake & CoI Check

- Read assignment details and capture: scheme/round, Application ID, candidate, institution, title, role (Detailed vs. General Assessor), and deadline.
- Create a task file: `YYYYMMDD-{scheme}-{appid}.md`.

### 2. Fetch Scheme Guidelines

Search PKB or external sources (e.g., GrantConnect, mySNF) for current round handbooks. Extract:

- Criteria, sub-elements, and weights.
- Scoring scale, band descriptors, and character limits.

### 3. Materials Assembly

- Download application PDF to `${ACA_DATA}/reviews/{scheme}/{appid}/`.
- Convert to line-numbered text: `pdftotext -layout {input}.pdf source.txt`.
- Build a section-to-line-range map in the working notes.

### 4. Reading Notes & Initial Pass

Generate `~/brain/reviews/{scheme}/{appid}/YYYYMMDD-reading-notes.md` containing:

- Mapping of criteria to line ranges.
- Basic factual claims made by the application.
- Clarification questions `[?]`.
- Structural anchors (aims, methods, budget summary).
- Anti-bias checklist.

### 5. Assessment & Quality Gate

Draft comments for each criterion following the scheme's scoring bands.

- Ensure all prose matches the assigned score.
- Criticize the proposal, not the person.
- Verify character limits are met.

### 6. Submission & Close-out

- Log in to the platform (RMS, mySNF, etc.), paste comments, verify counts, and submit.
- Update task to `status: done`, append final assessment to the task file, and archive the review folder.

## Scribe Mode (Collegial Drafts)

For reviewing draft papers/proposals written by colleagues:

1. Assemble materials in `${ACA_DATA}/reviews/[author]/`.
2. Generate `YYYYMMDD-reading-notes.md` mapping the author's questions to line numbers.
3. Draft feedback matching the user's voice (terse, specific, no hedging).

## References

- [[reviewer-roles]] — Role distinctions (Detailed vs General Assessor vs collegial)
- [[review-guidance]] — Taxonomy, scoring bands, tone, and anti-bias calibration
- [[review-template]] — Assessment file templates
- [[reading-notes-format]] — Reading notes layout
- [[platform-instructions]] — Submission platform tips
- PKB: search for `{scheme}-Assessor-Handbook` or `{scheme} Grant Guidelines`
