---
title: "academicOps Architecture"
type: specification
description: "Authoritative specification defining file structure, component requirements, loading systems, and design principles for the academicOps agent framework across all repository tiers (framework, personal, project). Timeless reference documentation only - must not include progress indicators, status updates, line counts, test results, temporal labels like NEW, or any metrics that change over time."
tags:
  - architecture
  - specification
  - framework
  - reference
relations:
  - "[[chunks/AXIOMS]]"
  - "[[chunks/INFRASTRUCTURE]]"
  - "[[core/_CORE]]"
  - "[[docs/bots/BEST-PRACTICES]]"
---

# academicOps Architecture

System design and implementation for the academicOps agent framework.

---

## Core Concepts

### Modular Chunks Architecture

**Problem**: Skills don't receive SessionStart hooks, lacking framework context (paths, axioms, env vars).

**Solution**: Modular `chunks/` directory with DRY symlinks.

```
chunks/                        # Single source of truth
├── AXIOMS.md                  # Universal principles (fail-fast, DRY, etc.)
├── INFRASTRUCTURE.md          # Framework paths, $ACADEMICOPS, repo structure
├── AGENT-BEHAVIOR.md          # Conversational/agent-specific rules
└── SKILL-PRIMER.md            # Skill execution context

core/_CORE.md                  # @references chunks/ for agents
skills/*/resources/            # Symlinks to chunks/ for skills
```

**How it works**:
1. **Agents**: SessionStart loads `_CORE.md` → @references load chunks/
2. **Skills**: `@resources/AXIOMS.md` loads via symlink → `../../chunks/AXIOMS.md`
3. **DRY**: Each principle exists in EXACTLY ONE chunk file
4. **Selective loading**: Framework skills get INFRASTRUCTURE.md, others don't

### Agent Instructions vs Documentation

**`core/` and `docs/bots/` = Agent Instructions** (executable rules for AI)
- Imperative voice: "You MUST..."
- Loaded at runtime
- Example: `core/_CORE.md`, `docs/bots/BEST-PRACTICES.md`

**`docs/` (except `docs/bots/`) and root `.md` = Human Documentation**
- Descriptive voice: "The system does..."
- For developers/users
- Example: `ARCHITECTURE.md`, `README.md`

**Rule**: Never mix agent rules with human docs.

### Environment Variables

Required variables:

- `$ACADEMICOPS` - Path to framework repository (PUBLIC)
- `$ACADEMICOPS_PERSONAL` - Path to user's personal repository (PRIVATE)

Used for path resolution, three-tier loading, and hook invocation.

---

## Instruction Loading System

### SessionStart: 3-Tier `_CORE.md`

Every session automatically loads:

```
$ACADEMICOPS/core/_CORE.md              # Framework (required)
$ACADEMICOPS_PERSONAL/core/_CORE.md     # Personal (optional)
$PWD/core/_CORE.md                      # Project (optional)
```

**Loading behavior**:
- Framework tier REQUIRED (fails if missing)
- Personal/Project tiers optional (skip if missing)
- Priority in conflicts: Project > Personal > Framework

**Content via @references**:
```markdown
# core/_CORE.md
@../chunks/AXIOMS.md
@../chunks/INFRASTRUCTURE.md
@../chunks/AGENT-BEHAVIOR.md
```

### Skills: resources/ Symlinks

Skills access framework context via `resources/` directory:

```
skills/aops-trainer/
├── SKILL.md
└── resources/
    ├── AXIOMS.md → ../../chunks/AXIOMS.md
    ├── INFRASTRUCTURE.md → ../../chunks/INFRASTRUCTURE.md
    └── SKILL-PRIMER.md → ../../chunks/SKILL-PRIMER.md
```

**In SKILL.md**:
```markdown
## Framework Context
@resources/SKILL-PRIMER.md
@resources/AXIOMS.md
@resources/INFRASTRUCTURE.md  # Framework skills only
```

**Framework-touching skills**: aops-trainer, skill-creator, skill-maintenance, claude-hooks, claude-md-maintenance

**Non-framework skills**: pdf, archiver, analyst, strategic-partner (skip INFRASTRUCTURE.md)

---

## File Structure

### Framework Repository ($ACADEMICOPS)

```
$ACADEMICOPS/
├── chunks/                # Shared context modules (DRY single sources)
├── core/
│   └── _CORE.md          # References chunks/ via @notation
├── agents/                # Framework subagent definitions
├── commands/              # Framework slash command definitions
├── hooks/                 # SessionStart, PreToolUse, Stop hooks
├── scripts/               # Automation tools
├── skills/                # Skill sources (packaged to ~/.claude/skills/)
│   └── */resources/      # Symlinks to chunks/
├── docs/
│   ├── bots/             # Framework agent development instructions
│   └── *.md              # Human documentation (ARCHITECTURE.md, etc.)
└── tests/                 # Integration tests
```

### Personal Repository ($ACADEMICOPS_PERSONAL)

```
$ACADEMICOPS_PERSONAL/
├── core/
│   └── _CORE.md          # Personal overrides/additions to core axioms
├── docs/
│   └── bots/             # Personal agent development instructions
├── agents/                # Personal custom agents (optional)
├── commands/              # Personal slash commands (optional)
└── skills/                # Personal skill sources (optional)
```

### Project Repository ($PWD)

```
$PWD/
├── core/
│   └── _CORE.md          # Project-specific instructions (optional)
├── docs/
│   └── bots/             # Project-specific agent instructions (optional)
└── [project files]        # Actual project code, data, notebooks, etc.
```

---

## Component Specifications

### Agents

**Purpose**: Orchestrate skills, provide agent-specific authority

**Requirements**:
- YAML frontmatter with `name`, `description`
- <500 lines total (architectural bloat if exceeded)
- Light on procedural detail (reference skills instead)
- MANDATORY skill invocation as first step
- Load via Task tool or slash commands

**Anti-pattern**: Duplicating skill workflows inline

### Skills

**Purpose**: Reusable workflows, domain expertise, tool integrations

**Requirements**:
- YAML frontmatter: `name`, `description`, `license`, `permalink`
- SKILL.md <300 lines
- **MANDATORY**: `resources/` directory with symlinks:
  - ALL skills: SKILL-PRIMER.md, AXIOMS.md
  - Framework-touching: + INFRASTRUCTURE.md
- Framework Context section at top (references @resources/)
- Optional: `scripts/`, `references/`, `assets/`
- Imperative/infinitive writing style
- Passes `scripts/package_skill.py` validation

**Framework-touching skills**: Read/write framework files, need $ACADEMICOPS paths
- Examples: aops-trainer, skill-creator, claude-hooks

**Non-framework skills**: General utilities
- Examples: pdf, archiver, strategic-partner

### Slash Commands

**Purpose**: User-facing shortcuts to load workflows

**Requirements**:
- YAML frontmatter with `description`
- **MANDATORY skill-first pattern**:
  ```markdown
  **MANDATORY FIRST STEP**: Invoke the `skill-name` skill IMMEDIATELY.

  After the skill loads, follow its instructions precisely.

  ARGUMENTS: $ARGUMENTS
  ```
- Keep under 50 lines (just invocation instructions)

**Anti-pattern**: Duplicating skill content inline

### Hooks

**Purpose**: Automated runtime enforcement

**Types**:
- **SessionStart**: Load 3-tier context (`load_instructions.py`)
- **PreToolUse**: Validate tool calls (`validate_tool.py`)
- **PostToolUse**: Conditional loading (`stack_instructions.py`)
- **Stop/SubagentStop**: Validate completion (`validate_stop.py`)
- **Logging**: Capture events (`log_*.py`)

**Requirements**:
- Python module with docstring (first line = description)
- Fail-fast implementation
- No defensive programming

### Chunks

**Purpose**: DRY single sources for universal concepts

**Files**:
- `AXIOMS.md` - Universal principles
- `INFRASTRUCTURE.md` - Framework structure
- `SKILL-PRIMER.md` - Skill context
- `AGENT-BEHAVIOR.md` - Conversational rules

**Requirements**:
- Referenced by `core/_CORE.md` (agents get via SessionStart)
- Symlinked to `skills/*/resources/` (skills load explicitly)
- Never duplicated elsewhere
- Integration tested (`tests/test_chunks_loading.py`)

---

## Validation & Enforcement

### Enforcement Hierarchy

Reliability (most → least):
1. **Scripts** - Automated code (most reliable)
2. **Hooks** - Runtime checks
3. **Configuration** - Permissions
4. **Instructions** - Agent directives (least reliable)

**Design principle**: If agents consistently disobey instructions, move enforcement UP the hierarchy.

### Claude Code Hooks

**SessionStart** (`load_instructions.py`):
- Loads 3-tier `_CORE.md`
- Blocks session if framework tier missing

**PreToolUse** (`validate_tool.py`):
- Blocks `.md` file creation (prevents documentation bloat)
- Requires `uv run python` for Python execution
- Blocks inline Python (`python -c`)
- Warns on git commits outside code-review agent

**SubagentStop/Stop** (`validate_stop.py`):
- Validates agent completion state

### Git Pre-Commit Hooks

- Documentation bloat prevention
- Python quality (ruff, mypy, pytest)

---

## Agent Architecture

### Two Types: Bounded Workers vs Orchestrator

**Regular Agents** (bounded workers):
- Do ONE specific thing, then STOP
- Complete task requested, nothing more
- If more work needed → ASK user
- Examples: developer, test-cleaner, trainer

**SUPERVISOR Agent** (orchestrator):
- Manages multi-step workflows
- Breaks tasks into atomic steps
- Calls specialized agents ONE AT A TIME
- Continues until entire workflow complete

**Rationale**: Prevents scope creep and recursive debugging.

### Key Agents

- **`/trainer`** - Framework maintenance (agents, hooks, configs)
- **`/dev`** - Application code implementation (TDD workflow)
- **`/STRATEGIST`** - Planning, facilitation, silent context capture
- **`supervisor`** - Orchestrates complex multi-step workflows (Task tool only)
- **`analyst`** - Academic research data analysis (dbt & Streamlit)

---

## Skills vs Subagents vs Commands

**Skills** (HOW): Technical expertise - single source of truth
- `tasks`, `email`, `pdf`, `xlsx`, `docx`, `test-writing`, `git-commit`
- Location: `~/.claude/skills/`

**Subagents** (WHAT): Workflows that invoke skills
- `strategist`, `supervisor`, `developer`, `analyst`
- Location: `agents/`

**Commands** (shortcuts): User convenience
- `/email` → strategist, `/dev` → developer
- Location: `commands/`

**Rule**: Subagents decide WHAT, skills provide HOW. Never duplicate HOW across subagents.

---

## Design Principles

### Complete Modularity (DRY)

Every concept documented exactly once, referenced everywhere else.

**Implementation**:
- `chunks/` for shared context (single source)
- `@references` for agents
- Symlinks for skills
- Validation hooks prevent duplication

### Fail-Fast Philosophy

- Agents fail immediately on errors
- Fix underlying infrastructure, don't teach workarounds
- No `.get(key, default)` - explicit configuration required

### Project Isolation

- Projects work independently
- No cross-dependencies between submodules
- Project-specific content stays in project repos

### Mandatory Skill-First Pattern

**ALL slash commands MUST**:
- Invoke corresponding skill FIRST
- Include "MANDATORY FIRST STEP" instruction
- Pass $ARGUMENTS to skill

**ALL agents MUST**:
- Invoke supporting skill FIRST
- Keep procedural details in skill, not agent

**Rationale**: Prevents improvisation, ensures consistency, enables documentation discovery

### Anti-Bloat Enforcement

Enforcement hierarchy (most → least reliable): Scripts > Hooks > Configuration > Instructions.

Component size limits enforce architecture boundaries:
- Skills: <300 lines
- Agents: <500 lines
- Changes >10 lines: Require GitHub issue approval

Process details in aops-trainer skill.

### Experiment-Driven Development

Changes to framework tested empirically with experiment logs (`experiments/YYYY-MM-DD_name.md`) rather than speculated. Test, measure, decide.

Workflow details in aops-trainer skill.

---

## See Also

- `README.md` - Quick start guide
- `INSTALL.md` - Detailed installation
- `docs/bots/BEST-PRACTICES.md` - Evidence-based component design
- `core/_CORE.md` - Core axioms (auto-loaded)
- `tests/test_chunks_loading.py` - Infrastructure verification
