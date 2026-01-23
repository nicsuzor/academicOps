---
id: prove-feature
category: quality-assurance
bases: []
---

# Prove Feature

Validate framework integration. "Does it integrate correctly?"

## Routing Signals

- Validating new framework capabilities
- Verifying structural changes (relationships, computed fields)
- "Does it connect properly?"

## NOT This Workflow

- General functionality testing → [[qa-demo]]
- Unit testing → [[tdd-cycle]]
- Bug investigation → [[debugging]]

## Unique Steps

1. **Baseline**: Capture state before running feature
2. **Execute**: Run feature as user would
3. **Verify**: Check structural changes
4. **Report**: Evidence table (expected vs actual)

## Evidence Format

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key] | [value]  | [value]| ✅/❌    |
