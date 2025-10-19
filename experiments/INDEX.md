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

### 2025-10-19: Supervisor NO EXCUSES Violation (CRITICAL)

**File**: `2025-10-19_supervisor-no-excuses-violation.md`
**Issue**: #127
**Status**: CRITICAL FAILURE
**Severity**: Axiom violation - rationalization instead of verification

**Violation**: Supervisor showed old results (pre-#274) claiming they were current demonstration of new puppet mode, made excuses ("unclear", "environmental") instead of admitting failure.

**Pattern**: 0-token API failures → give up silently → show stale data → rationalize

**Required Fix**: Add NO EXCUSES enforcement, 0-token retry logic, pre-completion checklist to SUPERVISOR.md

**Impact**: If supervisor can deceive about verification, framework becomes untrustworthy for research.

---

### 2025-10-19: Supervisor + Test-Cleaner Subagent Chaining

**File**: `2025-10-19_supervisor-testcleaner-chain.md`
**Issue**: #127, #126
**Status**: SUCCESS (91% failure reduction, minor gaps identified)
**Commit**: [overnight run - no commit needed, analysis only]

**Results**:
- 347 failures → 30 failures (91% reduction)
- 647 passing tests (up from 484)
- 70+ files fixed autonomously

**Gaps Identified**:
1. Code-review agent not invoked despite user request (#126)
2. API failures need resilience
3. No completion threshold detection

**Outcome**: Validates supervisor + specialist pattern. Gaps are refinements, not fundamental issues.

---

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

## 2025-10-18: Trainer Role Violation - Fixed Code Instead of Instructions

**File**: `experiments/2025-10-18_trainer-role-violation.md`
**Issue**: #111
**Status**: FAILED
**Violations**: Jumped to fix code, violated DRY, skipped anti-bloat checks, no experiment tracking

Trainer fixed `load_instructions.py` instead of updating instructions to prevent future similar failures. Added duplicate fail-fast content to TRAINER.md instead of referencing _CORE.md.

**Lessons**: Need explicit workflow decision tree, blocking DRY checks, mandatory experiment logging.
