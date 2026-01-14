---
id: spec-review
category: planning
---

# Spec Review Loop (Critic Feedback)

## Overview

Iterative design review process where a critic agent provides feedback on specifications, plans, or designs. Continues until the plan is robust or reaches diminishing returns.

## When to Use

- Designing new features or systems
- Planning complex refactoring
- Architectural decisions
- Any work where early feedback prevents costly mistakes

## Steps

### 1. Create initial specification or plan

Document your proposed approach:
- What problem are you solving?
- What is your proposed solution?
- What are the key design decisions?
- What alternatives did you consider?
- What are the trade-offs?

This can be a spec file, a plan in a bd issue, or a markdown document.

### 2. Invoke critic agent for review

Spawn the critic agent to review your plan:
```javascript
Task(subagent_type="aops-core:critic", model="opus", prompt=`
Review this [spec/plan/design] for issues.

**Context**: [brief description]

**Spec/Plan**:
[paste spec or reference file path]

**Review for**:
- Missing edge cases
- Simpler alternatives
- Potential issues or risks
- Clarity and completeness

Provide specific, actionable feedback.
`)
```

### 3. Analyze critic feedback

Review the critic's feedback:
- Which concerns are valid?
- Which suggestions improve the design?
- Which feedback can be safely dismissed?
- What questions need clarification?

### 4. Iterate on spec based on feedback

Update your specification to address valid concerns:
- Add missing edge cases
- Clarify ambiguous sections
- Consider simpler alternatives
- Document trade-off decisions

### 5. Check for convergence

Determine if another iteration is needed:

**Ready to proceed if:**
- All major concerns addressed
- No significant risks remain
- Spec is clear and complete
- Diminishing returns on further review

**Need another iteration if:**
- Major design flaws identified
- Significant edge cases missing
- Approach needs rethinking
- Clarity issues remain

If another iteration is needed, return to step 2.

## Convergence Criteria

Stop iterating when:
- 2-3 rounds completed with diminishing feedback
- All critical concerns addressed
- User approves the approach
- Time constraints require moving forward

## Success Metrics

- [ ] Critic feedback addressed or consciously deferred
- [ ] Major risks identified and mitigated
- [ ] Spec is clear enough to implement from
- [ ] Design decisions are documented with rationale
