---
name: acceptance-tests
category: reference
description: Instructions and template for adding agent-driven acceptance tests
---

# Acceptance Tests

Instructions for adding new agent-driven e2e tests to the framework.

## Adding New Tests

To add a new acceptance test, add a section to `tests/acceptance/*.md` (e.g., `tests/acceptance/v1.1-release.md`).

### Best Practices

1. **Semantic Pass Criteria**: Pass criteria must be semantic (QA agent judges meaning), not pattern-based (avoid "output contains X").
2. **Test the Correct Component**: If testing the hydrator, test its workflow recommendations, not downstream tool execution.
3. **Clear Evaluation Instructions**: Include clear evaluation instructions for the QA agent.

### Template

```markdown
### TEST-NNN: <Short Description>

**ID**: `v1.1-<kebab-case-id>`

**Description**: <What this test validates>

**User Input**:
```

<exact user prompt>
```

**Expected Behavior**:

1. <Step 1>
2. <Step 2>

**Invocation Method**: `hydrator-only` | `full-session`

**Pass Criteria** (QA agent evaluates semantically):

1. <Semantic criterion 1 - what QA should verify>
2. <Semantic criterion 2>

**Why This Matters**: <Business justification>

**Related**:

- <Links to related workflows, skills, docs>
```

## Example Criteria

**Example good criteria (Semantic):**

- "Hydrator recommends the analyst skill for data work"
- "QA verifies output includes task creation steps"
- "Agent response demonstrates understanding of email triage workflow"

**Example bad criteria (Pattern-based - avoid):**

- "Output contains 'analyst'"
- "Response includes the word 'task'"
