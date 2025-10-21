# academicOps Architecture

**Human-readable documentation of system design and current implementation.**

This document explains how academicOps works, what design decisions have been made, and what's still evolving. Written for developers, contributors, and users who want to understand the system.

---

## Philosophy: Designing for Evolution

academicOps is experimental infrastructure. The design evolves based on real-world usage and user feedback.

**Documentation principles:**
- Describes current state, not aspirational goals
- Design decisions inferred from working implementations
- Tensions and evolving preferences tracked explicitly in "Open Questions" section
- When documentation diverges from reality, reality wins—update docs to match

**File organization:**
- `agents/*.md` - Agent instructions (rules agents must follow)
- `docs/*.md`, `*.md` (root) - Human documentation (explanations of how system works)
- Agent rules use imperative voice ("You MUST..."), documentation uses descriptive voice ("The system does...")

---

## Core Concepts

### Agent Instructions vs Documentation

**Critical distinction maintained throughout academicOps:**

**`agents/` directory = Agent Instructions (executable rules)**
- Files loaded by agents at runtime
- Written in imperative voice for AI consumption
- Contains MUST/NEVER/ALWAYS rules
- Example: `agents/_CORE.md` with fail-fast axioms
- Example: `agents/TRAINER.md` with trainer agent instructions

**`docs/` directory = Human Documentation (explanatory)**
- Files for humans to read and understand the system
- Written in descriptive/explanatory voice
- Explains design decisions, usage, architecture
- Example: `docs/hooks_guide.md` explaining how hooks work
- Example: `ARCHITECTURE.md` (this file)

This separation prevents confusion between "what agents must do" and "what humans need to know."

### Namespace Rule

All projects using academicOps follow this structure:

```
any-repo/
├── agents/              # Agent instruction files (rules)
│   └── _CORE.md        # Core axioms loaded at SessionStart
├── docs/               # Human documentation (explanations)
│   └── (user's docs)
├── bots/               # academicOps installation (NEW standard)
│   ├── .academicOps/  # Symlink to framework
│   ├── agents/        # Repo-local agent overrides
│   ├── docs/          # Repo-local agent instructions
│   └── commands/      # Repo-local slash commands
└── .claude/
    ├── agents -> bots/.academicOps/.claude/agents
    └── settings.json
```

**Rule enforced in agent instructions**: Never put agent rules in `docs/`, never put human documentation in `agents/`.

---

## Instruction Loading System

### How Agents Get Their Instructions

At session start and when agents are invoked, academicOps loads instructions from multiple locations in a hierarchical order.

### SessionStart: Three-Tier Hierarchy

Every session loads `_CORE.md` from up to three tiers:

```
$ACADEMICOPS_BOT/bots/agents/_CORE.md              (Framework - REQUIRED)
$ACADEMICOPS_PERSONAL/bots/agents/_CORE.md         (Personal - optional)
$PWD/bots/agents/_CORE.md                          (Project - optional)
```

**All use `bots/agents/` directory** - consistent across all tiers.

**Loading behavior:**
- At least one file must exist (exits with error if all missing)
- Missing tiers silently skipped
- All loaded tiers visible to agent simultaneously
- Priority determines which guidance takes precedence in conflicts

**Content organization by tier:**

**Framework tier** (`$ACADEMICOPS_BOT/bots/agents/_CORE.md`):
- Generic work axioms (DO ONE THING, ANSWER DIRECTLY, fail-fast, DRY, verify first)
- Repository structure overview
- Tool requirements

**Personal tier** (`$ACADEMICOPS_PERSONAL/bots/agents/_CORE.md`):
- User's global preferences/overrides across all repos
- Work style, ADHD accommodations, communication preferences
- Tool preferences
- Workflow customizations

**Project tier** (`$PWD/bots/agents/_CORE.md`):
- Project-specific overrides to core axioms
- Domain-specific rules
- Local conventions

### Agent-Specific Instructions

When user invokes `/dev` or other slash commands, same 3-tier pattern applies:

```
$ACADEMICOPS_BOT/bots/agents/DEVELOPER.md          (Framework - REQUIRED)
$ACADEMICOPS_PERSONAL/bots/agents/DEVELOPER.md     (Personal - optional)
$PWD/bots/agents/DEVELOPER.md                      (Project - optional)
```

**Example: Running `/dev` in buttermilk repo loads:**

1. `$ACADEMICOPS_BOT/bots/agents/DEVELOPER.md` (6-step dev workflow)
2. `$ACADEMICOPS_PERSONAL/bots/agents/DEVELOPER.md` (user's dev preferences, if exists)
3. `buttermilk/bots/agents/DEVELOPER.md` (buttermilk-specific dev rules, if exists)

**Priority in conflicts**: Project > Personal > Framework

### Path Reference

**All paths use `.academicOps/` relative symlink:**

**Hooks** (in `settings.json`):
```json
"command": "uv run python .academicOps/scripts/load_instructions.py"
```

**Slash commands** (in `.claude/commands/*.md`):
```bash
uv run python .academicOps/scripts/load_instructions.py DEVELOPER.md
```

**Why consistent**: Commands get symlinked into target repos, so both hooks and commands run with `.academicOps/` available.

---

## File Structure

### Framework Repository (`$ACADEMICOPS_BOT`)

The academicOps framework itself organized as:

**Agent instructions** (`agents/`):
- `_CORE.md` - Core axioms for all agents
- `TRAINER.md` - Framework maintenance instructions
- `STRATEGIST.md` - Planning and task management
- `DEVELOPER.md` - Code implementation
- `REVIEW.md` - Code review and git operations
- `SUPERVISOR.md` - Multi-step workflow orchestration
- `TEST-CLEANER.md` - Test simplification and cleanup

**Automation scripts** (`scripts/`):
- `load_instructions.py` - SessionStart hook (loads 3-tier hierarchy)
- `read_instructions.py` - Generic hierarchical file loader
- `validate_tool.py` - PreToolUse hook (enforces tool usage rules)
- `validate_stop.py` - Stop hooks
- `install_bot.sh` - One-command installation for new repos
- `setup_academicops.sh` - Legacy installation script

**Configuration templates** (`dist/`):
- `.claude/settings.json` - Template Claude Code configuration
- `bots/docs/INSTRUCTIONS.md` - Template for project instructions
- `bots/agents/EXAMPLE.md` - Agent override example
- `.gitignore` - Standard exclusions

**Human documentation** (`docs/`):
- `hooks_guide.md` - Explains hook system
- `TESTING.md` - Test writing guidance
- `INSTRUCTION-INDEX.md` - Index of all instruction files
- `methodologies/` - Workflow explanations (dbt, computational research)

**Top-level documentation** (root):
- `README.md` - Quick start for users
- `ARCHITECTURE.md` - This file (system design explanation)
- `INSTALL.md` - Installation instructions

**Archived content** (`docs/_UNUSED/`):
- 30+ obsolete documentation files
- Kept for historical reference
- Not referenced in active system

### Installation Standard: `/bots/` Directory

New standard for academicOps installation in target repositories:

```
target-repo/
├── bots/
│   ├── .academicOps/              # Symlink to $ACADEMICOPS_BOT
│   ├── docs/INSTRUCTIONS.md       # Project-specific agent instructions
│   ├── agents/*.md                # Repo-local agent overrides (optional)
│   ├── commands/*.sh              # Repo-local slash commands (optional)
│   └── scripts/*.py               # Repo-local automation (optional)
├── .claude/
│   ├── agents -> bots/.academicOps/.claude/agents
│   ├── commands -> bots/.academicOps/.claude/commands
│   └── settings.json              # Project configuration
├── agents/                        # Legacy location
│   └── _CORE.md                  # Project instructions (being migrated)
└── docs/                          # User's existing documentation
    └── (never touched by academicOps)
```

**Design rationale:**
- All academicOps files in `/bots/` namespace - no conflicts with user directories
- Clear visual separation: `bots/.academicOps/` (symlink, never edit) vs `bots/docs/`, `bots/agents/` (repo-local, edit freely)
- Legacy paths still supported during migration

**Migration status:**
- New standard defined and tested on reference implementation
- Installation script available (`scripts/install_bot.sh`)
- Legacy fallback paths active during transition
- Deprecation timeline not yet set

---

## Validation & Enforcement

academicOps uses multiple enforcement layers to ensure code quality and maintain design principles.

### Enforcement Hierarchy

Reliability from most to least reliable:

1. **Scripts** - Code that prevents bad behavior (most reliable)
2. **Hooks** - Automated checks at key moments
3. **Configuration** - Permissions and restrictions
4. **Instructions** - Agent directives (least reliable, agents forget in long conversations)

**Design principle**: If agents consistently disobey instructions, the solution is to move enforcement up the hierarchy (towards scripts/hooks), not to add more detailed instructions.

### Claude Code Hooks

Configured in `.claude/settings.json`, these run during Claude Code sessions.

**SessionStart** (`load_instructions.py`):
- Loads 3-tier instruction hierarchy
- Blocks session if all tiers missing
- Shows user confirmation: `Loaded _CORE.md: ✓ bot ✓ personal ✓ project`

**PreToolUse** (`validate_tool.py`):
- Validates every tool call before execution
- Blocks markdown file creation (prevents documentation bloat)
- Requires `uv run python` prefix for Python execution
- Blocks inline Python (`python -c`)
- Warns on git commits outside code-review agent
- Blocks temporary test files in `/tmp/`

**Exit codes:**
- `0` - Allow (optionally with prompt)
- `1` - Warn (allow with warning to agent)
- `2` - Block (show error, prevent execution)

**SubagentStop/Stop** (`validate_stop.py`):
- Validates agent completion state
- Can enforce completion requirements

### Git Pre-Commit Hooks

Installed via `scripts/git-hooks/install-hooks.sh`.

**Documentation bloat prevention**:
- Blocks new `.md` files (except research papers, agent instructions)
- Prompts user for explicit confirmation
- Enforces "self-documenting code" principle

**Python code quality** (`.pre-commit-config.yaml`):
- `ruff` - Linting and formatting
- `mypy` - Static type checking
- `pytest` - Fast unit tests

### Permission System

Fine-grained tool access control in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)",
      "mcp__gh__create_issue"
    ],
    "deny": [
      "Write(**/*.md)",
      "Write(**/*.env*)",
      "Read(**/*.cache/**)"
    ]
  }
}
```

Deny rules take precedence over allow rules.

---

## Agent Responsibilities

academicOps provides specialized agents for different types of work. Each has clear scope and boundaries.

### Agent Architecture: Two Types

**Critical design decision** (Issue #134, _CORE.md Axiom 4):

**Regular Agents** (all agents except SUPERVISOR):
- **Bounded workers** - do ONE specific thing, then stop
- Complete the task requested, nothing more
- If more work needed → ASK user for permission
- If related issues found → REPORT but don't fix
- Examples: Developer, Test-Cleaner, Review, Trainer

**SUPERVISOR Agent**:
- **Orchestrator** - manages multi-step workflows
- Breaks complex tasks into smallest atomic steps
- Calls specialized agents ONE AT A TIME via Task tool
- Validates each step before proceeding
- Continues until entire workflow complete

**Rationale**: Prevents scope creep, recursive debugging, and agents expanding their own workflows indefinitely. Regular agents are constrained; SUPERVISOR handles complexity.

**Pattern**:
- Single task needed → Regular agent does it and stops
- Multi-step workflow → Use SUPERVISOR to orchestrate
- Agent finds related issue → Reports it, doesn't expand scope
- User asks question → Agent answers and stops (doesn't launch into investigation)

---

### Agent Instructions: 3-Tier Loading (Issue #135)

**Desired state** (not yet implemented):

**Where instructions live** - Same location in every repo:
```
[nicsuzor/academicOps]/bots/agents/trainer.md    # Framework (base)
[nicsuzor/writing]/bots/agents/trainer.md        # Personal addenda
[otherproject]/bots/agents/trainer.md            # Project overrides
```

**All three use `bots/agents/` directory** - consistent across all repos.

**Thin wrappers**:

1. **Subagent file** (`.claude/agents/trainer.md`):
   ```yaml
   ---
   name: trainer
   description: Agent trainer
   model: opus
   ---

   Instructions loaded via SubagentStart hook from bots/agents/trainer.md
   ```

2. **Command file** (`.claude/commands/trainer.md`):
   ```markdown
   ---
   description: Activate trainer mode
   ---

   Load: ${ACADEMICOPS_BOT}/scripts/read_instructions.py bots/agents/trainer.md
   ```

**Loading mechanisms**:
- `@agent-trainer` (Task tool) → Agent self-loads via Read tool (no SubagentStart hook available)
- `/trainer` (command) → Manually loads instructions
- Both result in same instructions (framework + personal + project)

**Status**: Self-loading pattern implemented (SubagentStart hook does not exist in Claude Code)

**Implementation** (interim solution until SubagentStart hook becomes available):

1. **Minimal agent file** (`.claude/agents/trainer.md`):
   - Instructs agent to self-load from `bots/agents/trainer.md`
   - Uses Read tool to load 3-tier hierarchy
   - ~15 lines (mostly loading instructions)

2. **Full instructions** (`bots/agents/trainer.md`):
   - Framework base instructions (~700 lines)
   - Same location in every repo for consistency

3. **Project overrides** (`[project]/bots/agents/trainer.md`):
   - Optional project-specific additions
   - Loaded if exists

**Limitation**: Not enforced by hooks, relies on agent following self-loading instruction

### @agent-trainer

**Purpose**: Maintains and optimizes the agent framework itself

**Responsible for:**
- Agent instruction files (`agents/*.md`)
- Framework documentation (`ARCHITECTURE.md`, `INSTRUCTION-INDEX.md`)
- Configuration files (`.claude/settings.json`, hooks)
- Instruction loading system
- Error message UX
- Pre-commit hook configuration

**Not responsible for:** Project-specific work, writing application code, research tasks

### @agent-strategist

**Purpose**: Planning, scheduling, project management, context capture

**Responsible for:**
- Task management
- Project planning and milestones
- Meeting notes and decision capture
- Goal setting and progress reviews
- Auto-extraction during conversations

**Data access:** Only accesses `data/` directory when working in `$ACADEMICOPS_PERSONAL` repo

**Not responsible for:** Writing code, modifying framework, committing changes

### @agent-supervisor

**Purpose**: Orchestrates complex multi-step workflows

**Responsible for:**
- Breaking tasks into steps
- Calling specialized agents in sequence
- Validating each step
- Iterating until completion

**Not responsible for:** Direct code writing (delegates to other agents)

### @agent-developer

**Purpose**: Application code implementation

**Responsible for:**
- Feature implementation
- Test writing (TDD methodology)
- Debugging and bug fixes
- Refactoring application code
- Running test suites

**Not responsible for:** Framework changes, planning, committing code

### @agent-code-review

**Purpose**: Code review and git operations

**Responsible for:**
- Reviewing staged changes
- Running pre-commit hooks
- Creating git commits
- Creating pull requests
- Enforcing code standards

**Not responsible for:** Writing code, planning, framework modifications

### @agent-test-cleaner

**Purpose**: Test simplification and cleanup

**Responsible for:**
- Ruthlessly simplifying test suites
- Eliminating brittle unit tests
- Creating robust integration tests
- Working through broken tests

**Not responsible for:** Application code, framework changes

---

## Design Principles

### Complete Modularity

**Every concept documented exactly once, referenced everywhere else.**

Implemented through:
- ONE canonical source per concept
- Agent files reference, never duplicate
- Validation hooks prevent duplication
- If content appears in multiple places, that's a bug requiring fix

**Reference pattern in agent instructions:**
```markdown
# Agent Instructions

For dbt workflows, see .academicOps/docs/methodologies/dbt-practices.md
For user accommodations, see .academicOps/docs/accommodations.md
```

### Fail-Fast Philosophy

Described in agent instructions (`agents/_CORE.md`), enforced in framework design:

- Agents fail immediately on errors
- Fix underlying infrastructure instead of teaching workarounds
- Reliable systems preferred over defensive programming instructions
- No `.get(key, default)` - explicit configuration required

### Project Isolation

Described in agent instructions, enforced in framework:

- Projects work independently
- No cross-dependencies between submodules
- Project-specific content stays in project repositories
- Shared infrastructure versioned explicitly

---

## Installation

### Prerequisites

- Python 3.12+ with `uv` package manager
- Claude Code CLI installed and configured
- Git repository for your project

### Environment Variables

```bash
# Required
export ACADEMICOPS_BOT=/path/to/academicOps

# Optional (for personal context/preferences)
export ACADEMICOPS_PERSONAL=/path/to/your/writing
```

Add to shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to persist.

### One-Command Setup

```bash
cd /path/to/your/project
$ACADEMICOPS_BOT/scripts/install_bot.sh
```

**What it creates:**
- `/bots/` directory structure
- `.claude/settings.json` with hook configuration
- Symlinks to framework agents and commands
- Git pre-commit hooks
- `.gitignore` updates

**Verification:**
```bash
claude  # Launch Claude Code
# Should see: "Loaded _CORE.md: ✓ bot ✓ project"
```

See `INSTALL.md` for detailed installation instructions and troubleshooting.

---

## Open Questions & Evolution Tracking

This section documents design decisions still being validated and known tensions in current implementation.

### Context Loading Scope

**Current implementation** (inferred from reference repo):
- Personal preferences load in all repos ✓
- Strategic data (`data/`) only accessible when working in personal repo ✓

**Needs validation:**
- Integration tests to confirm behavior across repo boundaries
- Real-world testing with multiple project repos
- Documented specification of privacy boundary semantics

**Tracking:** Issue #128

### Privacy Boundaries for Shared Repositories

**Current behavior:**
- Project repos can read from `$ACADEMICOPS_PERSONAL` (user preferences)
- Strategic data not automatically loaded in project repos
- Symlinks gitignored (safe to share repos publicly)

**Open questions:**
- Formal specification for mixed public/private repo scenarios
- Security review for shared repository contexts
- Best practices documentation

**Tracking:** Issue #128

### Migration from Legacy Structure

**Current state:**
- New `/bots/` standard defined
- Installation script functional
- Reference implementation (`~/src/writing`) migrated
- Legacy paths supported as fallback

**Needs completion:**
- Migration procedure documentation
- Bulk migration script for existing installations
- Deprecation timeline for legacy paths
- Communication plan for users

**Tracking:** Issue #128

### Slash Command Organization

**Current implementation:**
- Framework commands in `$ACADEMICOPS_BOT/.claude/commands/`
- Repo-local commands in `bots/commands/` (new standard)
- Commands symlinked to `.claude/commands` in project repos
- No formal override/shadowing specification

**Available framework commands:**
- `/dev` - Load developer workflow (DEVELOPER.md with 6-step process, EXPLORE MANDATORY)
- `/ttd` - Load test-driven development methodology
- `/log-failure` - Report agent/framework issues to academicOps
- `/trainer` - Activate trainer mode for framework improvements
- `/ops` - View all available commands

**Design decision: On-demand loading vs auto-loading** (Issue #133)

**Chosen approach**: Specialized workflows loaded on-demand via slash commands
- `/dev` for development workflow (not auto-loaded)
- `/ttd` for test-driven development methodology
- User explicitly signals intent ("I'm developing now")
- Zero token cost for non-development sessions

**Evaluation**: Track usage patterns over time to determine if frequently-used commands should become auto-loaded in specific project types.

**Needs design:**
- How do repo-local commands override framework commands?
- Command discovery order specification
- Namespace collision handling
- Documentation for command authors

---

## Updating This Documentation

**When to update ARCHITECTURE.md:**
- Design decision made based on real usage
- Tension discovered between documentation and reality
- Migration completed (move from "Open Questions" to implementation section)
- New component added to framework
- User asks "how does X work?" and answer isn't here

**How to update:**
1. Describe current state, not future plans
2. Move completed items from "Open Questions" to appropriate sections
3. Add newly discovered tensions to "Open Questions"
4. Keep concise - link to detailed docs for specifics
5. Maintain descriptive voice (not imperative)

**Principle**: This file always describes the working system as it exists today.

---

## See Also

- `README.md` - Quick start guide for new users
- `INSTALL.md` - Detailed installation instructions
- `docs/hooks_guide.md` - Deep dive on hook system
- `docs/TESTING.md` - Test writing guidance
- `docs/INSTRUCTION-INDEX.md` - Complete index of instruction files
- `agents/_CORE.md` - Core axioms (agent instructions)
- `agents/TRAINER.md` - Trainer agent instructions
