---
title: Framework Audit Skill Specification
type: spec
category: spec
status: Implemented
permalink: audit-skill-spec
description: Comprehensive framework governance audit - structure checking, justification checking, and index file updates
tags:
  - spec
  - documentation
  - governance
  - audit
  - skill-design
priority: P1
---

# Task: Framework Audit Skill

## Problem Statement

**What manual work are we automating?**

Framework governance requires multiple verification tasks:

1. **Structure verification**: Checking if files are documented in README.md/INDEX.md
2. **Justification verification**: Checking if each file traces to a spec or user story
3. **Reference verification**: Ensuring wikilinks and cross-references resolve
4. **Index maintenance**: Keeping README.md/INDEX.md accurate

This is error-prone and time-consuming, leading to documentation drift and orphaned files.

**Why does this matter?**

- **Structure drift**: When INDEX.md doesn't match filesystem, agents have outdated understanding
- **Unjustified files**: Files without specs accumulate as cruft (AXIOM #29 - One Spec Per Feature)
- **Broken references**: Wikilinks to nonexistent files confuse navigation
- **Trust erosion**: If documentation can't be trusted, agents can't rely on it

**Who benefits?**

Framework maintainers - ensures documentation stays trustworthy and files are justified.

## Success Criteria

**The automation is successful when**:

1. Every file has a corresponding entry in INDEX.md with a clear and concise justification
2. Every file traces to a spec
3. Orphan candidates are flagged for human review
4. All wikilink-style references resolve to existing files
5. README.md/INDEX.md reflect actual filesystem state
6. Zero manual verification needed to trust documentation

**Quality threshold**: Fail-fast on structure errors. Report justification status comprehensively.

## Scope

### In Scope

**Structure Audit**:

- Scan filesystem to discover all files
- Compare actual vs documented in INDEX.md
- Detect missing/extra entries
- Validate wikilink references resolve

**Justification Audit**:

- For each significant file in `$AOPS/`:
  - Search `$AOPS/specs/` for references
  - Check if mentioned in core docs (JIT-INJECTION.md, README.md, etc.)
  - Classify as: Justified, Implicit, or Orphan

**Index Updates**:

- Fix missing entries in INDEX.md
- Fix missing entries in README.md tables
- Report orphan candidates for human review

### Out of Scope

- Auto-deleting orphan files (human review required)
- Checking content quality within files
- Validating code correctness
- Creating specs for orphans (human decision)

**Boundary rationale**: Audit detects and reports. Remediation (delete vs spec) is a human decision.

## Implementation Approach

### High-Level Design

The skill operates as an agent-invoked workflow with three phases:

**Phase 1: Structure Audit**

1. Agent scans filesystem (`find $AOPS -type f`)
2. Agent reads INDEX.md, extracts documented tree
3. Agent compares → discrepancies list
4. Agent checks wikilinks → broken reference list

**Phase 2: Justification Audit**

1. Agent identifies significant files (top-level, skill dirs, etc.)
2. For each: grep specs/ for references
3. For each: check core docs for mentions
4. Classify: Justified / Implicit / Orphan

**Phase 3: Updates**

1. Agent fixes INDEX.md structure
2. Agent updates README.md tables
3. Agent generates report with orphan candidates

### Technology Choices

**Language/Tools**: Claude Code skill + Python health scripts

**Components**:

- Agent-driven audit for semantic analysis and updates
- Python scripts for fast, deterministic health checks

**Health Scripts** (`$AOPS/scripts/`):

- `audit_framework_health.py` - Full metrics collector
- `check_index_completeness.py` - INDEX.md accounting
- `check_skill_line_count.py` - SKILL.md size limits
- `check_broken_wikilinks.py` - Wikilink resolution
- `check_orphan_files.py` - Orphan detection

**Why hybrid approach**:

- Scripts: Fast, deterministic, CI/CD-compatible
- Agents: Semantic understanding for justification, intelligent updates
- Pre-commit/CI: Automated enforcement without agent overhead

### Error Handling Strategy

**Fail-fast cases**:

- README.md/INDEX.md doesn't exist
- $AOPS environment variable not set
- Unable to write updated files

**Report-and-continue cases**:

- Orphan files found → report, don't delete
- Ambiguous justification → report as Implicit
- Unknown file types → include in tree anyway

## Integration Points

### Framework Integration

- **Workflow 01-design-new-component.md**: Step 6 should invoke `Skill(skill="audit")`
- **Intent router**: Suggests this skill for documentation/audit requests

### Related Skills

- **link-audit**: Detailed wikilink graph analysis (complementary)
- **reference-map**: Generates reference graph visualization (complementary)

## Invocation

```
Skill(skill="audit")
```

Or via command:

```
/audit
```

## Report Format

```
## Audit Report

### Structure Issues Found
- Missing from INDEX.md: skills/foo/
- Extra in INDEX.md: skills/deleted/
- Broken wikilinks: [[nonexistent.md]] in X.md

### Justification Status

**Justified** (N) - spec exists:
- AXIOMS.md → specs/meta-framework.md

**Implicit** (N) - in docs, no dedicated spec:
- FRAMEWORK.md → JIT-INJECTION.md

**Orphan candidates** (N) - no reference found:
- docs/OLD-FILE.md

### Actions Taken
- Added skills/foo/ to INDEX.md
- Updated README.md commands table

### Requires Human Review
- Orphan: docs/OLD-FILE.md - delete or create spec?
```

## Relationships

### Depends On

- [[documentation-architecture]] - Defines purpose of README.md, INDEX.md, FRAMEWORK.md
- [[specs/framework-health.md|framework-health]] - Health metrics and CI/CD enforcement
- [[INDEX.md]] - File accounting target
- [[RULES.md]] - Enforcement mapping target

### Used By

- Pre-commit hooks for local enforcement
- GitHub Actions for CI enforcement
- Framework maintainers for manual audits

## Design Rationale

**Why combine structure, justification, and index updates?**

These are interdependent checks. Structure issues (missing files) often indicate justification gaps. Index updates fix the detected issues. Running them together provides a complete governance picture.

**Why hybrid agent + scripts?**

Scripts provide fast, deterministic checks for CI/CD. Agents provide semantic understanding for classification decisions and intelligent updates that preserve human-written content.

Implements:

- [[AXIOMS]] #20 (Maintain Relational Integrity)
- [[AXIOMS]] #29 (One Spec Per Feature) - by flagging files without specs
- [[HEURISTICS]] H7 (Link, Don't Repeat) - by validating references
