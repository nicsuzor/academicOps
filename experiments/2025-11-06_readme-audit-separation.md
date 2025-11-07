# README/AUDIT Separation Experiment

## Metadata

- Date: 2025-11-06
- Issue: User request via /trainer
- Commit: 288c0a1
- Model: claude-sonnet-4-5

## Context

User requested separation of "audit information" (current state) from "desired state" documentation.

**Problem**: README.md mixed specifications with current statistics, making it unclear what the repository SHOULD be vs. what it currently IS.

**Goal**: README.md as authoritative specification, AUDIT.md for compliance tracking.

## Hypothesis

Separating authoritative spec (README.md) from current state audit (AUDIT.md) will:

1. Clarify what the framework is designed to be
2. Enable compliance tracking over time
3. Make violations visible and actionable
4. Provide template for future audits
5. Support experiment-driven cleanup (measure before/after)

## Changes Made

### 1. Created docs/AUDIT.md

**Purpose**: Document current state for comparison against README spec

**Contents**:

- Component counts and statistics
- File sizes with bloat status
- Architecture pattern compliance (resources/, skill-first, anti-bloat)
- Known violations (Issue #142, etc.)
- Compliance summary (strengths, improvements needed, priorities)
- Measurement methodology for regenerating audit

**Key sections**:

- Current statistics (7 agents, 20 skills, 8 commands, 17 hooks)
- Anti-bloat violations (python-dev 797 lines, git-commit 516 lines)
- resources/ symlinks status (2/20 implemented)
- Skill-first pattern status (partial)
- Orphaned files (6 identified)
- Open GitHub issues relevant to framework

### 2. Rewrote README.md as Authoritative Specification

**Transformation**:

**REMOVED** (moved to AUDIT.md):

- Current line counts and file sizes
- "Quick Stats" from instruction tree
- "⚠️ 6 orphaned files" warnings
- "Potential overlaps" alerts
- Current implementation status

**KEPT/ENHANCED** (specification):

- Core principles (fail-fast, DRY, anti-bloat, experiment-driven, modular)
- Repository structure (desired state)
- Component specifications (requirements, not current state)
- Architectural patterns (standards to follow)
- Installation, validation, usage patterns
- Compliance monitoring process

**NEW sections**:

- "This README defines the desired state" (explicit purpose)
- Component specifications with requirements
- Architectural patterns as standards
- Anti-bloat enforcement rules
- Compliance monitoring workflow

**Key changes**:

- Present tense → Normative language ("MUST include", "Requirements:")
- Statistics → Specifications
- Observations → Standards
- Current state → Desired state

### 3. Established Bidirectional References

**README → AUDIT**:

- "See `docs/AUDIT.md` for current compliance status" (throughout)
- Explicit at top and bottom of README

**AUDIT → README**:

- References README as specification
- Uses README sections as compliance targets
- Documents deviations from README standards

## Success Criteria

**Clarity**:

1. README reader knows what framework SHOULD be
2. AUDIT reader knows what framework currently IS
3. Discrepancies between README/AUDIT are actionable

**Maintainability**: 4. AUDIT can be regenerated with documented methodology 5. Compliance tracking enables progress measurement 6. Future audits use same structure

**Actionability**: 7. Violations become GitHub issues 8. Priorities clear (immediate vs long-term) 9. Modular references pattern replicable

## Results

### Implementation Complete

**Files Created/Modified**:

- README.md: 590 lines (authoritative specification)
- docs/AUDIT.md: 339 lines (current state documentation)
- experiments/2025-11-06_readme-audit-separation.md: 158 lines (this log)

**Changes**:

- +1031 insertions, -178 deletions
- Clear normative language in README ("MUST", "Requirements:")
- Descriptive language in AUDIT (✅⚠️❌ status indicators)
- Bidirectional references maintained

### Success Criteria Validation

**Clarity** ✅:

1. README reader knows framework SHOULD be: ✅ Core principles, specifications, standards
2. AUDIT reader knows framework currently IS: ✅ Statistics, compliance status, violations
3. Discrepancies actionable: ✅ AUDIT flags violations with GitHub issue references

**Maintainability** ✅: 4. AUDIT regeneration documented: ✅ Measurement methodology section included 5. Progress measurable: ✅ Statistics establish baseline for future audits 6. Structure reusable: ✅ Template established in AUDIT.md

**Actionability** ✅: 7. Violations → GitHub issues: ✅ Issue #142 referenced, priorities listed 8. Priorities clear: ✅ Immediate vs long-term section in AUDIT 9. Patterns replicable: ✅ Modular references pattern explained

### Unexpected Findings

1. **README grew significantly**: 590 lines (from ~234 lines)
   - Rationale: Added component specifications, architectural patterns, usage examples
   - Acceptable: Specification document needs completeness

2. **AUDIT captures snapshot effectively**: 339 lines
   - Comprehensive without being exhaustive
   - Regeneration methodology makes it sustainable

3. **Bidirectional references natural**: README → AUDIT for status, AUDIT → README for spec
   - Prevents drift between documents
   - Makes relationship explicit

## Outcome

**SUCCESS**

**Achievements**:

- ✅ Clear separation: Spec (README) vs. audit (AUDIT)
- ✅ Normative vs. descriptive language distinction
- ✅ Compliance tracking baseline established
- ✅ Actionable violations documented
- ✅ Regeneration methodology included
- ✅ Experiment log complete

**Impact**:

- Framework has authoritative specification
- Compliance measurable over time
- Violations visible (18/20 skills lack resources/)
- Progress trackable via quarterly audits
- Template for future audits

**Next Steps**:

1. Apply modular references pattern to python-dev, git-commit (Issue #142)
2. Add resources/ symlinks to 18 remaining skills
3. Quarterly audit updates to track compliance
4. CI validation for anti-bloat rules (README specifies, not yet implemented)

## Notes

**Design Decisions**:

1. **AUDIT location**: `docs/AUDIT.md` (framework documentation, not root)
   - Rationale: Audit is supplementary, README is primary

2. **README style**: Normative/prescriptive
   - "MUST", "Requirements:", "Specifications"
   - Present tense for specifications
   - Anti-patterns documented

3. **AUDIT style**: Descriptive/observational
   - Current counts, status indicators (✅⚠️❌)
   - Tables for inventory
   - Explicit measurement methodology

4. **Bidirectional links**: README ↔ AUDIT
   - README points to AUDIT for "current status"
   - AUDIT references README as "specification"

**Comparison to Other Patterns**:

Similar to:

- OpenAPI spec (API.yaml) vs. actual implementation
- RFC specifications vs. implementation reports
- SQL schema vs. database state

**Benefits**:

- Clear separation of concerns
- Compliance measurable over time
- Violations become actionable tasks
- Progress trackable via experiments

**Risks**:

- AUDIT may fall out of sync (requires discipline)
- README may become aspirational (need enforcement)
- Users may confuse which document to follow

**Mitigations**:

- AUDIT includes regeneration instructions
- README references AUDIT frequently
- Compliance monitoring in contributing workflow
