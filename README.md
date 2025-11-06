# academicOps Agent Framework

**Modular, hierarchical agent framework for rigorous, context-aware automation in academic research projects.**

**Status**: PUBLIC repository, used as git submodule in personal/project repositories.

---

## Purpose

academicOps provides infrastructure for AI agent workflows that require:

- **Fail-fast philosophy** - No fallbacks, no defensive programming, infrastructure that works
- **DRY compliance** - Single source of truth via modular chunks and symlinks
- **Anti-bloat enforcement** - Hard limits on file sizes, architectural solutions over instructions
- **Experiment-driven development** - All changes tested and measured
- **Three-tier loading** - Framework → personal → project instruction hierarchy

**This README defines the desired state.** See `docs/AUDIT.md` for current compliance status.

---

## Core Principles (Invariants)

### 1. Fail-Fast Philosophy

**Scripts/hooks/config > instructions** (reliability hierarchy)

- Infrastructure works perfectly, or fails immediately
- No defensive programming, no error recovery, no workarounds
- Agents stop on errors, trainers fix root causes

**Source**: `chunks/AXIOMS.md` Axiom #7

### 2. DRY (Don't Repeat Yourself)

**One canonical source per concept**

- If content appears in >1 place → BUG
- Reference via @notation or symlinks
- Default: DELETE documentation rather than add

**Enforcement**: Modular `chunks/` + `resources/` symlinks

### 3. Anti-Bloat by Design

**Hard limits enforced**:

- Skills: SKILL.md <300 lines
- Agents: Instructions <500 lines
- Adding >10 lines requires GitHub issue + approval

**Before adding >5 lines, verify**:
- No architectural solution (scripts/hooks/config)?
- No existing content to reference?
- Not repeating chunks/ or BEST-PRACTICES.md?
- Bullet points, not prose?
- Specific instructions, not vague?

**Source**: `skills/skill-creator/SKILL.md`, `docs/bots/BEST-PRACTICES.md`

### 4. Experiment-Driven Development

**We don't know until we test**

- Every change requires experiment log (`experiments/YYYY-MM-DD_name.md`)
- Single variable per experiment
- Explicit success criteria
- Document outcomes: Success/Failure/Partial
- Keep/revert/iterate based on measurements

**No speculation**. Test, measure, decide.

### 5. Modular Architecture

**Chunks system**:

```
chunks/FILE.md (single source)
    ↓ @reference from core/_CORE.md (agents via SessionStart)
    ↓ symlink to skills/*/resources/FILE.md (skills load explicitly)
```

**Benefits**:
- Skills get framework context without SessionStart hooks
- Zero duplication
- Live integration tests verify infrastructure

**Source**: `ARCHITECTURE.md`, `tests/test_chunks_loading.py`

### 6. Knowledge Organization (bmem)

**Vector search + relational mapping for documentation and tasks**

**basic-memory** (internal ref: `bmem`) provides:
- Just-in-time concept loading via vector search (<2s)
- Relational mapping between concepts
- Task management with markdown + YAML frontmatter
- Cross-repository context building

**Integration**:
- MCP server: `mcp__basic-memory__*` tools
- Projects: `aops` ($ACADEMICOPS), `ns` ($ACADEMICOPS_PERSONAL)
- Storage: Markdown files + SQLite graph
- Access pattern: Search → load relevant concepts only

**Benefits**:
- Reduced SessionStart token cost (load on-demand vs load-all)
- Documentation discoverability via vector search
- Learning loops (agents update concepts from experiment outcomes)
- Unified knowledge graph across framework + personal repos

**Status**: Integration in progress (Issue #193)

**Source**: `chunks/INFRASTRUCTURE.md`, Issue #193

---

## Repository Structure (Specification)

```
$ACADEMICOPS/                  # This repository (PUBLIC framework)
├── chunks/                    # Shared context modules (DRY single sources)
│   ├── AXIOMS.md             # Universal principles (97 lines)
│   ├── INFRASTRUCTURE.md     # Framework paths, env vars (52 lines)
│   ├── AGENT-BEHAVIOR.md     # Conversational rules (26 lines)
│   └── SKILL-PRIMER.md       # Skill execution context (19 lines)
│
├── core/                      # Auto-loaded at SessionStart
│   ├── _CORE.md              # References chunks/
│   ├── DEVELOPMENT.md        # Development standards
│   ├── TESTING.md            # Testing requirements
│   ├── DEBUGGING.md          # Debugging workflow
│   └── STYLE.md              # Writing style guide
│
├── agents/                    # Subagent definitions (<500 lines each)
│   ├── ANALYST.md
│   ├── DEVELOPER.md
│   ├── STRATEGIST.md
│   ├── SUPERVISOR.md
│   ├── scribe.md
│   ├── task-manager.md
│   └── end-of-session.md
│
├── commands/                  # Slash command definitions
│   ├── analyst.md            # /analyst
│   ├── dev.md                # /dev
│   ├── email.md              # /email
│   ├── error.md              # /error
│   ├── log-failure.md        # /log-failure
│   ├── ops.md                # /ops
│   ├── STRATEGIST.md         # /STRATEGIST
│   └── trainer.md            # /trainer
│
├── hooks/                     # Runtime behavior enforcement
│   ├── load_instructions.py      # SessionStart: Load 3-tier context
│   ├── validate_tool.py          # PreToolUse: Check permissions
│   ├── validate_stop.py          # Stop: Validate completion
│   ├── stack_instructions.py     # PostToolUse: Conditional loading
│   └── log_*.py, autocommit_tasks.py, request_scribe_stop.py
│
├── skills/                    # Packaged skills (installed to ~/.claude/skills/)
│   ├── [skill-name]/
│   │   ├── SKILL.md          # <300 lines, YAML frontmatter
│   │   ├── resources/        # MANDATORY symlinks
│   │   │   ├── SKILL-PRIMER.md → ../../chunks/SKILL-PRIMER.md
│   │   │   ├── AXIOMS.md → ../../chunks/AXIOMS.md
│   │   │   └── INFRASTRUCTURE.md → ../../chunks/INFRASTRUCTURE.md  # Framework-touching only
│   │   ├── scripts/          # Executable code (Python/Bash)
│   │   ├── references/       # Documentation (loaded as needed)
│   │   └── assets/           # Output files (templates, boilerplate)
│   │
│   ├── Framework skills (8):
│   │   agent-initialization, aops-bug, aops-trainer,
│   │   claude-hooks, claude-md-maintenance, skill-creator,
│   │   skill-maintenance, document-skills
│   │
│   ├── Development skills (4):
│   │   git-commit, github-issue, test-writing, no-throwaway-code
│   │
│   └── Utility skills (8):
│       analyst, archiver, email, pdf, scribe,
│       strategic-partner, tasks, tja-research
│
├── docs/                      # Framework documentation
│   ├── bots/                 # Agent development context
│   │   ├── BEST-PRACTICES.md      # Evidence-based guidance
│   │   ├── skills-inventory.md    # Skill catalog
│   │   ├── skill-invocation-guide.md
│   │   ├── delegation-architecture.md
│   │   └── INDEX.md
│   │
│   ├── _CHUNKS/              # Domain-specific documentation
│   │   ├── HYDRA.md, PYTHON-DEV.md, DBT.md
│   │   ├── SEABORN.md, STATSMODELS.md, STREAMLIT.md
│   │   └── E2E-TESTING.md, FAIL-FAST.md, GIT-WORKFLOW.md
│   │
│   ├── methodologies/
│   ├── _UNUSED/              # Archived legacy docs
│   ├── AUDIT.md              # Current state vs desired state
│   ├── INSTRUCTION-INDEX.md  # Complete file registry
│   ├── TESTING.md, DEPLOYMENT.md, hooks_guide.md
│   └── CLAUDE_MD_GUIDE.md
│
├── experiments/               # Experiment logs (YYYY-MM-DD_name.md)
├── scripts/                   # Automation tools
│   ├── generate_instruction_tree.py
│   ├── validate_instruction_tree.py
│   └── setup_academicops.sh
│
├── tests/                     # Integration & unit tests
│   └── test_chunks_loading.py
│
├── config/                    # Client configurations
│   ├── mcp.json
│   └── settings.json
│
├── ARCHITECTURE.md            # System design documentation
├── CLAUDE.md                  # Project instructions (auto-loaded)
├── LICENSE                    # Apache 2.0
└── README.md                  # This file (authoritative specification)
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
- `AXIOMS.md` - Universal principles (97 lines)
- `INFRASTRUCTURE.md` - Framework structure (52 lines)
- `SKILL-PRIMER.md` - Skill context (19 lines)
- `AGENT-BEHAVIOR.md` - Conversational rules (26 lines)

**Requirements**:
- Referenced by `core/_CORE.md` (agents get via SessionStart)
- Symlinked to `skills/*/resources/` (skills load explicitly)
- Never duplicated elsewhere
- Integration tested (`tests/test_chunks_loading.py`)

---

## Architectural Patterns (Standards)

### 1. resources/ Symlinks (Universal)

**ALL skills MUST include**:

```bash
skills/skill-name/
├── SKILL.md
└── resources/
    ├── SKILL-PRIMER.md → ../../chunks/SKILL-PRIMER.md
    ├── AXIOMS.md → ../../chunks/AXIOMS.md
    └── INFRASTRUCTURE.md → ../../chunks/INFRASTRUCTURE.md  # If framework-touching
```

**In SKILL.md header**:
```markdown
## Framework Context
@resources/SKILL-PRIMER.md
@resources/AXIOMS.md
@resources/INFRASTRUCTURE.md  # If framework-touching
```

### 2. Mandatory Skill-First Pattern

**ALL slash commands MUST**:
- Invoke corresponding skill FIRST
- Include "MANDATORY FIRST STEP" instruction
- Pass $ARGUMENTS to skill

**ALL agents MUST**:
- Invoke supporting skill FIRST
- Keep procedural details in skill, not agent

**Rationale**: Prevents improvisation, ensures consistency, enables documentation discovery

### 3. Anti-Bloat Enforcement

**Pre-addition checklist** (before adding >5 lines):
- [ ] Tried scripts/hooks/config first?
- [ ] Checked existing content to reference?
- [ ] Verified not repeating chunks/ or _CORE.md?
- [ ] Using bullet points, not prose?
- [ ] Instructions specific, not vague?
- [ ] File stays under limits?

**Hard limits**:
- Skills: <300 lines
- Agents: <500 lines
- Adding >10 lines: GitHub issue + approval required

**CI enforcement** (to be implemented):
- Pre-commit hook checks line counts
- Blocks commits exceeding limits

### 4. Experiment-Driven Changes

**ALL changes require**:

1. GitHub issue (search first - 3+ searches)
2. Experiment log: `experiments/YYYY-MM-DD_name.md`
3. Hypothesis, success criteria, changes
4. Testing with real scenarios
5. Results documentation
6. Decision: Keep/Revert/Iterate

**Template**:
```markdown
## Metadata
- Date, Issue, Commit, Model

## Hypothesis
[What we expect]

## Changes Made
[Specific modifications]

## Success Criteria
[How to measure]

## Results
[What actually happened]

## Outcome
[Success/Failure/Partial]
```

### 5. Three-Tier Instruction Loading

**SessionStart hook loads**:

```
Framework tier    ($ACADEMICOPS/core/_CORE.md, docs/bots/INDEX.md)
    ↓
Personal tier     ($OUTER/docs/agents/*.md)
    ↓
Project tier      (./docs/agents/*.md)
```

Each tier can override or extend previous tier.

---

## Installation & Setup

### Environment Variable

```bash
# Add to shell profile (~/.bashrc, ~/.zshrc)
export ACADEMICOPS=/path/to/academicOps
```

### As Submodule

```bash
# In your personal/project repository
git submodule add https://github.com/nicsuzor/academicOps.git aops
git submodule update --init --recursive

# Set environment variable
export ACADEMICOPS=/path/to/your-repo/aops
```

### Skills Installation

```bash
# Package and install skills
cd $ACADEMICOPS/skills/skill-name
uv run python scripts/package_skill.py .

# Install to Claude Code
cp skill-name.zip ~/.claude/skills/
cd ~/.claude/skills && unzip skill-name.zip
```

---

## Validation & Testing

### Pre-Commit Checks

```bash
# Validation
python scripts/validate_instruction_tree.py

# Regenerate instruction tree (if stale)
python scripts/generate_instruction_tree.py
```

### Integration Tests

```bash
# Run all tests
uv run pytest

# Test chunks infrastructure
uv run pytest tests/test_chunks_loading.py -v

# Test skill validation
uv run python skills/skill-creator/scripts/package_skill.py skills/skill-name
```

### Anti-Bloat Validation

```bash
# Check file sizes
wc -l agents/*.md
wc -l skills/*/SKILL.md

# Verify resources/ compliance
find skills/ -type d -name "resources" | wc -l  # Should equal skill count
```

---

## Usage Patterns

### Invoking Agents

```bash
# Via Task tool (from another agent)
Task(subagent_type="general-purpose", prompt="...", description="...")

# Via slash command (user-facing)
/trainer
/dev
/analyst
```

### Invoking Skills

```bash
# Explicit invocation
Skill(command="skill-name")

# Automatic invocation (via agents/commands)
# Slash command → Loads skill → Agent follows skill instructions
```

### Creating New Components

**New skill**:
1. `cd $ACADEMICOPS/skills && python skill-creator/scripts/init_skill.py skill-name --path .`
2. Add `resources/` symlinks (SKILL-PRIMER, AXIOMS, INFRASTRUCTURE if framework-touching)
3. Edit SKILL.md (follow anti-bloat checklist)
4. Validate: `python skill-creator/scripts/package_skill.py skill-name`
5. Create experiment log
6. Commit via git-commit skill

**New agent**:
1. Create `agents/AGENT-NAME.md` with YAML frontmatter
2. Keep <500 lines
3. Reference skills, don't duplicate workflows
4. Include MANDATORY skill-first step
5. Regenerate instruction tree
6. Create experiment log
7. Commit via git-commit skill

**New slash command**:
1. Create `commands/command-name.md` with YAML frontmatter
2. Include MANDATORY skill-first pattern
3. Keep under 50 lines
4. Regenerate instruction tree
5. Commit via git-commit skill

---

## Compliance Monitoring

**Auditing frequency**: After structural changes or quarterly

**Audit process**:
1. Run validation scripts
2. Check file sizes against limits
3. Verify resources/ symlinks (all skills)
4. Confirm skill-first patterns (all commands/agents)
5. Update `docs/AUDIT.md` with findings
6. Create GitHub issues for violations
7. Apply modular references pattern to bloated files

**See**: `docs/AUDIT.md` for current compliance status

---

## Contributing

**All changes follow**:

1. Search GitHub issues (3+ searches)
2. Document in issue (diagnostics + solution design)
3. Create experiment log
4. Implement (max 3 changes, <10 lines each)
5. Test with real scenarios
6. Update experiment log with results
7. Commit via git-commit skill
8. Update audit if structural change

**See**: `skills/aops-trainer/SKILL.md` for complete workflow

---

## Key References

- **Core axioms**: `chunks/AXIOMS.md`, `core/_CORE.md`
- **Best practices**: `docs/bots/BEST-PRACTICES.md` (evidence-based guidance)
- **Architecture**: `ARCHITECTURE.md`
- **Testing**: `docs/TESTING.md`, `tests/`
- **Current state**: `docs/AUDIT.md`
- **Skill creation**: `skills/skill-creator/SKILL.md`
- **Agent optimization**: `skills/aops-trainer/SKILL.md`

---

## Quick Start

```bash
# Set environment
export ACADEMICOPS=/path/to/academicOps

# Validate structure
python scripts/validate_instruction_tree.py

# Run tests
uv run pytest

# Launch Claude Code
claude
```

**First time**: SessionStart hook auto-loads `core/_CORE.md`. Slash commands are ready to use.

---

## License

Apache 2.0 - See LICENSE file

---

**This README is the authoritative specification.** The repository should always align with this document. See `docs/AUDIT.md` for current compliance status and `experiments/` for change history.

**Last updated**: 2025-11-06
