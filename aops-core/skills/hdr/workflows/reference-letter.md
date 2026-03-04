---
title: Reference Letter Workflow
type: automation
category: instruction
permalink: workflows/reference-letter
tags: [hdr, reference-letter, workflow, supervision]
---

# Reference Letter Workflow

Process for handling reference letter requests from HDR students or for HDR students.

**When to Use**: Student requests reference letter for job, scholarship, or other opportunity.

**Detailed procedures and templates**: See **[[hdr-reference-details]]**.

## Workflow Steps

1. **Create Task**: Use `mcp__pkb__create_task` with the standard HDR reference letter template. Link to HDR project and set deadline.
2. **Create Draft File**: Create the reference letter draft at `$ACA_DATA/hdr/{student}/reference-{purpose}-{year}.md` using the standard YAML metadata and draft template.
3. **Link Task to Draft**: Update the task body to include a wikilink to the new draft file.
4. **Gather Context**: Gather supporting materials (application statement, requirements) and search memory for student's achievements. Add relevant context to the draft.
5. **Human Review and Completion**: Human writer edits content, signs, and sends the reference.
6. **Complete Task**: After sending, mark the task complete and update the draft file status to `sent`.

## Storage Convention

All reference letters are stored at `$ACA_DATA/hdr/{student}/` with the format `reference-{purpose}-{year}.md`.

## Error Handling

- **Missing deadline**: Default to P1 priority, ask user to confirm deadline.
- **No student directory**: Create `$ACA_DATA/hdr/{student}/` (lowercase first name).
- **Requirements unclear**: Flag for human clarification in the task body.

**Agent boundary**: The agent prepares the task and draft; the human writes, signs, and sends the reference.
