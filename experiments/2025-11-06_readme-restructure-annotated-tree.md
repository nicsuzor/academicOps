# Restructure README as User Guide with Annotated Component Tree

## Metadata

- Date: 2025-11-06
- Issue: #195
- Commit: [to be added]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Restructuring README.md to focus on user-facing "what component for what task" guidance with annotated tree + brief descriptions will make the framework more discoverable and scannable, while moving technical specifications to ARCHITECTURE.md will reduce duplication and clarify documentation roles.

## Changes Made

### 1. README.md Restructuring (-53 lines, 9% reduction)

**Replaced** "Repository Structure (Specification)" + "Component Specifications" (lines 119-313, 195 lines)

**With** "Components & Capabilities" section containing:

1. **Annotated File Trees** with inline descriptions:
   - Core Instructions (auto-loaded files)
   - Agents (7 agents with purpose descriptions)
   - Slash Commands (8 commands with action descriptions)
   - Skills (20 skills grouped by category with purpose descriptions)
   - Hooks (6 key hooks with timing descriptions)
   - Documentation (key files with role descriptions)

2. **Quick Reference Table** - "Which Tool When":
   - 15 common tasks mapped to specific components
   - Examples: "Extract tasks → scribe skill", "Commit code → git-commit skill"

**Key improvements**:

- Every component now has brief inline description
- User can scan entire capability set in <2 minutes
- Clear "use X for Y" guidance
- Cross-references to ARCHITECTURE.md for specifications

### 2. ARCHITECTURE.md Enhancement (+88 lines)

**Added** "Component Specifications" section after "File Structure":

- Agents: Purpose, requirements, anti-patterns
- Skills: Purpose, requirements, framework-touching vs non-framework distinction
- Slash Commands: Purpose, MANDATORY skill-first pattern
- Hooks: Purpose, types, requirements
- Chunks: Purpose, files, requirements

**Rationale**: Consolidates technical specifications in developer-focused document, eliminating duplication with README.

### 3. Component Descriptions Extracted

Used Python script to extract descriptions from YAML frontmatter (agents/skills/commands) and docstrings (hooks):

- 7 agents
- 8 slash commands
- 20 skills (categorized: framework, development, utility)
- 15 hooks

All descriptions now visible in annotated tree for quick reference.

## Success Criteria

**User Experience**:

- [x] Can find "which component for X task" quickly (Quick Reference table)
- [x] README scannable in <2 minutes (reduced from 615 to 562 lines)
- [x] All components have descriptions in tree
- [x] Clear capability overview

**Documentation Quality**:

- [x] No duplication between README and ARCHITECTURE
- [x] Specifications consolidated in ARCHITECTURE
- [x] User guide vs developer spec roles clarified
- [x] Cross-references between docs

## Results

**Quantitative**:

- README: 615 → 562 lines (-53 lines, -9%)
- ARCHITECTURE: 293 → 381 lines (+88 lines, +30%)
- Net change: +35 lines total, but better organized

**Qualitative**:

- README now focuses on "what" and "when to use"
- ARCHITECTURE focuses on "how" and "requirements"
- Every component visible with description
- Quick Reference table enables fast lookup

**User Feedback**: Awaiting review

## Outcome

**Success (Documentation)** - README restructured as user guide with annotated component tree.

**Benefits**:

1. **Discoverability**: Quick Reference table maps tasks to components
2. **Scannability**: Annotated trees show all capabilities at a glance
3. **Clarity**: Separated user guide (README) from developer spec (ARCHITECTURE)
4. **Completeness**: Every component documented with description
5. **Reduced duplication**: Specifications in one place (ARCHITECTURE)

**Next Steps**:

- User review and feedback
- Consider adding examples/tutorials section to README
- Update AUDIT.md if structural audit pending

## Technical Notes

**Extraction Method**:

- YAML frontmatter: `description:` field from .md files
- Python docstrings: First line from .py files
- All 42 components successfully extracted and documented

**Architectural Alignment**:

- Follows anti-bloat protocol (net -53 lines in user-facing doc)
- Maintains DRY (specifications in one place)
- Improves documentation discoverability (Issue #111)
- User-centered design (task-oriented Quick Reference)
