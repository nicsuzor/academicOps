---
title: Reference Letter Workflow
type: automation
category: instruction
permalink: workflows/reference-letter
tags:
  - hdr
  - reference-letter
  - workflow
  - supervision
---

# Reference Letter Workflow

Process for handling reference letter requests from HDR students or for HDR students.

## When to Use

- Student requests reference letter for job, program, scholarship, or other opportunity
- External party requests reference for a current/former student
- Rental or personal references for students

## Workflow Steps

### Step 1: Create Task

```python
mcp__pkb__create_task(
    task_title="Write {student}'s {purpose} reference letter",
    type="task",
    project="hdr",
    priority=1,  # Reference letters typically have deadlines
    due="{deadline}",  # ISO format: 2026-02-02T00:00:00+00:00
    tags=["reference", "{student-firstname}", "{purpose}"],
    assignee="nic",
    body="""# Reference Letter for {Student Name}

## Request Details

**For**: {Purpose - e.g., OII Summer Doctoral Programme}
**Deadline**: {Date}
**Send to**: {email or submission portal}
**Requested by**: {who asked}

## Reference File

Draft: [[hdr/{student}/reference-{purpose}-{year}.md]]

## Requirements

{Any specific criteria or questions to address}

## Checklist

- [ ] Review student's application/statement (if provided)
- [ ] Draft reference addressing requirements
- [ ] Final review and sign
- [ ] Send reference to {destination}
"""
)
```

### Step 2: Create Draft File

Create the reference letter draft at `$ACA_DATA/hdr/{student}/reference-{purpose}-{year}.md`:

```markdown
---
title: {Purpose} Reference Letter
for: {Student Full Name}
date: {today}
deadline: {deadline}
send_to: {email or portal}
status: draft
---

# Reference Letter for {Student Name}

**To**: {Recipient/Committee}
**From**: [Your name and title]
**Date**: [Date]
**Re**: Reference for {Student Name}, {Purpose}

---

Dear {Recipient},

I am writing to support {Student Name}'s application to {Program/Position}.

{Body of reference letter}

Yours sincerely,

{Signature block}
```

**File naming**: `reference-{purpose}-{year}.md`

- Examples: `oii-reference-2026.md`, `rental-reference-2024.md`, `job-reference-2026.md`

### Step 3: Link Task to Draft

Update task body to include wikilink to draft file:

```markdown
## Reference File

Draft saved: [[hdr/{student}/reference-{purpose}-{year}.md]]
```

### Step 4: Gather Context (Agent-Assisted)

If student has provided supporting materials:

1. **Application statement**: Include in task body for reference
2. **Requirements/criteria**: Document what the reference should address
3. **Google Doc links**: Note in task body (human must access directly)

Search memory for relevant context:

```python
mcp__pkb__search(query="{student name} research achievements")
```

Add relevant context to draft file to assist human writer.

### Step 5: Human Review and Completion

**Agent boundary**: The agent prepares the task and draft. The human:

- Writes/edits the reference content
- Signs the letter
- Sends via email or portal
- Updates task status

### Step 6: Complete Task

After sending:

```python
mcp__pkb__complete_task(id="{task-id}")
```

Update draft file status:

```yaml
status: sent
sent_date: {date}
```

## Reference Letter Types

| Type             | Purpose                                 | Typical Deadline |
| ---------------- | --------------------------------------- | ---------------- |
| Academic program | Summer school, PhD application, postdoc | 2-4 weeks        |
| Scholarship      | Funding applications                    | 2-4 weeks        |
| Employment       | Job applications                        | 1-2 weeks        |
| Rental           | Housing applications                    | 3-5 days         |
| Award nomination | Professional recognition                | 2-4 weeks        |

## Quality Checklist

Before sending, verify:

- [ ] Correct recipient name and title
- [ ] Student name spelled correctly
- [ ] Purpose/program name accurate
- [ ] Specific examples included (not generic praise)
- [ ] Requirements addressed (if criteria were specified)
- [ ] Contact details included for follow-up
- [ ] Signed appropriately

## Storage Convention

All reference letters stored at:

```
$ACA_DATA/hdr/{student}/
├── reference-oii-2026.md
├── reference-rental-2024.md
└── reference-job-2025.md
```

## Error Handling

**Missing deadline**: Default to P1 priority, ask user to confirm deadline

**No student directory**: Create `$ACA_DATA/hdr/{student}/` (lowercase first name)

**Requirements unclear**: Include "Requirements TBD" section in task, flag for human clarification
