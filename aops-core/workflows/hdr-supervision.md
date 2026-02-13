---
id: hdr-supervision
name: hdr-supervision
category: academic
bases: [base-task-tracking]
description: Conventions and workflows for HDR student supervision and administration.
tags: [academic, hdr, supervision, conventions]
---

# HDR Supervision Workflow

Conventions for managing HDR (Higher Degree by Research) students, including directory structures, task categorization, and common workflows.

## Directory Convention

All student-specific documents should be stored in:

`$ACA_DATA/hdr/{student}/`

- **{student}**: Lowercase, sanitized surname or first name (be consistent).
- **When to use**: Store thesis drafts, meeting notes, supervision agreements, and student-specific reference materials here.

Example: `$ACA_DATA/hdr/kashyap/Chapter1-feedback.md`

## Task Categorization

- **Project**: Always use `project=hdr` for tasks related to student supervision.
- **Do NOT use**: The `supervision` project is deprecated for student-specific tasks; use `hdr` instead.
- **Tags**: Use `#supervision`, `#{student}`, and `#review` as appropriate.

## Google Docs Access Pattern

Google Docs are common for collaborative writing with students.

1. **Accessing Content**:
   - Use `web_fetch` to read the content of public or shared Google Docs.
   - For private docs requiring authentication, use `rclone` or `Playwright` via the shell if configured.
2. **Download & Convert**:
   - When a student shares a Google Doc for review, download it (e.g., as `.docx`) and convert to markdown using `pandoc` for storage in `$ACA_DATA/hdr/{student}/`.
   - Maintain the link to the original Google Doc in the task body and the markdown file metadata.

## Reference Letter Workflow

Reference letter requests follow a standard four-stage workflow.

See [[reference-letter]] for the detailed procedure.
