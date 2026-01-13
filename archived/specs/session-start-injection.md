---
title: SessionStart Injection Specification
type: spec
category: spec
status: Draft
permalink: session-start-injection-spec
tags: [framework, hooks, architecture, session]
created: 2025-12-30
---

# SessionStart Injection Specification

## Purpose

Define what information the framework injects when Claude Code launches - the **foundation context** every session starts with before any user prompt.

## Architectural Position

```
Claude Code launched
    ↓
SessionStart hook fires
    ↓
Context injected (THIS SPEC)
    ↓
Agent has baseline knowledge
    ↓
User submits first prompt
    ↓
...
```

This is the **entry point** of the framework. Everything downstream assumes this baseline exists.

## Information Categories

SessionStart injection provides exactly four categories of information:

### 1. Navigation (FRAMEWORK-PATHS.md)

**Purpose**: WHERE things are - resolved paths for this session.

**Contents**:

- `$AOPS/` - Framework source root (absolute path)
- `$ACA_DATA/` - User data root (absolute path)
- Standard subdirectories (commands/, skills/, hooks/, agents/, tasks/, etc.)
- Path table with common files

**Contract**:

- All path variables (`$AOPS`, `$ACA_DATA`) are expanded to absolute paths at injection time
- Agents MUST NOT guess paths - all needed paths are provided here
- Missing or incorrect paths = framework misconfiguration = fail

**Rationale**: Agents frequently guess paths (AXIOM violation #2 "Don't make shit up"). Explicit path injection eliminates this failure mode.

### 2. Principles (AXIOMS.md)

**Purpose**: WHAT agents CAN'T do - inviolable rules with no exceptions.

**Contents**:

- Numbered principles (currently ~30)
- Each principle is atomic and actionable
- No evidence, examples, or enforcement details

**Contract**:

- Every principle applies to every session
- Agents MUST follow these regardless of context
- Violations are never acceptable (no "usually" or "in most cases")

**Rationale**: Core behavior constraints must be present BEFORE any prompt. Can't rely on agents loading these themselves - they might skip or misinterpret.

### 3. Patterns (HEURISTICS.md)

**Purpose**: HOW agents SHOULD act - empirically validated guidance.

**Contents**:

- Numbered heuristics (H1, H2, etc.) with rule statement only
- No metadata (confidence, evidence, axiom refs) - that lives in bd issues
- Revision protocol pointing to `/log` skill

**Contract**:

- Heuristics are default behavior, not inviolable
- User can override with explicit instruction
- Agents should follow unless there's specific reason not to
- Evidence and traceability live in bd issues (label: `learning`)

**Rationale**: Learned patterns surface proven approaches. Metadata stripped for token efficiency - agents need rules, not provenance.

### 4. Identity (CORE.md)

**Purpose**: WHO the agent serves - user context and preferences.

**Contents**:

- User identity and role
- Communication preferences
- Tools and environment
- Workflow requirements

**Contract**:

- This is the authoritative source for user context
- Preferences here override generic behavior
- Updates to user context go here (single source of truth)

**Rationale**: Personalization requires knowing the user. Loading identity at session start ensures consistent treatment.

## Implementation Requirements

### Fail-Fast Behavior (See [[AXIOMS.md]])

All four files are **mandatory**. If ANY file is:

- Missing → Exit code 1, session cannot start
- Empty → Exit code 1, session cannot start
- Malformed → Best effort parse, warn on stderr

**Rationale**: Silent degradation leads to mysterious failures. Better to fail loudly at session start than produce confused behavior later.

### Injection Format

Files are concatenated with clear section headers:

```
# Framework Paths (FRAMEWORK-PATHS.md)
[content with paths expanded]

---

# Framework Principles (AXIOMS.md)
[content]

---

# Framework Heuristics (HEURISTICS.md)
[content]

---

# User Context (CORE.md)
[content]
```

### Path Variable Expansion

Before injection, replace:

- `$AOPS` → absolute path to framework root
- `$ACA_DATA` → absolute path to user data root

This happens at runtime so content is session-specific.

## What's NOT Included (and Why)

| Candidate         | Decision | Rationale                                        |
| ----------------- | -------- | ------------------------------------------------ |
| ROADMAP.md        | Excluded | Changes frequently; load on-demand when relevant |
| VISION.md         | Excluded | Strategic context, not operational baseline      |
| README.md         | Excluded | Reference doc, not foundational context          |
| Project CLAUDE.md | Excluded | Loaded separately by Claude Code per-repo        |
| Recent history    | Excluded | Use memory server queries at prompt-time         |
| Active tasks      | Excluded | Stale quickly; better at prompt-time via /do     |

**Design principle**: SessionStart injection is **minimal and complete** - only what EVERY session needs, nothing extra.

## Future Considerations

### Potential Additions (requires evidence)

- **ACCOMMODATIONS.md injection**: Currently referenced via CORE.md. Could be injected directly if evidence shows agents miss it.
- **Capability index**: List of available skills/commands. Currently in README.md; could be condensed injection.

### NOT Candidates

- Dynamic state (tasks, sessions) - changes too fast, use prompt-time queries
- Project-specific context - already handled by per-repo CLAUDE.md
- Memory server content - use semantic search, not bulk injection

## Verification

### Test: Session starts with all context

```bash
# Verify all files exist and are non-empty
test -s $AOPS/FRAMEWORK-PATHS.md
test -s $AOPS/AXIOMS.md
test -s $AOPS/HEURISTICS.md
test -s $ACA_DATA/CORE.md
```

### Test: Context appears in session

After session start, agent should be able to answer:

- "What is $AOPS?" → Returns absolute path (not variable)
- "What are the axioms?" → Can list principles
- "Who is the user?" → Returns user context from CORE.md

### Test: Fail-fast on missing file

```bash
# Temporarily rename file
mv $AOPS/AXIOMS.md $AOPS/AXIOMS.md.bak
# Start session → should fail with exit code 1
# Restore
mv $AOPS/AXIOMS.md.bak $AOPS/AXIOMS.md
```

## Related Documents

- [[sessionstart_load_axioms.py]] - Implementation
- [[FLOW]] - Execution flow diagrams
- [[AXIOMS.md]] - Inviolable principles
- [[HEURISTICS.md]] - Empirical patterns
- [[FRAMEWORK-PATHS.md]] - Path configuration
- [[CORE.md]] - User context

## Acceptance Criteria

- [ ] SessionStart injection loads exactly 4 files (FRAMEWORK, AXIOMS, HEURISTICS, CORE)
- [ ] All path variables expanded to absolute paths
- [ ] Missing/empty files cause exit code 1 (fail-fast)
- [ ] Injection appears in session context before first prompt
- [ ] execution-flow.md diagram starts with "Claude Code launched", not "User submits prompt"
