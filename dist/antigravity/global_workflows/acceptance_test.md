  Add a new acceptance test to tests/acceptance/v1.1-release.md. Follow the template in the "Adding New Tests" section. Remember:
  1. Pass criteria must be semantic (QA agent judges meaning), not pattern-based ("output contains X")
  2. Test the correct component - if testing hydrator, test its workflow recommendations, not downstream tool execution
  3. Include clear evaluation instructions for the QA agent

  The template in the file:

  ### TEST-NNN: <Short Description>

  **ID**: `v1.1-<kebab-case-id>`

  **Description**: <What this test validates>

  **User Input**:
  Expected Behavior:
  1. <Step 1>
  2. <Step 2>

  Invocation Method: hydrator-only | full-session

  Pass Criteria (QA agent evaluates semantically):
  1. <Semantic criterion - what QA should verify>

  Why This Matters:

  Related:
  - <Links to related workflows, skills, docs>

  **Example good criteria:**
  - "Hydrator recommends the analyst skill for data work"
  - "QA verifies output includes task creation steps"
  - "Agent response demonstrates understanding of email triage workflow"

  **Example bad criteria (violates P#49):**
  - "Output contains 'analyst'"
  - "Response includes the word 'task'"
