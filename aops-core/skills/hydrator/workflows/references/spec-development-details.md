# Specification Development Detailed Procedures

Detailed questions, templates, and criteria for developing automation specifications.

## Defining Acceptance Criteria (Step 4)

**CRITICAL**: Acceptance criteria define "done" and are user-owned (agents cannot modify them).

### Persona Paragraph

Inhabit the user's situation when they encounter this feature:

- Cognitive and emotional state
- Environmental and technical constraints
- What success feels like

### Qualitative Dimensions

Frame answers as qualitative dimensions requiring judgment, not binary checklists. Describe the spectrum from excellent to poor for each:

- "How will we know this automation succeeded?"
- "What quality threshold is acceptable?"
- "What would indicate this implementation is WRONG?" (Failure modes)

### Regression Checks

Identify binary guards against breakage, separate from qualitative acceptance. These will be implemented as automated tests.

## Designing Integration Tests (Step 7)

**CRITICAL**: Tests must implement the acceptance criteria defined in Step 4.

### Mapping Tests to Criteria

- Map each test approach to a specific acceptance criterion.
- Walk through the full cycle: Setup → Execute → Validate → Cleanup.

### Verification Questions

- "How do we prove EACH acceptance criterion is met?"
- "How do we detect EACH failure mode?"
- "Is every acceptance criterion covered by at least one test?"

Tests must be designed to fail initially to prove they are testing the correct behaviors.
