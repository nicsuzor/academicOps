---
id: outbound-review-details
category: reference
description: Task creation template and extended guidance for outbound-review workflow
---

# Outbound Review — Details

## Task Creation Template

When decomposing a "share X" task, create subtasks like:

```
parent: <share-task-id>
children:
  - title: "Review: alignment — [deliverable name]"
    tags: [review, alignment, outbound-review]
    body: |
      Alignment review per [[outbound-review]] workflow.
      Deliverable: [path or description]
      Audience: [who will receive this]
      Purpose: [what decision/action this supports]
      [Paste alignment criteria from workflow]
  - title: "Review: quality — [deliverable name]"
    tags: [review, quality, outbound-review]
    body: |
      Quality review per [[outbound-review]] workflow.
      Deliverable: [path or description]
      Source data/code: [paths]
      [Paste quality criteria from workflow]
  - title: "Review: voice — [deliverable name]"
    tags: [review, voice, outbound-review]
    body: |
      Voice review per [[outbound-review]] workflow.
      Deliverable: [path or description]
      Audience: [who, their expertise level, their relationship to the work]
      [Paste voice criteria from workflow]
  - title: "Verify and send — [deliverable name]"
    assignee: nic
    depends_on: [alignment-id, quality-id, voice-id]
    body: |
      Review agent findings. Address FAIL/ESCALATE items. Send.
```

## Scaling

- **Minimum viable**: 3 agent reviews + 1 human verify (as above)
- **Extended**: Add domain-specific reviewers (e.g., legal review, data privacy review) as additional subtasks with the same PASS/FAIL/ESCALATE pattern
- **Light mode**: For low-stakes internal shares, a single agent can do all three dimensions in one pass — but the criteria must still be explicitly locked before review begins

## Anti-patterns

- **Reviewing your own work**: The agent that wrote the deliverable must NOT review it. Use fresh agents.
- **Rubber-stamping**: "PASS — looks good" without evidence citations is not a valid verdict.
- **Scope creep in review**: Reviews identify issues; they don't rewrite. If rewriting is needed, that's a separate task.
- **Skipping human gate**: Agents never send externally. Always route final send to human.
