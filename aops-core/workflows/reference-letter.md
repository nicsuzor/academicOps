---
id: reference-letter
name: reference-letter
category: academic
bases: [base-task-tracking]
description: Standard workflow for handling reference letter requests (request → draft → review → send).
tags: [academic, reference, letter, workflow]
---

# Reference Letter Workflow

Standard procedure for drafting, reviewing, and finalizing reference letters for students or colleagues.

## 1. Request Stage

When a request is received (usually via email):

1. **Create Task**: Create a task with `type: task`, `project: hdr` (for students) or `academic` (for others).
2. **Gather Materials**: Ask the applicant for:
   - Their current CV.
   - The position description or scholarship details.
   - Their draft of the letter (if they are providing one).
   - Any specific points they want highlighted.
3. **Store Materials**: Save documents in `$ACA_DATA/hdr/{name}/references/{date}/` or `$ACA_DATA/academic/references/{name}/`.

## 2. Drafting Stage

1. **Draft Letter**: Use a previous letter as a template if appropriate.
2. **Format**: Draft in markdown. Include:
   - Date
   - Recipient info
   - Salutation
   - Body paragraphs (justified)
   - Closing
   - Signature block placeholder
3. **Check Heuristics**: Ensure the draft follows the letter style defined in [[skills-pdf]].

## 3. Review & PDF Generation

1. **Review**: Self-review for tone and accuracy.
2. **Insert Signature**: Ensure the signature image is referenced correctly:
   ```markdown
   Yours sincerely,

   <img src="$ACA_DATA/assets/signature.png" style="height: 50px;" />

   Nicolas Suzor
   ```
3. **Generate PDF**: Use the PDF generation skill:
   ```bash
   uv run python scripts/generate_pdf.py path/to/letter.md --type letter
   ```

## 4. Finalize & Send

1. **Verify PDF**: Open and check the generated PDF for formatting issues.
2. **Send**:
   - If sending directly: Draft the email with the PDF attached.
   - If uploading to a portal: Navigate to the portal and upload the PDF.
3. **Complete Task**: Mark the task as `done`.
4. **Archive**: Move the markdown draft to `$ACA_DATA/archived/references/{name}/` if appropriate, or keep in student folder.
