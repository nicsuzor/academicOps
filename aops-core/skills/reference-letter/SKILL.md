---
name: reference-letter
category: academic
description: Draft, review, and finalize reference letters for students, colleagues, and collaborators
allowed-tools: Read,Write,Edit,AskUserQuestion,mcp__pkb__search,mcp__pkb__create_task
version: 1.0.0
---

# Reference Letter Skill

Standard procedure for drafting, reviewing, and finalizing reference letters.

**Not HDR-specific.** This skill handles reference letters for students, colleagues, collaborators, and anyone else. For HDR-specific supervision workflows, see `/hdr`.

## When to Use

- Reference letter request received (usually via email)
- Letter needed for job application, scholarship, fellowship, promotion

## Phases

### 1. Gather Materials

Ask the applicant for:
- Their current CV
- The position description or scholarship details
- Their draft of the letter (if providing one)
- Specific points they want highlighted

Store materials in `$ACA_DATA/references/{name}/{date}/`.

### 2. Draft

- Use a previous letter as template if appropriate
- Draft in markdown with: date, recipient, salutation, body, closing, signature block
- Match the user's writing voice (warm, direct, collegial)

### 3. Review and Generate PDF

- Self-review for tone and accuracy
- Insert signature image reference
- Generate PDF: `Skill(skill="pdf", args="path/to/letter.md --type letter")`

### 4. Finalize and Send

- Verify PDF formatting
- Draft email with PDF attached, or upload to portal
- Mark task as done
- Archive materials in `$ACA_DATA/references/{name}/`
