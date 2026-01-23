# Prove Feature Workflow

Validate framework integration. "Does it integrate correctly?"

## When to Use

Use this workflow when:
- Validating new framework capabilities
- Verifying structural changes (relationships, computed fields)
- Asking "does it connect properly?"

Do NOT use for:
- General functionality testing (use qa-demo)
- Unit testing (use tdd-cycle)
- Bug investigation (use debugging)

## Constraints

### Verification Sequencing

1. **Capture baseline** before executing the feature (state snapshot)
2. **Execute the feature** as a user would
3. **Verify structural changes** after execution
4. **Produce an evidence report** with expected vs actual values

### Always True

- All verification must be evidence-based
- Every claim must have expected and actual values compared

## Evidence Format

Use this table format for evidence:

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key] | [value]  | [value]| ✅/❌    |

## Triggers

- When validation is requested → capture baseline
- When baseline is captured → execute feature
- When feature is executed → verify changes
- When verification is complete → produce evidence report

## How to Check

- Baseline captured: state snapshot exists before feature execution
- Feature executed: feature was run as user would invoke it
- Structural changes verified: structural elements (relationships, fields) were inspected
- Evidence report produced: evidence table with expected vs actual values exists
- Evidence-based verification: all claims are backed by observable evidence
- Expected vs actual comparison: each verification point has both expected and actual values
