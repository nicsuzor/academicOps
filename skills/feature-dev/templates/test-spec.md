---
title: Test Specification Template
type: template
permalink: skills/feature-dev/templates/test-spec
description: Template for comprehensive integration test design and validation planning
tags: [template, feature-dev, testing, qa]
---

# Test Specification: [Feature Name]

**Date**: YYYY-MM-DD **Test Location**: `path/to/test/file` **Status**: [Designed | Implemented | Passing | Failing]

## Overview

**Purpose**: [What this test validates] **Scope**: [What aspects of the feature are tested] **Success Criteria**: [Reference user story - don't duplicate] → See `user-story.md` section "Success Criteria"

## Test Design

### Integration Test

**Test type**: End-to-end integration test **Test framework**: [pytest, bash script, etc.] **Test location**: `path/to/test/file`

**What it tests**:

1. [Complete user workflow from start to finish]
2. [Each success criterion validated]
3. [Error conditions handled correctly]
4. [Edge cases covered]

**Test must**:

- Run automatically without manual steps
- Validate complete workflow end-to-end
- Check actual outputs against expected
- Fail loudly if any assertion fails
- Clean up test artifacts after run

### Test Cases

#### Test Case 1: [Happy Path]

**Scenario**: [Normal, expected usage]

**Setup**:

```
[Test environment preparation]
[Test data creation]
```

**Execute**:

```
[Actions performed by test]
[Feature invocation]
```

**Validate**:

```
[Assertions to verify success]
[Expected vs actual comparison]
```

**Cleanup**:

```
[Resource cleanup]
[Test artifact removal]
```

**Expected result**: [What should happen] **Success criteria validated**: [Which criteria this case verifies]

---

#### Test Case 2: [Edge Case]

**Scenario**: [Boundary condition or edge case]

[Same structure as Test Case 1]

---

#### Test Case 3: [Error Condition]

**Scenario**: [Invalid input or error state]

[Same structure as Test Case 1]

**Expected result**: [Appropriate error handling]

---

### Additional Test Cases

[Add as many as needed to cover all success criteria and edge cases]

## Test Implementation

**Language**: [bash, python, etc.] **Dependencies**: [Required tools or libraries]

**Test script outline**:

```bash
#!/bin/bash
# Integration test for [feature-name]

set -e  # Exit on error

# Setup
[Environment preparation]

# Test Case 1: [Happy Path]
[Implementation]

# Test Case 2: [Edge Case]
[Implementation]

# Test Case 3: [Error Condition]
[Implementation]

# Cleanup
[Remove test artifacts]

# Report
echo "✅ All tests passed"
exit 0
```

## Success Criteria Mapping

Map each success criterion to test cases that validate it:

| Success Criterion | Test Case(s)   | Validation Method        |
| ----------------- | -------------- | ------------------------ |
| [Criterion 1]     | Test Case 1, 2 | [How test verifies this] |
| [Criterion 2]     | Test Case 3    | [How test verifies this] |
| [Criterion 3]     | Test Case 1    | [How test verifies this] |

## Regression Testing

**Existing tests that must still pass**:

- `path/to/existing/test` - [What it validates]
- `path/to/another/test` - [What it validates]

**Areas to check**:

- [Existing functionality that might be affected]
- [Integration points with other features]

## Test Execution

**How to run**:

```bash
[Command to execute test]
```

**Expected output on success**:

```
[Sample successful test output]
```

**Expected output on failure**:

```
[Sample failed test output with clear error]
```

**Continuous integration**: [How test fits into CI/CD if applicable]

## Test Development Notes

**Test-First Protocol**:

1. Write this test specification
2. Implement the test code
3. Run test - MUST FAIL (feature doesn't exist yet)
4. Commit failing test
5. Implement feature
6. Run test - MUST PASS
7. Commit feature with passing test

**Current status**: [Where we are in test-first cycle]

**Known issues**: [Any test implementation challenges]

**Validation checklist**:

- [ ] Test covers all success criteria
- [ ] Test checks edge cases
- [ ] Test validates error handling
- [ ] Test is fully automated
- [ ] Test cleans up after itself
- [ ] Test fails before feature exists
- [ ] Test passes after feature complete

## Mock Data / Test Fixtures

[If test requires specific data or setup]

**Test data**:

- [Description of test data needed]
- [Location of test fixtures]

**Setup requirements**:

- [Environment configuration]
- [Dependencies to install]

---

**References**:

- User story: `user-story.md`
- Experiment plan: `experiment-plan.md`
- Development plan: `dev-plan.md`
- Testing axioms: [[AXIOMS.md]] (Fail-Fast, Integration Tests)
- Feature dev skill: [[../SKILL.md]]
