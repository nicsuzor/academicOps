---
name: framework
description: Categorical framework governance. Treats every change as a universal rule. Delegates user data operations to skills.
allowed-tools: Read,Grep,Glob,Edit,Write,Skill
version: 3.0.0
permalink: skills-framework-skill
---

# Framework Conventions Skill

**When to invoke**: Before modifying framework infrastructure OR when making any change that should become a generalizable pattern.

**What it provides**: Categorical analysis, conventions, delegation to appropriate skills.

**What it doesn't do**: Ad-hoc one-off changes. Every action must be justifiable as a universal rule.

## Categorical Imperative (MANDATORY)

Per AXIOMS.md #11: Every action must be justifiable as a universal rule. This skill enforces that principle.

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

## Core Conventions

### Folder Naming Convention

Each folder should have a markdown file with the same name as the folder. This is the core/index content for that folder.

```
projects/aops/aops.md      # ✅ Core file for aops/ folder
skills/bmem/bmem.md        # ✅ Core file for bmem/ folder
experiments/experiments.md # ✅ Core file for experiments/ folder
```

### Single Source of Truth

Each piece of information exists in exactly ONE location:
- Principles: `AXIOMS.md`
- Directory structure: `README.md`
- User context: `$ACA_DATA/CORE.md`
- Work style: `$ACA_DATA/ACCOMMODATIONS.md`

**Pattern**: Reference, don't repeat.

### Delegation Token

When `/meta` or `framework` skill delegates to implementation skills (python-dev, analyst), the delegation MUST include:

```
FRAMEWORK SKILL CHECKED
```

Implementation skills MUST refuse requests without this token.

### Standard Tools

- Package management: `uv`
- Testing: `pytest`
- Git hooks: `pre-commit`
- Type checking: `mypy`
- Linting: `ruff`

### Skills are Read-Only

Skills in `skills/` MUST NOT contain dynamic data. All mutable state goes in `$ACA_DATA/`.

### Trust Version Control

- Never create backup files (`.bak`, `_old`, etc.)
- Edit directly, git tracks changes
- Commit AND push after completing work

## Anti-Bloat Rules

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

## Component Patterns

### Adding a Skill

1. Create `skills/<name>/SKILL.md`
2. Follow YAML frontmatter format (see existing skills)
3. Keep under 500 lines
4. Add integration test

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

## Before You Modify

1. **Check existing patterns** - Similar component exists?
2. **Verify paths** - Right location per conventions?
3. **Validate scope** - Single responsibility?
4. **Plan test** - How will you verify it works?

## When Done

Return "FRAMEWORK SKILL CHECKED" to your caller if providing context for delegation.
