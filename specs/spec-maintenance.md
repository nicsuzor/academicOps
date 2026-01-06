---
title: Spec Maintenance
type: spec
category: spec
status: implemented
permalink: spec-maintenance
tags: [spec, framework, documentation, synthesis]
---

# Spec Maintenance

**Status**: Implemented

## Workflow

```mermaid
graph TD
    A[Feature Implementation Complete] --> B[/feature-dev Phase 8]
    B --> C[Find/Create Spec]
    C --> D[Merge Implementation Details]
    D --> E[Strip Temporal Content]
    E --> F[Delete Orphan Docs]
    F --> G[Update specs/specs.md Index]

    H[/garden scan] --> I[Detect Orphan Docs]
    I --> J[Report for Synthesis]
```

Ensure specs remain the single source of truth for feature documentation.

## Problem Statement

Agents create orphan implementation files instead of updating specs. The logged case: agent created `learning/overwhelm-dashboard-implementation.md` instead of updating `specs/Cognitive Load Dashboard Spec.md`. Result: two files describing the same feature, drift between them.

**Root cause analysis** (from LOG.md):

1. **No skill enforces spec-update workflow** - `/feature-dev` ends at validation, no synthesis step
2. **"Learning" is easy filing** - path of least resistance → new file
3. **Categorical Imperative gap** - no skill for "update spec after implementation"
4. **`status: Implemented` misread as frozen** - specs are living documents
5. **H23 is advisory, not procedural** - heuristics don't enforce themselves

## User Story

**As** the framework,
**I want** specs automatically updated after implementation,
**So that** one spec per feature remains the authoritative source (per AXIOMS #29).

## Design Decision: Extend Existing Skills vs. New Skill

### Option A: New `/spec` Skill (Rejected)

Create standalone skill for spec lifecycle management.

**Against:**

- `/garden synthesize` already does spec synthesis (lines 53-82)
- `/feature-dev` already manages feature lifecycle
- Would require agents to remember another skill to invoke
- Violates H21 (Core-First Incremental Expansion) - infrastructure before need

### Option B: Extend Existing Skills (Recommended)

Wire together existing capabilities:

| Gap                                   | Fix                         | Location       |
| ------------------------------------- | --------------------------- | -------------- |
| No post-implementation spec update    | Add Phase 8: Spec Synthesis | `/feature-dev` |
| Orphan implementation docs undetected | Add orphan detection        | `/garden scan` |
| Specs.md index not maintained         | Auto-update on spec changes | `/garden`      |
| README feature inventory stale        | Check during `/qa`          | `/qa` skill    |

**Rationale:** The pieces exist. The problem is workflow, not tooling.

## Acceptance Criteria

- **AC1**: `/feature-dev` Phase 7 (Validation) includes mandatory "Update spec with implementation details" todo item
- **AC2**: `/garden scan` reports orphan implementation docs (files in learning/ that describe features with existing specs)
- **AC3**: `/garden synthesize` updates `specs/specs.md` index when operating on a spec
- **AC4**: No new skill file created - this is workflow integration

## Implementation

### Phase 1: Extend `/feature-dev`

Add to Phase 7 (Validation & Decision):

```markdown
**After validation passes (KEEP decision)**:

8. **Spec Synthesis**
   - Find or create the feature's spec in `$AOPS/specs/`
   - Merge implementation decisions into spec (design rationale, key functions, UX lessons)
   - Strip temporal content (dates, "what was built" narrative)
   - Delete orphan implementation docs (learning/, experiments/ files about this feature)
   - Verify spec is timeless, self-contained, current
```

Add mandatory TodoWrite item:

```
- [ ] Update spec with implementation details (invoke /garden synthesize)
```

### Phase 2: Extend `/garden scan`

Add orphan detection to scan mode:

```markdown
### Orphan Implementation Docs

Detect files in learning/ or experiments/ that describe features with existing specs:

1. List all files in learning/_.md and experiments/_.md
2. For each, semantic search specs/ for matching feature
3. If match found with >0.7 similarity → flag as orphan candidate
4. Report: "Found N implementation docs that should be synthesized into specs"
```

### Phase 3: Extend `/garden synthesize`

Add spec index maintenance:

```markdown
### After Synthesizing a Spec

1. Check if spec is listed in specs/specs.md
2. If not listed, add to appropriate category
3. If status changed, update the index entry
4. Commit spec + index together
```

## What This Does NOT Do

- **Does NOT maintain `$AOPS/README.md`** - Feature inventory is framework governance (stays in `/framework`)
- **Does NOT maintain `$AOPS/INDEX.md`** - File tree is framework governance (stays in `/framework`)
- **Does NOT create a new skill** - Uses existing `/garden` and `/feature-dev`

## Implementation (2025-12-27)

Approach approved: extend existing skills rather than create new one.

**Changes made**:

- `/feature-dev` Phase 8 added (Spec Synthesis) - mandatory post-validation step
- `/garden scan` extended with orphan implementation doc detection
- `/garden synthesize` extended with spec index maintenance
