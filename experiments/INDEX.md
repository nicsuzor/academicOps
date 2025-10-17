# Experiment Tracking Index

Master log of all agent performance experiments, failures, and interventions.

## Purpose

Track agent instruction changes systematically with:
- What was tested
- What violations occurred
- What was learned
- What was changed

See TRAINER.md lines 126-153 for requirements.

## Active Experiments

### 2025-10-17: validate_env.py Flat Architecture Refactor

**File**: `2025-10-17_validate-env-flat-arch.md`
**Issue**: #114, #118
**Status**: FAILED (multiple violations)
**Commit**: [pending]

**Violations**:
1. Dual code paths (backward compatibility)
2. Hardcoded path assumptions
3. Trainer failed to track performance when requested

**Outcome**: Rolled back changes, awaiting discovery mechanism definition.

---

## Closed Experiments

(None yet)

---

## Format Template

```markdown
# Experiment: [Name]

**Date**: YYYY-MM-DD
**Commit**: [git hash]
**Issue**: #[number]
**Agent**: [which agent performed work]

## Hypothesis
[What was being tested]

## Implementation
[What was changed]

## Violations
- [Standard violated]
- [Another violation]

## Outcome
[Success/Failure and why]

## Lessons
[What to change in instructions/enforcement]
```
