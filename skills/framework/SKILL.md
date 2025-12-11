---
name: framework
description: Understand framework conventions before modifying hooks, skills, commands, or agents. Provides paths, patterns, and anti-bloat principles.
allowed-tools: Read,Grep,Glob
version: 2.0.0
permalink: skills-framework-skill
---

# Framework Conventions Skill

**When to invoke**: Before modifying framework infrastructure (hooks, skills, commands, agents, scripts).

**What it provides**: Paths, conventions, existing patterns, anti-bloat rules.

**What it doesn't do**: Strategic decisions, implementation, debugging. Use `/meta` for that.

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
    ├── STATE.md           # Current state
    ├── VISION.md          # Goals
    ├── ROADMAP.md         # Progression
    └── specs/             # Task specifications
```

## Core Conventions

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

## Before You Modify

1. **Check existing patterns** - Similar component exists?
2. **Verify paths** - Right location per conventions?
3. **Validate scope** - Single responsibility?
4. **Plan test** - How will you verify it works?

## When Done

Return "FRAMEWORK SKILL CHECKED" to your caller if providing context for delegation.
