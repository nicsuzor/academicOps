# README Cleanup: Minimal User Guide

## Metadata

- Date: 2025-11-06
- Issue: N/A (continuation of #195)
- Commit: [to be added]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Removing installation/validation/usage/compliance sections from README and keeping only essential user-facing content (component tree, three-tier loading, quick start) will make README truly scannable while consolidating all technical content in ARCHITECTURE.md.

## Changes Made

### 1. README.md Major Cleanup (-246 lines, -44% reduction)

**Removed sections** (lines 261-562, 302 lines total):

- Architectural Patterns sections 1-4 (resources, skill-first, anti-bloat, experiment-driven)
- Installation & Setup (detailed instructions)
- Validation & Testing
- Usage Patterns
- Compliance Monitoring
- Contributing (detailed workflow)

**Kept from Architectural Patterns**:

- Three-Tier Instruction Loading explanation (essential for understanding framework)
- Simplified to 13 lines with clear diagram

**Added streamlined sections**:

- Key References (8 essential doc links)
- Quick Start (5 lines - just env var + script + launch)
- License + footer

**Result**: 562 → 316 lines (-246 lines, -44%)

### 2. ARCHITECTURE.md Enhancement (+42 lines)

**Added to Design Principles section**:

- Mandatory Skill-First Pattern
- Anti-Bloat Enforcement (checklist + hard limits)
- Experiment-Driven Development (workflow steps)

**Rationale**: These are architectural requirements that developers need, not user-facing guidance.

### 3. Path Standardization

**Fixed**: `docs/agents` → `docs/bots` in three-tier loading diagram

- Personal tier: `$ACADEMICOPS_PERSONAL/docs/bots/*.md`
- Project tier: `$PWD/docs/bots/*.md`

**Consistency**: Matches actual directory structure (`docs/bots/` exists, not `docs/agents/`)

## Success Criteria

**README Simplicity**:

- [x] Reduced to essential user-facing content only
- [x] Removed all technical workflow details
- [x] Kept three-tier explanation (core concept)
- [x] One-command installation (setup script reference)
- [x] Under 350 lines total

**Technical Content Consolidation**:

- [x] All architectural patterns in ARCHITECTURE.md
- [x] No duplication between docs
- [x] Developer workflows in proper location

**Accuracy**:

- [x] Path references corrected (docs/bots not docs/agents)
- [x] All cross-references valid

## Results

**README.md** (Before → After):

- Lines: 562 → 316 (-246, -44%)
- Sections: 14 → 6
- Focus: Pure user guide (what exists, how to start)

**ARCHITECTURE.md**:

- Lines: 381 → 423 (+42, +11%)
- Added: 3 design principle subsections
- Consolidation: All technical patterns now in one place

**Net change**: -204 lines total

**Content Distribution**:

- **README**: Components, three-tier loading, quick start, references
- **ARCHITECTURE**: All specifications, patterns, workflows, requirements

## Outcome

**Success** - README now truly minimal user guide.

**Key Improvements**:

1. **Scannable**: 316 lines total, 6 sections, clear hierarchy
2. **User-focused**: No developer workflows, just "what exists + how to start"
3. **Accurate**: Fixed docs/agents → docs/bots standardization
4. **Consolidated**: All technical patterns in ARCHITECTURE
5. **Maintained essential**: Three-tier loading explanation retained

**User Experience**:

- New user reads: Components tree → Three-tier concept → Quick Start → Done
- Developer reads: README for overview → ARCHITECTURE for specifications
- No confusion about where to find what

**Removed Redundancy**:

- Installation details (just reference setup script)
- Validation instructions (developer concern, in ARCHITECTURE)
- Usage patterns (covered by component descriptions)
- Compliance monitoring (developer/maintainer concern)
- Detailed contributing workflow (GitHub CONTRIBUTING.md standard location)

## Technical Notes

**Three-Tier Loading**:

- Kept in README because it's fundamental to understanding how framework works
- Essential for users to know their customizations layer properly
- Simplified presentation (13 lines vs previous verbose explanation)

**docs/bots Standardization**:

- Corrects long-standing inconsistency
- Actual directory: `docs/bots/` (contains BEST-PRACTICES.md, INDEX.md, etc.)
- References now accurate throughout documentation

**Architecture Consolidation**:

- Mandatory Skill-First: Developer pattern
- Anti-Bloat Enforcement: Developer checklist
- Experiment-Driven: Developer workflow
- All belong in ARCHITECTURE, not user guide
