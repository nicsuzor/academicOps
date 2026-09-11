---
name: workflow-create
description: Convert a user-approved process into a reusable workflow template in the template library. Use when capturing completed workflows for repeatable use. Exclude for unapproved or speculative workflows.
---

# /workflow-create -- Convert an approved process into a template

Extract the structural architecture of a completed, user-approved process and author a reusable workflow template in the library.

## Extraction Rules

1. **Read-only evidence**: Inspect transcripts, tasks, and artifacts without modifying them.
2. **Grade evidence by approval**:
   - **Approved verbatim**: Encode directly as template obligations.
   - **Corrected**: Prioritize user corrections over initial drafts.
   - **Improvised defaults**: Encode unreviewed choices as flexible defaults, not doctrine.
3. **Capture pattern, not narrative**: Extract the coordination mechanics (blind parallel reviews, synthesis stages, independent gates) rather than session-specific events.
4. **Specify purpose, not method**: Define entry triggers, exit conditions, and criteria; leave tactical execution to future executors.
5. **Minimum content, not maximum**: Include only enough for a composing agent to select the template and know when the step is finished -- the same sufficient-and-no-more standard `workflow-library`'s schema states ([[aops_brief_workflow_assembly]]). Do not invent exclusions, contraindications, or gates the evidence didn't produce.

## Validation and Delivery

- **Generality test**: Verify the process generalizes beyond the current domain without brittle assumptions.
- **Library check**: Enumerate existing templates to prevent duplicate slugs or overlapping scopes.
- **Save in place**: Write the completed template to the appropriate tier (project, PKB, or universal) conforming to the template schema. Report the resulting path and approval sources.
