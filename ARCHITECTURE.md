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

```bash
export ACADEMICOPS=/path/to/academicOps          # Required
export ACADEMICOPS_PERSONAL=/path/to/personal    # Optional
```

Available to all agents and skills. Used for:
- Path resolution (`$ACADEMICOPS/commands/trainer.md`)
- Three-tier loading (framework → personal → project)
- Hook invocation

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
