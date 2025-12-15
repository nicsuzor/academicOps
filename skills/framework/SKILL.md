---
name: framework
description: Categorical framework governance. Treats every change as a universal rule. Delegates user data operations to skills.
allowed-tools: Read,Grep,Glob,Edit,Write,Skill,AskUserQuestion
version: 4.1.0
permalink: skills-framework-skill
---

# Framework Conventions Skill

**When to invoke**: Before modifying framework infrastructure OR when making any change that should become a generalizable pattern.

**What it provides**: Categorical analysis, conventions, delegation to appropriate skills, **compliance assessment**.

**What it doesn't do**: Ad-hoc one-off changes. Every action must be justifiable as a universal rule.

## Logical Derivation System

This framework is a **validated logical system**. Every component must be derivable from axioms and supporting documents.

### Authoritative Source Chain (Read in Order)

| Priority | Document | Contains | Location |
|----------|----------|----------|----------|
| 1 | AXIOMS.md | Inviolable principles | `$AOPS/AXIOMS.md` |
| 2 | HEURISTICS.md | Empirically validated guidance (revisable) | `$AOPS/HEURISTICS.md` |
| 3 | VISION.md | What we're building, success criteria | `$ACA_DATA/projects/aops/VISION.md` |
| 4 | ROADMAP.md | Current status, done/planned/issues | `$ACA_DATA/projects/aops/ROADMAP.md` |
| 5 | This skill | Conventions derived from above | `$AOPS/skills/framework/SKILL.md` |
| 6 | README.md | Feature inventory | `$AOPS/README.md` |
| 7 | INDEX.md | File tree | `$AOPS/INDEX.md` |

**Derivation rule**: Every convention in this skill MUST trace to an axiom or vision statement. If it can't, the convention is invalid.

### Compliance Assessment Protocol

When assessing any component for compliance:

1. **Trace to axiom**: Which axiom(s) justify this component's existence?
2. **Check placement**: Does INDEX.md define where this belongs?
3. **Verify uniqueness**: Is this information stated exactly once (DRY)?
4. **Confirm purpose**: Does VISION.md support this capability?

If ANY check fails → component is non-compliant → refactor or delete.

### HALT Protocol (MANDATORY)

**When you encounter something you cannot derive:**

1. **STOP** - Do not guess, do not work around
2. **STATE** - "I cannot determine [X] because [Y]"
3. **ASK** - Use AskUserQuestion to get clarification
4. **DOCUMENT** - Once resolved, add the rule to appropriate location

**Examples requiring HALT:**
- File doesn't fit any defined category
- Two axioms appear to conflict
- Placement is ambiguous (could go in multiple locations)
- New pattern with no existing convention

## Framework Introspection (MANDATORY - FIRST STEP)

**Before ANY action**, load the framework structure and verify consistency.

### Step 1: Load Authoritative Documents

Read these files in order (use Read tool):

1. `$AOPS/AXIOMS.md` - Inviolable principles
2. `$AOPS/HEURISTICS.md` - Empirically validated guidance
3. `$AOPS/INDEX.md` - Authoritative file tree
4. `$ACA_DATA/projects/aops/VISION.md` - Goals and scope
5. `$ACA_DATA/projects/aops/ROADMAP.md` - Current status

**Do NOT proceed until all 5 documents are loaded.** This ensures every action is informed by the complete framework state.

### Step 2: Run Consistency Checks

Before accepting ANY proposed change, verify ALL of:

| Check | Question | Failure = HALT |
|-------|----------|----------------|
| Axiom derivation | Which axiom(s) justify this change? | Cannot identify axiom |
| INDEX placement | Does INDEX.md define where this belongs? | Location not in INDEX |
| DRY compliance | Is this information stated exactly once? | Duplicate exists elsewhere |
| VISION alignment | Does VISION.md support this capability? | Outside stated scope |
| Namespace uniqueness | Does this name conflict with existing skill/command/hook/agent? | Name collision detected |

### Step 3: HALT Protocol on Inconsistency

If ANY check fails:

1. **STOP** - Do not proceed with the change
2. **REPORT** - State exactly which check failed and why
3. **ASK** - Use AskUserQuestion: "How should we resolve this inconsistency?"
4. **WAIT** - Do not attempt workarounds or auto-fixes

**Example HALT output:**
```
FRAMEWORK INTROSPECTION FAILED

Check failed: DRY compliance
Issue: Proposed content duplicates information in $AOPS/README.md lines 45-52
Options:
1. Reference existing content instead of duplicating
2. Move authoritative content to new location
3. Proceed anyway (requires explicit user approval)
```

---

## Categorical Imperative (MANDATORY)

Per AXIOMS.md #1: Every action must be justifiable as a universal rule derived from these AXIOMS.

### Before ANY Change

1. **State the rule**: What generalizable principle justifies this action?
2. **Check rule exists**: Is this in AXIOMS, this skill, or documented elsewhere?
3. **If no rule exists**: Propose the rule. Get user approval. Document it.
4. **Ad-hoc actions are PROHIBITED**: If you can't generalize it, don't do it.

### File Boundaries (ENFORCED)

| Location | Action | Reason |
|----------|--------|--------|
| `$AOPS/*` | Direct modification OK | Public framework files |
| `$ACA_DATA/*` | **MUST delegate to skill** | User data requires repeatable processes |

**Rationale**: If we need to operate on user data, we build a skill for it. One-off scripts and manual changes are prohibited. This ensures every process is generalizable and repeatable.

### When Operating on User Data

1. **Identify the operation category**: What type of work is this?
2. **Find existing skill**: Does a skill already handle this? (bmem, tasks, analyst, etc.)
3. **If skill exists**: Invoke it with `FRAMEWORK SKILL CHECKED` token
4. **If NO skill exists**: Create one first, THEN invoke it

### Creating Skills for New Operations

When no skill handles a needed user data operation:

1. **Use this skill** to create the new skill (skill creation is a framework operation)
2. Follow "Adding a Skill" pattern in Component Patterns section
3. Skill must be generalizable (not one-off)
4. Then invoke the new skill to do the actual work

**This is recursive**: Creating a skill uses the framework skill. The framework skill provides the patterns. Skill creation happens in `$AOPS/skills/` (framework files = direct modification OK).

**Example**: Need to clean up non-compliant files in `$ACA_DATA/`?
1. Invoke `framework` skill
2. Framework skill creates `cleanup` skill in `$AOPS/skills/cleanup/`
3. Framework skill then invokes `cleanup` skill to do the work
4. Future cleanup uses the same skill

- ❌ Wrong: Directly delete files in `$ACA_DATA/`
- ✅ Right: Create skill via framework, then invoke it

### Delegation Output Format

When delegating to a skill:

```
FRAMEWORK SKILL CHECKED

Categorical Rule: [the universal rule justifying this action]
Skill: [skill to invoke]
Operation: [what the skill should do]
Scope: [files/directories affected]
```

## Framework Paths

```
$AOPS/                     # Framework repo (academicOps)
├── AXIOMS.md              # Inviolable principles
├── skills/                # Agent skills (invoke via Skill tool)
├── hooks/                 # Lifecycle automation
├── commands/              # Slash commands
├── agents/                # Agentic workflows
├── tests/                 # Framework tests (pytest)
├── lib/                   # Shared utilities
├── scripts/               # Deployment scripts
└── config/                # Configuration files

$ACA_DATA/                 # User data repo
├── ACCOMMODATIONS.md      # Work style
├── CORE.md                # User context
├── STYLE-QUICK.md         # Writing style
├── tasks/                 # Task data
└── projects/aops/         # Framework project data
    ├── VISION.md          # Goals (edit in place)
    ├── ROADMAP.md         # Progression (edit in place)
    ├── specs/             # Design documents
    ├── experiments/       # Hypothesis → results
    ├── learning/          # Patterns from experience
    ├── decisions/         # Architectural choices
    ├── bugs/              # Bug investigations (delete when fixed)
    └── qa/                # Verification reports (delete when resolved)
```

## Core Conventions (with Axiom Derivations)

Each convention traces to its source axiom. If a convention lacks derivation, it's invalid.

### Folder Naming Convention

Each folder should have a markdown file with the same name as the folder.

```
projects/aops/aops.md      # ✅ Core file for aops/ folder
skills/bmem/bmem.md        # ✅ Core file for bmem/ folder
```

**Derives from**: AXIOMS #8 (Single-Purpose Files) - one defined audience, one purpose per file.

### Single Source of Truth

Each piece of information exists in exactly ONE location:

| Information | Authoritative Location |
|-------------|------------------------|
| Principles | `$AOPS/AXIOMS.md` |
| File tree | `$AOPS/INDEX.md` |
| Feature inventory | `$AOPS/README.md` |
| User context | `$ACA_DATA/CORE.md` |
| Work style | `$ACA_DATA/ACCOMMODATIONS.md` |
| Framework vision | `$ACA_DATA/projects/aops/VISION.md` |
| Framework status | `$ACA_DATA/projects/aops/ROADMAP.md` |

**Derives from**: AXIOMS #9 (DRY, Modular, Explicit) - one golden path, no duplication.

**Pattern**: Reference, don't repeat.

### Delegation Token

When `/meta` or `framework` skill delegates to implementation skills (python-dev, analyst), the delegation MUST include:

```
FRAMEWORK SKILL CHECKED
```

Implementation skills MUST refuse requests without this token.

**Derives from**: AXIOMS #1 (Categorical Imperative) - every action flows through generalizable framework process.

### Standard Tools

- Package management: `uv`
- Testing: `pytest`
- Git hooks: `pre-commit`
- Type checking: `mypy`
- Linting: `ruff`

**Derives from**: AXIOMS #9 (Use Standard Tools) - one golden path per job.

### Skills are Read-Only

Skills in `skills/` MUST NOT contain dynamic data. All mutable state goes in `$ACA_DATA/`.

**Derives from**: AXIOMS #11 (Skills are Read-Only) - skills distributed read-only, dynamic data in `$ACA_DATA/`.

### Trust Version Control

- Never create backup files (`.bak`, `_old`, etc.)
- Edit directly, git tracks changes
- Commit AND push after completing work

**Derives from**: AXIOMS #12 (Trust Version Control) - git is the backup system.

## Documentation Structure (Authoritative)

The framework has exactly these core documents. No others.

**Derives from**: AXIOMS #8 (Single-Purpose Files) + #9 (DRY) - each document has one purpose, no overlap.

### Framework Documentation ($AOPS/)

| Document | Purpose | Contains |
|----------|---------|----------|
| README.md | Entry point | Feature inventory (skills, commands, hooks, agents) with how-to-invoke |
| AXIOMS.md | Principles ONLY | Inviolable rules - NO enforcement, NO examples, NO implementation |
| INDEX.md | File tree | Complete directory structure |

**AXIOMS.md rule**: Axioms are pure principles. Enforcement mechanisms belong in this skill. Implementation details belong in component docs.

### Project Documentation ($ACA_DATA/projects/aops/)

| Document | Purpose | Contains |
|----------|---------|----------|
| VISION.md | Goals | What we're building, success criteria, scope boundaries |
| ROADMAP.md | Status | Done / In Progress / Planned / Known Issues |
| learning/ | Patterns | Thematic files for failure patterns and lessons |

### Documentation Rules

1. **VISION.md is grounded** - Academic support framework, not autonomous research.
2. **ROADMAP.md is simple** - Just lists: Done, In Progress, Planned, Issues.
3. **README.md has the inventory** - Every skill/command/hook with one-line purpose and how to invoke.
4. **AXIOMS.md is pure** - Principles only. No enforcement, examples, or implementation.
5. **No other core docs** - specs/, experiments/, learning/ handle everything else.

**Derives from**: AXIOMS #7 (Self-Documenting) - documentation-as-code, no separate doc files beyond these.

### Feature Inventory Format (README.md)

Each capability listed with:
- Name
- Purpose (one line)
- Invocation (how to use it)
- Test (how it's verified)

## Anti-Bloat Rules

**Derives from**: AXIOMS #9 (DRY, Modular, Explicit) + VISION (Minimal maintenance).

### File Limits

- Skill files: 500 lines max
- Documentation chunks: 300 lines max
- Approaching limit = Extract and reference

### Prohibited Bloat

1. Multi-line summaries after references (brief inline OK)
2. Historical context ("What's Gone", migration notes)
3. Meta-instructions ("How to use this file")
4. Duplicate explanations across files

### File Creation

New files PROHIBITED unless:
1. Clear justification (existing files insufficient)
2. Integration test validates purpose
3. Test passes before commit

**Derives from**: AXIOMS #17 (Write for Long Term) - no single-use files.

## Component Patterns

**Testing requirement**: All framework tests must be **e2e against production code with live data**. No unit tests, no mocks of internal code. See `references/testing-with-live-data.md`.

### Adding a Skill

1. Create `skills/<name>/SKILL.md`
2. Follow YAML frontmatter format (see existing skills)
3. Keep under 500 lines
4. Add e2e test (NOT unit test - test real behavior with real data)

### Adding a Command

1. Create `commands/<name>.md`
2. Define YAML frontmatter (name, description, tools)
3. Commands are slash-invoked: `/name`

### Adding a Hook

1. **Read `hooks/CLAUDE.md` first** - contains architecture principles
2. Create hook in `hooks/` directory
3. Triggers: PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, Stop
4. Hooks inject context/instructions - they NEVER call LLM APIs directly

### Script Design

Scripts are SIMPLE TOOLS that agents call via Bash:

**Allowed**: Mechanical data transformation (chunking, merging)
**Prohibited**: File reading, pattern matching, filtering, reasoning

Agents orchestrate. Scripts are utilities.

## Framework Project Data (`$ACA_DATA/projects/aops/`)

Per AXIOMS.md #11 (Categorical Imperative): Every file must fit a defined category. No ad-hoc files.

### Allowed File Types and Locations

| Type | Location | Rule |
|------|----------|------|
| Vision/Strategy | `VISION.md`, `ROADMAP.md` | One file each, edited in place |
| Specifications | `specs/` | Design docs for features. Status in frontmatter: draft/approved/implemented |
| Experiments | `experiments/` | Hypothesis → results. Use `TEMPLATE.md`. Date-prefix filenames |
| Learning | `learning/` | Patterns extracted from experience. Thematic files, append-only |
| Decisions | `decisions/` | Architectural choices with rationale. Immutable once made |
| Bugs | `bugs/` | Bug investigations. Delete when fixed |
| QA | `qa/` | Verification reports. Delete after issues resolved |

### Prohibited

- ❌ Root-level working documents (session notes, plans, summaries)
- ❌ Files without clear category
- ❌ Duplicate content across files
- ❌ "Index" or "Summary" files (use search instead)

### Before Creating a File

1. **Does it fit a category above?** If no → don't create it
2. **Does similar content exist?** If yes → edit existing file
3. **Is this session-specific?** If yes → don't persist it (use conversation context)

### Cleanup = Compliance Check

Cleanup is NOT a separate process. It's verifying files comply with these rules:
- Files outside defined locations → delete or move
- Duplicate content → consolidate
- Session detritus → delete (learning already in conversation/bmem)

## Compliance Refactoring Workflow

When bringing components into compliance with this logical system:

### Step 1: Assess Current State

For each component (file, convention, pattern):
1. Can its existence be derived from AXIOMS + VISION?
2. Is it in the location defined by INDEX.md?
3. Is its information unique (not duplicated elsewhere)?

### Step 2: Classify the Issue

| Issue Type | Action |
|------------|--------|
| No axiom derivation | Delete or propose new axiom (HALT, ask user) |
| Wrong location | Move to correct location per INDEX.md |
| Duplicated content | Consolidate to single authoritative source |
| Missing from INDEX | Add to INDEX.md or delete if invalid |
| Ambiguous placement | **HALT** - ask user to clarify |

### Step 3: Incremental Change

- Fix ONE issue at a time
- Commit after each fix
- Verify no regressions (run tests)
- Update ROADMAP.md if significant

### Step 4: Document the Rule

If you discovered a new pattern:
1. Propose the generalizable rule
2. Get user approval
3. Add to this skill with axiom derivation
4. Never apply ad-hoc fixes without rules

**Derives from**: AXIOMS #1 (Categorical Imperative) - every action must be justifiable as universal rule.

## Before You Modify

1. **Check existing patterns** - Similar component exists?
2. **Verify paths** - Right location per conventions?
3. **Validate scope** - Single responsibility?
4. **Plan test** - How will you verify it works?
5. **Trace to axiom** - Which principle justifies this?

## When Done

Return "FRAMEWORK SKILL CHECKED" to your caller if providing context for delegation.
