# academicOps Architecture

System design and implementation for the academicOps agent framework.

---

## Core Concepts

### Modular Chunks Architecture (NEW)

**Problem**: Skills don't receive SessionStart hooks, lacking framework context (paths, axioms, env vars).

**Solution**: Modular `chunks/` directory with DRY symlinks.

```
chunks/                        # Single source of truth
├── AXIOMS.md (97 lines)       # Universal principles (fail-fast, DRY, etc.)
├── INFRASTRUCTURE.md (52)     # Framework paths, $ACADEMICOPS, repo structure
├── AGENT-BEHAVIOR.md (26)     # Conversational/agent-specific rules
└── SKILL-PRIMER.md (19)       # Skill execution context

core/_CORE.md (19 lines)       # @references chunks/ for agents
skills/*/resources/            # Symlinks to chunks/ for skills
```

**How it works**:
1. **Agents**: SessionStart loads `_CORE.md` → @references load chunks/
2. **Skills**: `@resources/AXIOMS.md` loads via symlink → `../../chunks/AXIOMS.md`
3. **DRY**: Each principle exists in EXACTLY ONE chunk file
4. **Selective loading**: Framework skills get INFRASTRUCTURE.md, others don't

**Verified**: Live integration tests (`tests/test_chunks_loading.py`) prove infrastructure works.

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

**Recommended deployment** (framework as submodule):

```bash
# In ~/.zshrc
export ACADEMICOPS="$HOME/src/writing/aops"              # Framework (submodule)
export ACADEMICOPS_PERSONAL="$HOME/src/writing/bots"     # Personal overrides
```

**Alternative deployment** (framework standalone):

```bash
export ACADEMICOPS=/path/to/academicOps          # Framework repo
export ACADEMICOPS_PERSONAL=/path/to/personal    # Personal overrides
```

Available to all agents and skills. Used for:
- Path resolution (`$ACADEMICOPS/commands/trainer.md`)
- Three-tier loading (framework → personal → project)
- Hook invocation

**Submodule benefits**:
- Single Basic Memory project indexes framework + personal content
- WikiLinks work across repos: `[[aops/concepts/fail-fast]]`
- Unified search
- Framework versioned with personal repo

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

```
$ACADEMICOPS/
├── chunks/                # Shared context modules (DRY single sources)
├── core/
│   └── _CORE.md          # References chunks/ (19 lines, down from 113)
├── agents/                # Subagent definitions
├── commands/              # Slash command definitions
├── hooks/                 # SessionStart, PreToolUse, Stop hooks
├── scripts/               # Automation tools
├── skills/                # Packaged skill sources
│   └── */resources/      # Symlinks to chunks/
├── docs/                  # Human documentation
│   └── bots/             # Framework dev context (loaded at SessionStart)
└── tests/                 # Integration tests
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

### Experiment-Driven Development

**ALL changes require**:
1. GitHub issue (search first - 3+ searches)
2. Experiment log: `experiments/YYYY-MM-DD_name.md`
3. Hypothesis, success criteria, changes
4. Testing with real scenarios
5. Results documentation
6. Decision: Keep/Revert/Iterate

**No speculation**. Test, measure, decide.

---

## Testing

```bash
# Run all tests
uv run pytest

# Test chunks infrastructure (verifies symlinks, @references, env vars)
uv run pytest tests/test_chunks_loading.py -v
```

**Integration tests** (`tests/test_chunks_loading.py`):
- Run Claude Code in headless mode (real API calls, no mocks)
- Verify chunks content appears in agent memory
- Test SessionStart loading, skill symlinks, environment variables
- All 4 tests passing ✅

---

## Installation

See `INSTALL.md` for detailed setup.

**Quick setup**:
```bash
export ACADEMICOPS=/path/to/academicOps
$ACADEMICOPS/scripts/setup_academicops.sh
```

---

## See Also

- `README.md` - Quick start guide
- `INSTALL.md` - Detailed installation
- `docs/bots/BEST-PRACTICES.md` - Evidence-based component design
- `core/_CORE.md` - Core axioms (auto-loaded)
- `tests/test_chunks_loading.py` - Infrastructure verification
