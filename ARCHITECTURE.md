# academicOps Architecture

Single source of truth for the academicOps agent framework: what exists, how it works, and who is responsible.

## Core Design Philosophy

**Sleek and Minimal:** Simple, flexible architecture. Every layer has a clear purpose. No over-engineering.

**Single Instruction Loading Pathway:** All agents load `_CORE.md` from the 3-tier hierarchy at SessionStart. No project-specific slash commands. No complex discovery
mechanisms.

**Modular by Reference:** Documentation lives once, gets referenced everywhere. DRY principle strictly enforced.

## Instruction Loading System

### Automatic Loading (SessionStart Hook)

**Single Script Chain:**

1. `load_instructions.py` (SessionStart hook) → calls
2. `read_instructions.py _CORE.md` → loads 3-tier hierarchy

**3-Tier Hierarchy (Priority: Project → Personal → Bot):**

$PROJECT/agents/_CORE.md              ← Highest priority (project-specific)
$ACADEMICOPS_PERSONAL/agents/_CORE.md ← Medium priority (user global)
$ACADEMICOPS_BOT/agents/_CORE.md      ← Lowest priority (framework defaults)

**Output:**

- **To User** (stdout): Colored status line showing which levels loaded
Loaded _CORE.md: ✓ bot ✓ personal ✓ project
- **To Agent** (stderr): Full text of all 3 files for agent consumption

**Behavior:**

- **At least ONE file MUST exist** (blocks with exit code 1 if all missing)
- Files loaded in priority order (project overrides personal overrides bot)
- Missing files at any tier are silently skipped (fail-fast only if ALL missing)

### Agent-Specific Loading

When you invoke `@agent-{name}`, Claude Code loads:

1. SessionStart instructions (all 3 tiers of `_CORE.md`)
2. Agent-specific file: `${ACADEMICOPS_BOT}/agents/{NAME}.md`

**Example:** `@agent-developer` loads:

1. `_CORE.md` (all 3 tiers - core axioms + user context + project context)
2. `DEVELOPER.md` (developer-specific workflows)

### No Project-Specific Slash Commands

**Old System (removed):**

- `/mm` → MediaMarkets analysis mode
- `/bm` → Buttermilk development mode
- `/tja` → TJA analysis mode

**New System:**

- Project context auto-loads from `$PROJECT/agents/_CORE.md`
- Agent definitions remain generic (`DEVELOPER.md`, `ANALYST.md`)
- Project-specific knowledge lives in project repos, not bot framework

**Rationale:** Most projects don't need dedicated commands. Auto-loaded project context is sufficient.

## File Structure

### Bot Framework (`$ACADEMICOPS_BOT/`)

**Agent Definitions** (`agents/`):

- `_CORE.md` - Core axioms loaded for ALL agents at SessionStart
- `TRAINER.md` - Agent framework maintenance
- `STRATEGIST.md` - Planning and project management
- `DEVELOPER.md` - Code implementation
- `CODE.md` - Code review and commits (invoked as `@agent-code-review`)
- `ANALYST.md` - Data analysis workflows (dbt, SQL)

**Framework Documentation** (`docs/`):

- `hooks_guide.md` - Hook system documentation
- `methodologies/computational-research.md` - Research workflows
- `methodologies/dbt-practices.md` - Analytics engineering patterns

**Scripts** (`scripts/`):

- `load_instructions.py` - SessionStart hook (calls read_instructions.py)
- `read_instructions.py` - Reads `<filename>` from 3-tier hierarchy
- `validate_tool.py` - PreToolUse hook (enforces tool rules)
- `validate_stop.py` - SubagentStop/Stop hooks
- `setup_academicops.sh` - Setup script for new projects
- `check_instruction_orphans.py` - Validates instruction file linkage
- Other utility scripts for tasks, code review, etc.

**Configuration Templates** (`dist/`):

- `.claude/settings.json` - Template Claude Code settings
- `agents/INSTRUCTIONS.md` - Template for project `_CORE.md` files
- `.gitignore` - academicOps exclusions

**Archived Files** (`docs/_UNUSED/`):

- 32+ archived obsolete documentation files
- Not referenced in active loading paths
- Kept for historical reference only

### Personal Context (`$ACADEMICOPS_PERSONAL/`)

**User Global Preferences:**

- `agents/_CORE.md` - User's global preferences across all projects
- `agents/DEVELOPER.md` - User's development patterns (optional)
- `docs/**` - User-specific documentation (optional)
- `data/` - User's tasks, goals, projects, context (for strategist)

### Project Level (`$PROJECT/`)

**Project-Specific Context:**

- `agents/_CORE.md` - Project-specific rules and context
- `.claude/settings.json` - Project Claude Code configuration
- `.claude/commands/` - Project-specific slash commands (if truly needed)
- `.academicOps/scripts/` - Symlinked validation scripts (created by setup)

## Validation & Enforcement System

### Pre-Tool-Use Hook (`validate_tool.py`)

**Purpose:** Enforces tool usage rules before agents execute tools

**Rules Enforced:**

1. Markdown file creation restricted (prevents documentation bloat)
2. Python execution requires `uv run` prefix
3. Inline Python (`python -c`) blocked
4. Git commits warn for non-code-review agents
5. `/tmp` test files blocked (violates Axiom #5 - build for replication)

**Configuration:** Runs automatically via Claude Code's PreToolUse hook

### Pre-Commit Hooks (`.pre-commit-config.yaml`)

**Purpose:** Code quality enforcement before git commits

**Hooks:**

- `ruff-check` - Python linting with auto-fixes
- `ruff-format` - Python code formatting
- `mypy` - Static type checking
- `radon` - Complexity and maintainability metrics
- `test-architecture` - Test file location validation
- `pytest` - Fast unit tests only

**Performance:** Only runs on Python file changes (optimized for fast doc commits)

## Agent Responsibilities

### @agent-trainer

**Scope:** Agent framework infrastructure and meta-system maintenance

Responsible for:

- Agent instruction files (`agents/*.md`)
- Framework documentation (`docs/`, ARCHITECTURE.md, INSTRUCTION-INDEX.md)
- Configuration (`.claude/settings.json`, validation hooks)
- Instruction loading system (SessionStart hooks, read scripts)
- Error message UX for validation failures
- Pre-commit hook configuration

**NOT responsible for:** Project-specific work, writing application code, research tasks

### @agent-strategist

**Scope:** Planning, scheduling, project management, context capture

Responsible for:

- Task management (creating, organizing, prioritizing tasks)
- Project planning and milestone tracking
- Meeting notes and decision documentation
- Goal setting and progress reviews
- Context capture from conversations

**NOT responsible for:** Writing code, modifying agent instructions, framework changes

### @agent-developer

**Scope:** Writing, testing, and debugging application code

Responsible for:

- Implementing features in project code
- Writing tests (following TDD methodology)
- Debugging and fixing bugs
- Refactoring application code
- Running test suites

**NOT responsible for:** Agent framework changes, project planning, committing code

### @agent-code-review

**Scope:** Code review and git commit operations

Responsible for:

- Reviewing staged changes for quality
- Running pre-commit validation hooks
- Creating git commits with conventional messages
- Creating pull requests
- Enforcing code standards

**NOT responsible for:** Writing code, planning features, modifying agent instructions

### @agent-analyst

**Scope:** Data analysis workflows (dbt, SQL, data pipelines)

Responsible for:

- dbt model development and testing
- SQL query optimization
- Data pipeline debugging
- Analytics code review

**NOT responsible for:** General application development, agent framework changes

## Design Principles

### Complete Modularity (Issue #111)

**Every concept documented exactly once, referenced everywhere else.**

- ONE canonical source per concept
- Agent files reference, never duplicate
- Predictable file locations for discovery
- Validation hooks prevent duplication

**Reference Pattern:**

```markdown
# Agent Instructions

Load methodologies:
- @bot/docs/methodologies/dbt-practices.md
- @docs/agents/INSTRUCTIONS.md (if exists)

Enforcement Hierarchy

Reliability Order (most → least):
1. Scripts - Code that prevents bad behavior
2. Hooks - Automated checks at key moments
3. Configuration - Permissions and restrictions
4. Instructions - Last resort (agents forget in long conversations)

Principle: If agents consistently disobey instructions, move enforcement UP the hierarchy.

Fail-Fast Philosophy

- Agents should fail immediately on errors
- Fix underlying infrastructure, don't teach workarounds
- Reliable systems > defensive programming instructions

Setup Process

Installing academicOps in a New Project

Run setup script:
cd $PROJECT
$ACADEMICOPS_BOT/scripts/setup_academicops.sh

What it creates:
1. .claude/settings.json (copied from dist/.claude/settings.json)
2. .claude/agents/ (symlinked to academicOps agents)
3. agents/_CORE.md (template for project context)
4. .academicOps/scripts/ (symlinked validation scripts)
5. .gitignore updates (excludes academicOps managed files)

What it verifies:
- ACADEMICOPS_BOT environment variable set and directory exists
- ACADEMICOPS_PERSONAL environment variable (optional)
- load_instructions.py exists and is executable

Environment Variables Required

export ACADEMICOPS_BOT=/path/to/academicOps      # Required
export ACADEMICOPS_PERSONAL=/path/to/writing     # Optional
