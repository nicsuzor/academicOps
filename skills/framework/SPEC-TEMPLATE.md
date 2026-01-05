---
title: AcademicOps Specification Template
type: template
permalink: spec-template
description: Template for specifying academicops tasks with clear scope, acceptance criteria, and integration tests
tags:
  - template
  - task-specification
  - automation
---

# AcademicOps Feature Specification Template

Use this template to specify each academicops feature before implementation. This ensures clear scope, testability, and alignment with framework principles.

---

# Task: [Descriptive Name]

**Date**: YYYY-MM-DD 
**Stage**: [1-5 from ROADMAP.md] 
**Priority**: [P1/P2/P3 based on impact and effort]

## Problem Statement / User story

**What manual work are we automating?**

[Clear, specific description of the current manual process that causes pain]

**Why does this matter?**

[Impact: How much time/effort does this save? What quality improvements result?]

**Who benefits?**

[Usually Nic, but be specific about which aspect of his work]

## Acceptance Criteria (MANDATORY)

**CRITICAL**: These criteria are USER-OWNED and define what "done" means. Agents CANNOT modify, weaken, or reinterpret these criteria (see [[AXIOMS.md]] #21).

### Success Tests (Must ALL pass for "done")

1. [ ] [Specific, observable, testable criterion - e.g., "95% of captured tasks auto-categorized correctly"]
2. [ ] [Observable outcome - e.g., "Zero manual filing needed for email-based tasks"]
3. [ ] [Measurable improvement - e.g., "Categorization time reduced from 5min to <10sec per task"]

### Failure Modes (If these occur, implementation is WRONG)

1. [ ] [Specific failure condition - e.g., "Tasks categorized to wrong project"]
2. [ ] [Error condition - e.g., "Automation crashes on malformed input"]
3. [ ] [Performance degradation - e.g., "Processing time >1 minute per task"]

**Quality threshold**: [What level of quality is acceptable? When should it fail-fast vs. make best effort?]

**Test implementation**: Acceptance criteria MUST be implemented as automated tests. Success = tests pass. Agents implement the criteria as tests; they do not decide what "done" means.

## Scope

### In Scope

- [Specific capability 1]
- [Specific capability 2]
- [Specific capability 3]

### Out of Scope

- [What we're explicitly NOT doing]
- [Edge cases we'll handle later]
- [Related but separate problems]

**Boundary rationale**: [Why these boundaries? What makes this a "do one thing" task per [[AXIOMS.md]]?]

## Dependencies

### Required Infrastructure

- [What must exist before this can work? e.g., "Task markdown format defined"]
- [What other automations must work first?]
- [What manual processes must be documented first?]

### Data Requirements

- [What data does this need access to?]
- [What format/structure is required?]
- [What happens if data is missing or malformed?]

## Integration Test Design

**CRITICAL**: Integration tests IMPLEMENT the acceptance criteria defined above. Tests verify acceptance criteria; they do not define new criteria.

**Test must be designed BEFORE implementation**

Each test should map to specific acceptance criteria from above. Reference which criterion each test validates.

### Test Setup

[What needs to be prepared for the test?]

```bash
# Setup commands
# e.g., Create test task files, prepare test data
```

### Test Execution

[What actions does the test perform?]

```bash
# Execution commands
# e.g., Run automation script, capture output
```

### Test Validation

[What proves the automation worked?]

```bash
# Validation commands
# e.g., Check output files, verify categories, measure time
```

### Test Cleanup

[How do we clean up test artifacts?]

```bash
# Cleanup commands
# e.g., Remove test files, reset state
```

### Success Conditions

- [ ] Test initially fails (proves test detects problems)
- [ ] Test passes after implementation
- [ ] Test covers happy path
- [ ] Test covers error cases
- [ ] **Test validates ALL acceptance criteria from above (not agent-defined criteria)**
- [ ] **Test detects ALL failure modes from above**
- [ ] Test is idempotent (can run repeatedly)
- [ ] Test cleanup leaves no artifacts

**Mapping to acceptance criteria**:
- Test 1 validates: [Acceptance criterion #1]
- Test 2 validates: [Acceptance criterion #2]
- Test 3 detects: [Failure mode #1]

## Implementation Approach

### High-Level Design

[How will this work? What's the general approach?]

**Components**:

1. [Component 1 - e.g., "Task parser: Extract metadata from markdown"]
2. [Component 2 - e.g., "Categorizer: Match to projects using keywords"]
3. [Component 3 - e.g., "Writer: Update task file with category"]

**Data Flow**: [Input] → [Component 1] → [Component 2] → [Component 3] → [Output]

### Technology Choices

**Language/Tools**: [e.g., "Python with uv", "Bash script", "Claude skill"]

**Libraries**: [What dependencies needed? Justify each]

**Rationale**: [Why these choices? What alternatives considered?]

### Error Handling Strategy

**Fail-fast cases** (halt immediately, per [[AXIOMS.md]]):

- [e.g., "Task file malformed"]
- [e.g., "Required metadata missing"]

**Graceful degradation cases** (best effort):

- [e.g., "Project keyword ambiguous → flag for manual review"]
- [e.g., "Low confidence categorization → suggest but don't auto-apply"]

**Recovery mechanisms**:

- [How do we recover from failures?]
- [What state needs to be preserved?]

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: [e.g., "Task categorized to wrong project"]
   - **Detection**: [How would we know?]
   - **Impact**: [What's the consequence?]
   - **Prevention**: [How do we prevent this?]
   - **Recovery**: [How do we fix it?]

2. **Failure mode**: [e.g., "Automation crashes on malformed input"]
   - **Detection**: [How would we know?]
   - **Impact**: [What's the consequence?]
   - **Prevention**: [How do we prevent this?]
   - **Recovery**: [How do we fix it?]

3. **Failure mode**: [e.g., "Performance degrades with large task lists"]
   - **Detection**: [How would we know?]
   - **Impact**: [What's the consequence?]
   - **Prevention**: [How do we prevent this?]
   - **Recovery**: [How do we fix it?]

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- [e.g., "Categorization accuracy: % manual corrections needed"]
- [e.g., "Performance: Time per task"]
- [e.g., "Reliability: % runs without errors"]

**Monitoring approach**:

- [e.g., "Log all categorization decisions to data/logs/"]
- [e.g., "Weekly review of manual corrections"]
- [e.g., "Alert if error rate >5%"]

**Validation frequency**: [How often do we check? Automated or manual?]

## Documentation Requirements

### Code Documentation

- [ ] Docstrings for all functions (purpose, inputs, outputs, failure modes)
- [ ] Inline comments for non-obvious logic
- [ ] Type hints for Python (mypy must pass)
- [ ] README in script directory if complex

### User Documentation

- [ ] Update relevant skill/workflow docs with automation
- [ ] Document manual fallback if automation fails
- [ ] Add to ROADMAP.md progress tracking
- [ ] Create experiment log entry when complete

### Maintenance Documentation

- [ ] Known limitations and edge cases
- [ ] Future improvement opportunities
- [ ] Dependencies and version requirements

## Rollout Plan

### Phase 1: Validation (Experiment)

- Test with limited dataset
- Monitor closely for issues
- Collect feedback and metrics
- Document in experiment log

**Criteria to proceed**: [e.g., "95% accuracy on 50 test tasks, zero crashes"]

### Phase 2: Limited Deployment

- Deploy for specific use case only
- Keep manual process as backup
- Continue monitoring
- Refine based on real usage

**Criteria to proceed**: [e.g., "2 weeks of reliable operation, <5% manual corrections"]

### Phase 3: Full Deployment

- Replace manual process completely
- Archive manual documentation as reference only
- Reduce monitoring to periodic checks
- Document as "production" in framework

**Rollback plan**: [What if we need to revert? How?]

## Risks and Mitigations

**Risk 1**: [e.g., "Categorization logic too complex to maintain"]

- **Likelihood**: [High/Medium/Low]
- **Impact**: [High/Medium/Low]
- **Mitigation**: [e.g., "Start with simple keyword matching, add complexity only if needed"]

**Risk 2**: [e.g., "Performance issues with large datasets"]

- **Likelihood**: [High/Medium/Low]
- **Impact**: [High/Medium/Low]
- **Mitigation**: [e.g., "Test with realistic dataset sizes, optimize if needed"]

## Open Questions

[Questions to resolve before or during implementation]

1. [e.g., "Should ambiguous categorizations auto-apply with low confidence tag, or flag for manual review?"]
2. [e.g., "What's the fallback if categorization service is unavailable?"]
3. [e.g., "How do we handle tasks that span multiple projects?"]

## Notes and Context

[Any additional context, constraints, or considerations]

[Link to related tasks, experiments, or documentation]

---

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably (>95% success rate)
- [ ] All failure modes addressed
- [ ] Documentation complete (code, user, maintenance)
- [ ] Experiment log entry created
- [ ] No documentation conflicts introduced
- [ ] Code follows [[AXIOMS.md]] principles (fail-fast, DRY, explicit)
- [ ] Monitoring in place and working
- [ ] Rollout plan executed successfully
- [ ] Framework ROADMAP.md updated with progress

## Post-Implementation Review

[After 2 weeks of production use]

**What worked well**:

- [Aspect that exceeded expectations]

**What didn't work**:

- [Aspect that underperformed or caused issues]

**What we learned**:

- [Insights for future automations]

**Recommended changes**:

- [Improvements to make or things to do differently next time]
