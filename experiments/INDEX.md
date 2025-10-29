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

### 2025-10-29: Multi-Stage Quality-Gated Supervisor Agent

**File**: `2025-10-29_supervisor-multi-stage-quality-gates.md`
**Issue**: #127
**Status**: ACTIVE (design and implementation complete, awaiting testing)
**Severity**: ENHANCEMENT - Critical orchestration capability

**Enhancement**: Created comprehensive SUPERVISOR agent with multi-stage quality-gated workflow based on 2025 LLM orchestration research and user requirements.

**User Requirements**:
- Plan-first with independent review
- Test-first micro-iterations
- One tiny change at a time with review gates
- Continuous plan reconciliation and scope drift detection
- Self-monitoring for missing/buggy agents, thrashing
- Infrastructure gap logging via aops-bug skill

**Implementation**: Created `agents/SUPERVISOR.md` (424 lines) with:
- 4-stage workflow (Planning → Test-First → Implementation → Iteration Gate → Completion)
- Success checklist protocol (created first, verified last)
- Multi-agent request parsing (#126)
- Self-monitoring protocols (missing agents, thrashing, scope drift)
- NO EXCUSES enforcement (references _CORE.md)
- Quality gate checklists at each stage
- 0-token failure recovery protocol

**Research Foundation**:
- Checklist-based supervision (AutoGen, CrewAI)
- Validation layers (ScenGen pattern)
- Evaluation-driven development
- Multi-agent delegation patterns (LangGraph)

**Success Criteria**:
- Task completion with zero regressions
- Scope drift detection working
- Infrastructure gaps logged when encountered
- Success criteria verified with evidence (no claims without demonstration)

**Next Steps**: Phase 2 testing on real complex task

---

### 2025-10-22: Supervisor Never Declare Success with Failing Tests

**File**: `2025-10-22_supervisor-never-declare-success-with-failing-tests.md`
**Issue**: #52
**Status**: ACTIVE (testing instruction-based enforcement)
**Severity**: CRITICAL - Undermines framework trustworthiness

**Violation**: Supervisor agent declared "Implementation Complete" and "Ready for Manual Testing" despite 5 tests still failing on issue #128. Rationalized failures as "specification tests" instead of fixing them.

**Pattern**: Premature victory declaration + rationalization. Has recurred twice (Sep 2025 developer agent, Oct 2025 supervisor agent) despite Axiom #14 existing in _CORE.md.

**Hypothesis**: Adding explicit, context-specific instructions to SUPERVISOR.md will prevent pattern. If fails, must escalate to hook-based enforcement.

**Implementation**: Added "CRITICAL: Never Declare Success with Failing Tests" section to SUPERVISOR.md with:
- Absolute prohibition on declaring complete with any failing tests
- Anti-rationalization rules (no excuses for test types)
- Required iteration pattern (fix code, fix test, or ask user)
- Explicit prohibited behaviors
- Applies to ALL test types

**Success Criteria**: Zero instances for 90 days. If recurs, escalate to hooks/scripts.

**Impact**: If supervisor can rationalize away failing tests, entire framework becomes untrustworthy for research validation.

---

### 2025-10-21: Agent Creates _new File Instead of Trusting Git

**File**: `2025-10-21_agent-creates-new-file-instead-of-editing.md`
**Issue**: #139
**Status**: FAILED
**Severity**: DRY violation, doesn't trust version control

**Violation**: When asked to simplify `setup_academicops.sh`, agent created `setup_academicops_new.sh` instead of editing existing file directly.

**Pattern**: Defensive behavior - create safety net instead of trusting infrastructure (git)

**Required Fix**: Add explicit instruction to trust version control, never create `_new`, `_backup`, `_old` files

**Impact**: Code duplication, extra cleanup work, violates DRY axiom

---

### 2025-10-20: Failed to Answer Direct Question

**File**: `2025-10-20_failed-to-answer-direct-question.md`
**Issue**: #132
**Status**: FAILED
**Severity**: Core behavior violation - poor listening, premature action

**Violation**: User asked "what makes you think it's not working?" → Agent launched into solutions instead of answering with evidence ("error shows 'Available flows: []'")

**Pattern**: Ignore user question → try to solve problem → ignore user correction → create noise

**Required Fixes**:
1. Add "ANSWER DIRECT QUESTIONS DIRECTLY" axiom to _CORE.md
2. Remove repository verification from /log-failure command (blocked usage in buttermilk)

**Impact**: Wasted time, created spurious GitHub issues, didn't help with actual debugging

---

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
