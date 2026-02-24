---
name: hdr
category: instruction
description: HDR (Higher Degree Research) student task conventions, reference letter workflows, and document access patterns.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__pkb__create_task,mcp__pkb__update_task,mcp__pkb__search,mcp__pkb__create_memory
version: 1.0.0
permalink: skills-hdr
tags:
  - hdr
  - supervision
  - students
  - reference-letters
  - workflows
---

# HDR Student Skill

Manage HDR (Higher Degree Research) student-related tasks including supervision, reference letters, reviews, and document handling.

## Path Resolution

**CRITICAL**: This skill requires the `$ACA_DATA` environment variable to be set.

- `$ACA_DATA` points to the user's data directory

HDR data location: `$ACA_DATA/hdr/`

## Core Conventions

### 1. Task Creation for HDR Students

**MANDATORY**: All HDR student tasks MUST use `project=hdr`.

```python
mcp__pkb__create_task(
    task_title="Review Sadia's dissertation chapter",
    type="task",
    project="hdr",  # NOT "supervision", NOT "academic"
    tags=["sadia", "dissertation", "review"],
    assignee="nic"  # HDR tasks typically assigned to human
)
```

**Why**: HDR tasks are stored at `$ACA_DATA/hdr/tasks/` and use `hdr-` prefix for task IDs. Using the wrong project breaks routing and organization.

**Task ID format**: `hdr-{hash}-{title-slug}`

### 2. Directory Convention: `hdr/{student}/`

Student-specific files are organized by student name:

```
$ACA_DATA/hdr/
├── tasks/                    # HDR-related tasks
│   ├── hdr-abc123-review-sadias-chapter.md
│   └── hdr-def456-write-lucinda-reference.md
├── sadia/                    # Sadia Sharmin's files
│   ├── oii-reference-2026.md
│   └── rental-reference-2024.md
├── tegan/                    # Tegan's files
│   └── annual-planning.md
└── lucinda/                  # Lucinda's files
    └── (student-specific docs)
```

**When to create student directory**:

- Reference letters (stored as `{student}/reference-{purpose}-{year}.md`)
- Annual planning documents
- Thesis drafts or chapters for review
- Any student-specific artifact that doesn't belong in a task

**Naming convention**: Use lowercase first name only (e.g., `sadia/`, not `sadia-sharmin/`).

### 3. Google Docs Access Pattern

When HDR tasks involve Google Docs (common for shared drafts and feedback):

**In task body**, include the link clearly:

```markdown
**Link**: https://docs.google.com/document/d/1q-5VhWcNnWwtYjL5v-SWjT8rEUse6MkOHi9TMkAH-M4/edit
```

**Accessing Google Docs content**:

1. **For review/feedback tasks**: The human must access the Google Doc directly in browser. The agent cannot read Google Docs content automatically.

2. **If content needs to be in the repo**: Ask the user to:
   - Export as `.docx` and download
   - Use `/convert-to-md` skill to convert to markdown
   - Store result in appropriate `hdr/{student}/` directory

3. **For collaborative editing**: Keep work in Google Doc until finalized, then archive to repo.

**Current limitation**: No automated Google Docs MCP integration. Future enhancement may add `mcp__gdocs__read_document` capability.

### 4. Reference Letter Workflow

See `[[workflows/reference-letter]]` for the complete workflow.

**Quick reference**:

1. Create task with deadline: `project=hdr`, `tags=["reference", "{student}"]`
2. Create draft file: `$ACA_DATA/hdr/{student}/{purpose}-reference-{year}.md`
3. Link task to draft file in task body
4. Human reviews/edits/signs
5. Human sends via email
6. Complete task

## HDR Task Types

| Task Type           | Description                      | Typical Assignee |
| ------------------- | -------------------------------- | ---------------- |
| Reference letter    | Write recommendation for student | nic              |
| Dissertation review | Review chapter/draft             | nic              |
| Supervision inquiry | Respond to prospective student   | nic              |
| Final seminar       | Schedule and attend              | nic              |
| Annual planning     | Review annual plan with student  | nic              |

**Note**: Most HDR tasks are `assignee=nic` because they require human judgment and relationship management.

## Related Files

- Student list: `$ACA_DATA/projects/hdr/current-students.md`
- Project overview: `$ACA_DATA/projects/hdr/hdr.md`
- Reference workflow: `[[workflows/reference-letter]]`

## Error Handling

**Wrong project used**:

- If task created with `project=supervision` or `project=academic`: Update to `project=hdr`
- Move task file to correct location if needed

**Student directory missing**:

- Create `$ACA_DATA/hdr/{student}/` on first use
- Use lowercase first name only

**Google Doc inaccessible**:

- Note in task body that access requires user authentication
- Ask user to export/share content if agent needs to process it
