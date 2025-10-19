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

academicOps uses a **multi-layered enforcement hierarchy** to ensure quality and consistency:

### 1. Claude Code Hooks (Runtime Validation)

Configured in `.claude/settings.json`, these hooks run during Claude Code sessions.

#### SessionStart Hook (`load_instructions.py`)

**Purpose:** Loads hierarchical instructions at every session start

**Process:**

1. Calls `read_instructions.py _CORE.md`
2. Loads from 3-tier hierarchy (bot → personal → project)
3. Returns context to agent via stderr
4. Shows user-friendly status via stdout

**Output to user:**
```
Loaded _CORE.md: ✓ bot ✓ personal ✓ project
```

**Fail-fast:** Blocks session if ALL three tiers are missing

#### PreToolUse Hook (`validate_tool.py`)

**Purpose:** Validates every tool call before execution

**Rules Enforced:**

1. **Markdown file creation restricted** (prevents documentation bloat)
   - Blocks: `Write(**/*.md)`, except research papers
   - Enforces: Self-documenting code principle
2. **Python execution requires `uv run` prefix**
   - Blocks: `python script.py`, `python3 script.py`
   - Allows: `uv run python script.py`
3. **Inline Python blocked**
   - Blocks: `python -c "code"`
   - Reason: Non-reproducible, untestable
4. **Git commits restricted to code-review agent**
   - Warns: Non-review agents attempting commits
   - Enforces: Quality gate separation
5. **Temporary test files blocked**
   - Blocks: Files in `/tmp`
   - Enforces: Axiom #5 (build for replication)

**Exit Codes:**
- `0` - Allow (with optional prompt)
- `1` - Warn (allow with warning message)
- `2` - Block (show error to agent)

#### SubagentStop/Stop Hooks (`validate_stop.py`)

**Purpose:** Validates agent completion state

**Configuration:**
```json
{
  "hooks": {
    "SubagentStop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run python scripts/validate_stop.py SubagentStop"
      }]
    }]
  }
}
```

### 2. Git Pre-Commit Hooks (Commit-Time Quality)

Installed via `scripts/git-hooks/install-hooks.sh`, enforced before every git commit.

#### Documentation Bloat Prevention (`pre-commit`)

**Purpose:** Prevents proliferation of `.md` documentation files

**What it blocks:**
- New `.md` files anywhere (except allowed paths)
- README.md, HOWTO.md, GUIDE.md files
- System documentation files

**What it allows:**
- Research papers (`papers/`, `manuscripts/`)
- Agent instructions (`agents/*.md` - these ARE executable code)
- Explicitly confirmed deliverables

**Enforcement:**
1. Detects all new `.md` files being added (status A)
2. Filters out allowed paths
3. Prompts user for confirmation if forbidden files found
4. Blocks commit unless user confirms files are allowed content types

**User experience:**
```
🛑 WARNING: New .md file(s) detected that may violate documentation philosophy:

  - scripts/setup/README.md

Documentation Philosophy:
  ✅ ALLOWED: Research papers, manuscripts, agent instructions
  ❌ FORBIDDEN: README.md, HOWTO.md, GUIDE.md, system documentation

Instead of creating documentation files, use:
  • Scripts with --help output and comprehensive inline comments
  • Issue templates with complete instructions
  • Code comments for design decisions

Are you CERTAIN these are allowed content types? (y/N)
```

**Installation:**
```bash
$ACADEMICOPS_BOT/scripts/git-hooks/install-hooks.sh
```

Options:
- Default: Backs up existing pre-commit hook
- `--force`: Overwrites without backup
- `--help`: Shows usage information

#### Python Code Quality (`.pre-commit-config.yaml`)

**Purpose:** Automated code quality checks for Python files

**Hooks:**

- `ruff-check` - Python linting with auto-fixes
- `ruff-format` - Code formatting (Black-compatible)
- `mypy` - Static type checking
- `radon` - Complexity and maintainability metrics
- `test-architecture` - Validates test file locations
- `pytest` - Runs fast unit tests only

**Performance optimization:** Only runs on Python file changes (`.py` files)

**Installation:**
```bash
cd $ACADEMICOPS_BOT
uv run pre-commit install
```

### 3. Permission System (Configuration-Level)

Fine-grained tool access control in `.claude/settings.json`.

**Allow List:**
```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)",
      "mcp__gh__create_issue"
    ]
  }
}
```

**Deny List:**
```json
{
  "permissions": {
    "deny": [
      "Write(**/*.md)",
      "Write(**/*.env*)",
      "Read(**/*.cache/**)",
      "Write(./**/.venv/**)"
    ]
  }
}
```

### Enforcement Hierarchy

**Reliability Order (most → least reliable):**

1. **Scripts** - Code that prevents bad behavior (hooks, validation)
2. **Hooks** - Automated checks at key moments (SessionStart, PreToolUse)
3. **Configuration** - Permissions and restrictions (settings.json)
4. **Instructions** - Agent directives (last resort - agents forget in long conversations)

**Principle:** If agents consistently disobey instructions, move enforcement UP the hierarchy.

**Example:** If agents keep creating README.md files despite instructions:
1. ❌ Instruction: "Don't create README files" (ignored)
2. ⚠️ Configuration: `deny: ["Write(**/*.md)"]` (can be overridden)
3. ✅ PreToolUse Hook: Blocks Write tool for `.md` files (enforced)
4. ✅ Git Hook: Blocks commit if `.md` files added (enforced)

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

## Setup Process

### Installing academicOps in a New Project

**Prerequisites:**
```bash
export ACADEMICOPS_BOT=/path/to/academicOps      # Required
export ACADEMICOPS_PERSONAL=/path/to/writing     # Optional
```

**Run setup script:**
```bash
cd $PROJECT
$ACADEMICOPS_BOT/scripts/setup_academicops.sh
```

**What it creates:**

1. `.claude/settings.json` - Claude Code configuration with hooks
2. `.claude/agents/` - Symlinked to academicOps agents
3. `agents/_CORE.md` - Template for project-specific context
4. `.academicOps/scripts/` - Symlinked validation scripts
5. `.git/hooks/pre-commit` - Documentation quality enforcement
6. `.gitignore` updates - Excludes academicOps managed files

**What it verifies:**

- `ACADEMICOPS_BOT` environment variable set and directory exists
- `ACADEMICOPS_PERSONAL` environment variable (optional)
- `load_instructions.py` exists and is executable
- Git repository exists (for hook installation)

**Output:**
```
=== academicOps Setup for Third-Party Repository ===

Setting up: /path/to/project

Checking environment variables...
✓ ACADEMICOPS_BOT=/path/to/academicOps
✓ ACADEMICOPS_PERSONAL=/path/to/writing

Setting up Claude Code configuration...
✓ Created .claude
✓ Copied settings.json from dist/ template
✓ Symlinked agents from academicOps

Setting up .academicOps deployment directory...
✓ Created .academicOps/scripts
✓ Symlinked validate_tool.py
✓ Symlinked validate_stop.py
✓ Symlinked hook_models.py
✓ Symlinked load_instructions.py

Installing git pre-commit hooks...
✓ Pre-commit hook installed

Testing configuration...
✓ load_instructions.py executes successfully

=== Setup Complete ===
```

See `INSTALL.md` for detailed installation instructions.
