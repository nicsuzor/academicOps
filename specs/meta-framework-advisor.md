---
title: Meta-Framework Advisor
type: spec
category: spec
status: implemented
permalink: meta-framework-advisor
tags:
  - spec
  - framework
  - governance
  - strategic-partner
  - categorical-imperative
---

# Meta-Framework Advisor

**Status**: Implemented

## Workflow

```mermaid
graph TD
    A[/meta Invoked] --> B[Load Full Context]
    B --> C[AXIOMS.md]
    B --> D[HEURISTICS.md]
    B --> E[VISION.md]
    B --> F[ROADMAP.md]

    G[Proposed Change] --> H{Consistency Checks}
    H --> I{Axiom Derivation?}
    H --> J{INDEX Placement?}
    H --> K{DRY Compliance?}
    H --> L{VISION Alignment?}

    I -->|Fail| M[HALT Protocol]
    J -->|Fail| M
    K -->|Fail| M
    L -->|Fail| M

    I -->|Pass| N{All Pass?}
    J -->|Pass| N
    K -->|Pass| N
    L -->|Pass| N

    N -->|Yes| O[Delegate to Implementation]
    M --> P[Report + Ask User]
```

## Problem Statement

### The Academic + Developer Dual Role

Nic is a full-time academic (research, teaching, writing) who is also building a sophisticated AI assistant framework. The framework must evolve incrementally toward an ambitious vision WITHOUT spiraling into complexity, chaos, or documentation bloat.

### Core Challenges

- **Ad-hoc changes**: One-off fixes that don't generalize, creating inconsistency
- **Framework amnesia**: Agents forget prior decisions and create duplicates
- **Documentation drift**: Information duplicated across files, conflicts emerge
- **No institutional memory**: Hard to maintain strategic alignment across sessions
- **Cognitive load**: Tracking "what we've built" falls entirely on Nic

### What's Needed

A strategic partner that:

1. **Remembers** the vision, current state, and prior decisions
2. **Guards** against documentation bloat, duplication, and complexity spiral
3. **Enforces** categorical governance - every change must be a universal rule
4. **Ensures** testing, quality, and integration remain robust
5. **Enables trust** so Nic can delegate framework decisions confidently

## Solution

Categorical framework governance via the `/meta` command and `framework` skill. Every change must be justifiable as a universal rule derived from axioms.

### Entry Points

| Entry             | Purpose                                                          |
| ----------------- | ---------------------------------------------------------------- |
| `/meta` command   | Strategic brain - loads context, makes decisions, delegates work |
| `framework` skill | Governance layer - consistency checks, HALT protocol             |

### How It Works

**1. Mandatory Context Loading**

Before any action, load authoritative documents:

1. AXIOMS.md - Inviolable principles
2. HEURISTICS.md - Empirically validated guidance
3. INDEX.md - Authoritative file tree
4. VISION.md - Goals and scope
5. ROADMAP.md - Current status

**2. Consistency Checks**

Before accepting any change, verify:

| Check                | Question                         | Failure = HALT        |
| -------------------- | -------------------------------- | --------------------- |
| Axiom derivation     | Which axiom(s) justify this?     | Cannot identify axiom |
| INDEX placement      | Is location defined?             | Location not in INDEX |
| DRY compliance       | Information stated exactly once? | Duplicate exists      |
| VISION alignment     | Is this in scope?                | Outside stated scope  |
| Namespace uniqueness | Name collision?                  | Name already used     |

**3. HALT Protocol**

On any check failure:

1. **STOP** - Do not proceed
2. **REPORT** - State which check failed
3. **ASK** - Use AskUserQuestion for clarification
4. **WAIT** - No workarounds

**4. File Boundary Enforcement**

| Location      | Action                 |
| ------------- | ---------------------- |
| `$AOPS/*`     | Direct modification OK |
| `$ACA_DATA/*` | MUST delegate to skill |

**5. Delegation Protocol**

When delegating to implementation skills:

```
FRAMEWORK SKILL CHECKED

Categorical Rule: [universal rule justifying action]
Skill: [skill to invoke]
Operation: [what to do]
Scope: [files affected]
```

## Three-Layer Information Architecture

```
Layer 1: Authoritative Framework State (Always Current)
  ├── $AOPS/AXIOMS.md - Foundational principles
  ├── $AOPS/VISION.md - Ambitious end state
  └── $AOPS/ROADMAP.md - Current stage and priorities

Layer 2: Dynamic Tracking (Session-to-session learning)
  ├── $AOPS/HEURISTICS.md - Empirically validated patterns
  └── GitHub Issues - Episodic observations and experiments

Layer 3: Automation Instructions
  └── $AOPS/skills/framework/SKILL.md - How to maintain framework
```

**Key principles**:

- State (layers 1-2) is separate from instructions (layer 3)
- Authoritative sources are discoverable (top-level)
- Learning accumulates in HEURISTICS.md and GitHub Issues
- Instructions reference state, don't duplicate it

## Scope

### IN SCOPE

- **Context Management**: Maintain authoritative current state, make it queryable
- **Strategic Advocacy**: Ensure agents understand vision, redirect misaligned work
- **Documentation Guardianship**: Prevent bloat, enforce single source of truth
- **Quality Assurance**: Tests exist and pass, tools work together
- **Continuity**: Provide context when returning after time away

### OUT OF SCOPE

- Individual feature implementation (other skills)
- User's academic work (separate from framework)
- Day-to-day task management (tasks skill)

## Relationships

### Depends On

- AXIOMS.md - Source of inviolable principles
- HEURISTICS.md - Empirical guidance
- INDEX.md - Authoritative structure

### Delegates To

- python-dev - Python implementation
- analyst - Data analysis
- remember - Knowledge persistence
- tasks - Task management

## Success Criteria

1. **No ad-hoc changes**: Every modification traces to an axiom
2. **Consistency**: Changes don't conflict with existing patterns
3. **Single source of truth**: No duplicate information created
4. **Correct placement**: Files in locations defined by INDEX.md
5. **Context recovery**: When invoked, partner loads and provides current state
6. **No duplication**: Partner catches attempts to create what exists
7. **Trust enabled**: Nic delegates framework decisions without reviewing everything

## Design Rationale

**Why categorical governance?**

Per AXIOMS #1: "Every action taken must be justifiable as a universal rule." One-off changes accumulate into inconsistency. By requiring every change to be generalizable, the framework stays coherent.

**Why mandatory introspection?**

Agents forget context between sessions. Loading authoritative documents ensures every action is informed by complete framework state, preventing duplicate creation and conflicting changes.

**Why file boundary enforcement?**

User data (`$ACA_DATA`) requires repeatable processes. Direct manipulation creates one-off changes that can't be reproduced. Skills encode repeatable patterns.

**Why HALT protocol?**

When derivation fails, the framework lacks a rule for this case. Guessing creates inconsistency. HALTing and asking ensures new rules are explicitly approved.
