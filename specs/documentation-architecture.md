---
title: Documentation Architecture
type: spec
category: spec
status: approved
permalink: documentation-architecture
description: Three-document architecture for framework documentation with clear audience separation
tags:
  - framework
  - documentation
  - architecture
---

# Documentation Architecture

**Date**: 2026-01-05
**Stage**: 2 (Framework Consolidation)
**Priority**: P1

## Problem Statement / User Story

**What problem does this solve?**

Framework documentation suffered from overlap and underspecification. Multiple files (README.md, INDEX.md, FRAMEWORK.md, specs/specs.md) served unclear purposes with mixed audiences. Agents received exhaustive file trees they didn't need; humans couldn't find how things fit together.

**Why does this matter?**

- Agents waste context on irrelevant file listings
- Humans can't quickly understand framework capabilities
- Audit processes lack clear accounting of all files
- Overlap creates maintenance burden and drift

**Who benefits?**

- **Agents**: Get only the paths they need (FRAMEWORK.md)
- **Humans**: Understand capabilities and relationships (README.md)
- **Auditors/Maintainers**: Complete file accounting (INDEX.md)

## Acceptance Criteria (MANDATORY)

### Success Tests

1. [ ] FRAMEWORK.md contains only agent-essential paths and key files (no exhaustive listing)
2. [ ] INDEX.md clearly states "audit-only" purpose in frontmatter
3. [ ] README.md serves as human feature guide with capability overview
4. [ ] No content duplication between the three documents
5. [ ] Each document has clear `audience` field in frontmatter

### Failure Modes

1. [ ] Agent receives INDEX.md content at session start (wrong - too large)
2. [ ] Human must read INDEX.md to understand framework (wrong - that's README's job)
3. [ ] Files exist that don't appear in INDEX.md (audit failure)

## Scope

### In Scope

- Define three-document architecture with clear separation
- Update FRAMEWORK.md, INDEX.md, README.md frontmatter to clarify purposes
- Remove cross-reference tables from INDEX.md (move to README.md if needed)

### Out of Scope

- Converting INDEX.md to structured format (noted for future investigation)
- Automating INDEX.md generation from file system
- Consolidating other specs (separate Phase 2a work)

**Boundary rationale**: This spec defines the architecture. Implementation details for each document are in the documents themselves.

## Dependencies

### Required Infrastructure

- None - uses existing markdown files

### Data Requirements

- Current file tree (for INDEX.md completeness verification)

## Design

### Three-Document Architecture

| Document         | Purpose                                              | Audience                   | Injected to Agents? |
| ---------------- | ---------------------------------------------------- | -------------------------- | ------------------- |
| **FRAMEWORK.md** | Agent-focused paths and key files                    | Agents                     | Yes (SessionStart)  |
| **INDEX.md**     | Complete file accounting for audits                  | Maintainers, audit scripts | No                  |
| **README.md**    | Human feature guide - capabilities and relationships | Humans                     | No                  |

### FRAMEWORK.md (Agent-Focused)

**Contains**:

- Resolved path table ($AOPS, $ACA_DATA, key directories)
- Key file references (AXIOMS, HEURISTICS, CORE, ACCOMMODATIONS)
- Memory system overview
- Environment variable architecture

**Does NOT contain**:

- Complete file tree (that's INDEX.md)
- Feature descriptions (that's README.md)
- Cross-reference tables

### INDEX.md (Audit-Only)

**Contains**:

- Complete file tree with one-line descriptions
- Every file in $AOPS accounted for
- Frontmatter: `audience: maintainers, audit-scripts`

**Does NOT contain**:

- Feature explanations
- Cross-reference tables (Command→Skill, etc.)
- How-to guidance

**Future option**: May convert to structured format (CSV, JSON) for programmatic validation. Currently markdown for human readability during audits.

### README.md (Human Feature Guide)

**Contains**:

- Quick Start
- How workflows fit together
- Command/Skill/Hook/Agent tables with purposes
- Cross-reference tables (moved from INDEX.md)
- Common Tasks
- Glossary

**Does NOT contain**:

- Complete file listing
- Path resolution details

## Verification

### Manual Verification

1. Read each document's frontmatter - purpose and audience must be clear
2. Check SessionStart hook - only FRAMEWORK.md should be injected (plus AXIOMS, HEURISTICS)
3. Verify INDEX.md lists every file in $AOPS (use `scripts/check_orphan_files.py`)

### Automated Verification (Future)

- Pre-commit hook validates INDEX.md completeness
- CI check that cross-reference tables exist only in README.md

## Notes and Context

**Decision rationale**: The three-document split emerged from audit analysis showing overlap between INDEX.md (complete file tree) and README.md (feature inventory). Rather than merge them, we separated by audience: agents need paths (FRAMEWORK.md), auditors need completeness (INDEX.md), humans need understanding (README.md).

**Related**:

- [[audit-skill]] - enforces this architecture (verifies structure, maintains INDEX.md/README.md)
- [[audit-plan]] Phase 3 (Framework-Wide Structure Review)
- [[spec-maintenance]] for spec lifecycle

## Completion Checklist

- [x] Architecture approved by user (2026-01-05)
- [ ] FRAMEWORK.md updated with agent-focused content only
- [ ] INDEX.md frontmatter updated to clarify audit-only purpose
- [ ] README.md verified as human feature guide
- [ ] Cross-reference tables in correct location (README.md only)
- [ ] No duplication between documents
