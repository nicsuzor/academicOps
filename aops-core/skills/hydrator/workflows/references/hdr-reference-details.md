# HDR Reference Letter Detailed Procedures

Detailed templates, categories, and storage conventions for handling HDR reference letters.

## Task Template (Step 1)

```python
mcp__pkb__create_task(
    task_title="Write {student}'s {purpose} reference letter",
    type="task",
    project="hdr",
    parent="hdr-tasks-root",
    priority=1,
    due="{deadline}",
    tags=["reference", "{student-firstname}", "{purpose}"],
    assignee="nic",
    body="""# Reference Letter for {Student Name}

## Request Details
**For**: {Purpose}
**Deadline**: {Date}
**Send to**: {email or portal}
**Requested by**: {who asked}

## Reference File
Draft: [[hdr/{student}/reference-{purpose}-{year}.md]]

## Requirements
{Criteria to address}

## Checklist
- [ ] Review student's application/statement
- [ ] Draft reference addressing requirements
- [ ] Final review and sign
- [ ] Send reference to {destination}
"""
)
```

## Draft File Template (Step 2)

Create at `$ACA_DATA/hdr/{student}/reference-{purpose}-{year}.md`:

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
- [ ] Specific examples included
- [ ] Requirements addressed
- [ ] Contact details included
- [ ] Signed appropriately

## Storage Convention

All reference letters stored at `$ACA_DATA/hdr/{student}/`.
Filename format: `reference-{purpose}-{year}.md`
Examples: `oii-reference-2026.md`, `rental-reference-2024.md`.
