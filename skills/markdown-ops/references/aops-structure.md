# academicOps Repository Structure Rules

This document defines where different types of markdown files belong in the academicOps framework.

## Core Directory Structure

```
$ACADEMICOPS/                  # Framework root
├── agents/                    # Subagent definitions (<500 lines each)
├── chunks/                    # Shared context modules (DRY single sources)
├── commands/                  # Slash command definitions
├── config/                    # Client configurations
├── core/                      # Auto-loaded at SessionStart
├── docs/                      # Framework documentation
│   ├── bots/                  # Agent development context
│   ├── _CHUNKS/               # Domain-specific documentation
│   ├── methodologies/         # Methodology documentation
│   ├── _UNUSED/               # Archived legacy docs
│   ├── AUDIT.md               # Current state vs desired state
│   ├── INSTRUCTION-INDEX.md   # Complete file registry
│   └── [other framework docs]
├── experiments/               # Experiment logs (YYYY-MM-DD_name.md)
├── hooks/                     # Runtime behavior enforcement
├── scripts/                   # Automation tools
├── skills/                    # Packaged skills
│   └── [skill-name]/
│       ├── SKILL.md           # <300 lines, YAML frontmatter
│       ├── resources/         # MANDATORY symlinks to chunks/
│       ├── scripts/           # Executable code
│       ├── references/        # Documentation
│       └── assets/            # Output files
├── tests/                     # Integration & unit tests
├── ARCHITECTURE.md            # System design documentation
├── CLAUDE.md                  # Project instructions (auto-loaded)
├── LICENSE
└── README.md                  # Authoritative specification
```

## File Placement Rules

### Agents (`agents/*.md`)

**Purpose**: Orchestrate skills, provide agent-specific authority

**When to create here**:

- Creating new subagent workflow
- Defining agent with specific tool permissions
- Orchestrating multiple skills

**Requirements**:

- YAML frontmatter: `name`, `description`
- <500 lines total
- MANDATORY skill-first pattern (invoke skill before work)
- Reference skills, don't duplicate workflows

**Naming**: `AGENT-NAME.md` (uppercase) or `agent-name.md` (lowercase)

### Skills (`skills/[skill-name]/SKILL.md`)

**Purpose**: Reusable workflows, domain expertise

**When to create here**:

- Creating portable, reusable workflow
- Packaging domain-specific knowledge
- Building tool integration

**Requirements**:

- YAML frontmatter: `name`, `description`, `license`, `permalink`
- SKILL.md <300 lines
- MANDATORY `resources/` directory with symlinks
- Follow anti-bloat checklist

**Structure**:

```
skills/skill-name/
├── SKILL.md              # Main skill file
├── resources/            # MANDATORY
│   ├── SKILL-PRIMER.md → ../../chunks/SKILL-PRIMER.md
│   ├── AXIOMS.md → ../../chunks/AXIOMS.md
│   └── INFRASTRUCTURE.md → ../../chunks/INFRASTRUCTURE.md  # Framework-touching only
├── scripts/              # Optional
├── references/           # Optional
└── assets/               # Optional
```

### Commands (`commands/*.md`)

**Purpose**: User-facing shortcuts to load workflows

**When to create here**:

- Creating slash command (e.g., `/trainer`, `/analyst`)
- Building user shortcut to agent/skill

**Requirements**:

- YAML frontmatter: `description`
- MANDATORY skill-first pattern
- Keep under 50 lines
- Just invocation instructions, not content duplication

### Chunks (`chunks/*.md`)

**Purpose**: DRY single sources for universal concepts

**When to create here**:

- Content needed by multiple agents/skills
- Universal principles or standards
- Framework infrastructure knowledge

**Current files**:

- `AXIOMS.md` - Universal principles (97 lines)
- `INFRASTRUCTURE.md` - Framework structure (52 lines)
- `SKILL-PRIMER.md` - Skill context (19 lines)
- `AGENT-BEHAVIOR.md` - Conversational rules (26 lines)

**Requirements**:

- Referenced by `core/_CORE.md`
- Symlinked to `skills/*/resources/`
- Never duplicated elsewhere
- Integration tested

### Core (`core/*.md`)

**Purpose**: Auto-loaded context at SessionStart

**When to create here**:

- Universal instructions for all agents
- Development standards
- Testing requirements
- Style guidelines

**Current files**:

- `_CORE.md` - References chunks/
- `DEVELOPMENT.md` - Development standards
- `TESTING.md` - Testing requirements
- `DEBUGGING.md` - Debugging workflow
- `STYLE.md` - Writing style guide

### Documentation (`docs/`)

#### Framework Development (`docs/bots/`)

**Purpose**: Agent development and framework context

**When to create here**:

- Best practices documentation
- Framework architecture guides
- Agent development patterns
- Skills inventory

**Current files**:

- `BEST-PRACTICES.md` - Evidence-based guidance
- `skills-inventory.md` - Skill catalog
- `skill-invocation-guide.md`
- `delegation-architecture.md`
- `INDEX.md`

#### Domain Docs (`docs/_CHUNKS/`)

**Purpose**: Domain-specific documentation loaded by skills

**When to create here**:

- Python/dbt/Streamlit/Seaborn documentation
- Technology-specific guides
- Testing methodology docs

**Examples**:

- `PYTHON-DEV.md`, `DBT.md`, `HYDRA.md`
- `SEABORN.md`, `STATSMODELS.md`, `STREAMLIT.md`
- `E2E-TESTING.md`, `FAIL-FAST.md`, `GIT-WORKFLOW.md`

#### Framework Docs (`docs/`)

**When to create here**:

- Framework-level documentation
- Audit reports
- Deployment guides
- Testing documentation

**Special files**:

- `AUDIT.md` - Current state tracking
- `INSTRUCTION-INDEX.md` - Complete file registry
- `TESTING.md` - Testing documentation
- `DEPLOYMENT.md` - Deployment guides

### Experiments (`experiments/YYYY-MM-DD_name.md`)

**Purpose**: Document all framework changes with metrics

**When to create here**:

- MANDATORY for ALL framework changes
- Testing new patterns
- Measuring impact of modifications

**Naming**: `YYYY-MM-DD_descriptive-name.md`

**Required structure**:

```markdown
# Experiment Name

## Metadata

- Date: YYYY-MM-DD
- Issue: #NNN
- Commit: [hash]
- Model: [model-name]

## Context

[Background and motivation]

## Hypothesis

[What you expect to happen]

## Changes Made

[Specific modifications]

## Success Criteria

[How to measure if this worked]

## Results

[What actually happened]

## Outcome

[Success/Failure/Partial]

## Notes

[Additional observations]
```

### Hooks (`hooks/*.py` or `hooks/*.sh`)

**Purpose**: Automated runtime enforcement

**When to create here**:

- SessionStart automation
- PreToolUse validation
- PostToolUse conditional loading
- Stop/SubagentStop validation
- Event logging

**Requirements**:

- Python module with docstring (first line = description)
- Fail-fast implementation
- No defensive programming

### Scripts (`scripts/*.py`)

**Purpose**: Framework automation tools

**When to create here**:

- Validation scripts
- Code generation
- Setup automation

**Examples**:

- `generate_instruction_tree.py`
- `validate_instruction_tree.py`
- `setup_academicops.sh`

## Anti-Bloat Rules

Before creating any markdown file:

- [ ] Is there existing content to reference instead?
- [ ] Does this duplicate chunks/ or other files?
- [ ] Can this be consolidated with existing documentation?
- [ ] Is this the minimal effective location?
- [ ] Does file stay under limits? (Skills <300, Agents <500)

**Hard limits**:

- Skills: SKILL.md <300 lines
- Agents: <500 lines
- Adding >10 lines: GitHub issue + approval required

## File Type Decision Tree

```
START: Need to create markdown file
↓
Q1: Is this documenting a framework change/experiment?
YES → experiments/YYYY-MM-DD_name.md
NO ↓

Q2: Is this orchestrating multiple skills with agent authority?
YES → agents/AGENT-NAME.md
NO ↓

Q3: Is this a reusable, portable workflow?
YES → skills/skill-name/SKILL.md
NO ↓

Q4: Is this a user-facing shortcut?
YES → commands/command-name.md
NO ↓

Q5: Is this universal content needed by multiple components?
YES → chunks/CONCEPT.md
NO ↓

Q6: Is this framework development context?
YES → docs/bots/filename.md
NO ↓

Q7: Is this domain-specific documentation?
YES → docs/_CHUNKS/DOMAIN.md
NO ↓

Q8: Is this current state tracking?
YES → docs/AUDIT.md
NO ↓

Q9: Is this general framework documentation?
YES → docs/filename.md
NO ↓

ERROR: File may not belong in academicOps framework
Consider: Is this project-specific? Should it be in parent repo?
```

## Common Mistakes to Avoid

1. **Duplicating chunks/** - Always reference, never duplicate
2. **Creating orphaned files** - Every file should be referenced somewhere
3. **Mixing concerns** - Keep agents, skills, commands, docs separate
4. **Ignoring limits** - Skills <300 lines, Agents <500 lines
5. **Skipping experiments** - ALL changes require experiment log
6. **Missing resources/** - ALL skills need resources/ symlinks
7. **Bloated SKILL.md** - Move detailed content to references/
