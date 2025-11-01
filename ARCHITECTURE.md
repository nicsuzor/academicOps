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
~/.claude/                      # Global Claude Code configuration (OWNED by academicOps)
├── settings.json               # Global hooks and environment variables
│   └── env.ACADEMICOPS    # Points to academicOps installation
└── skills/                     # Deployed portable workflows (from dist/skills/*.zip)

/path/to/academicOps/          # academicOps framework installation
├── bots/                       # Agent instructions and hooks
│   ├── agents/                # Agent instruction files (rules)
│   │   └── _CORE.md          # Core axioms
│   └── hooks/                 # Hook scripts (called via $ACADEMICOPS)
├── .claude/skills/            # Skill source code (for development)
├── dist/skills/               # Packaged skills (*.zip for deployment)
├── scripts/                   # Utility scripts
└── docs/                      # Human documentation

any-repo/                      # Individual project repos
├── .claude/settings.json      # Project-specific hooks (optional, overrides global)
├── bots/                      # Project-specific bot configuration (optional)
│   ├── agents/               # Project-specific agent rules
│   │   └── _CORE.md         # Project context
│   └── hooks/                # Project-specific hooks
└── docs/                      # Human documentation
```

**Key architectural decisions:**

1. **Global `~/.claude/` ownership**: academicOps installs hooks and environment variables globally
2. **`$ACADEMICOPS` environment variable**: Available everywhere, points to framework installation
3. **Settings symlinked**: `~/.claude/settings.json` → `$ACADEMICOPS/.claude/settings.json` (single source of truth)
4. **Skills deployed to `~/.claude/skills/`**: Extracted from `dist/skills/*.zip`, available globally
5. **Project-local overrides**: Projects can override global hooks with `.claude/settings.json`
6. **Hook invocation**: Global hooks use `uv run --directory "$ACADEMICOPS"` for dependencies
7. **`bots/` namespace**: All agent instructions and hooks live under `bots/` directory

**Rule enforced in agent instructions**: Never put agent rules in `docs/`, never put human documentation in `bots/`.

### Configuration Management

**Canonical settings.json** lives in `$ACADEMICOPS/.claude/settings.json` and is **symlinked** to `~/.claude/settings.json` by `scripts/setup_academicops.sh`.

**Why symlink instead of copy:**
- **Single source of truth**: Hook configuration version-controlled in academicOps repo
- **Automatic updates**: Changes to hooks propagate immediately when git pulling updates
- **No drift**: User's local config stays in sync with framework improvements
- **Easier maintenance**: No manual copying of hook configurations

**What's in canonical settings.json:**
- `ACADEMICOPS` environment variable
- All 9 Claude Code hook events (SessionStart, PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, SessionEnd, PreCompact, Notification)
- Standard permissions (allow `uv run pytest/python`, `gh issue create`)
- Deny patterns (prevent writing to `.env`, `.venv`, `.cache`)
- Custom status line showing user@host, directory, git branch, venv

**Local customization:**
If you need machine-specific settings, you have two options:
1. **Edit the canonical file** in `$ACADEMICOPS/.claude/settings.json` (commit if universal, gitignore if personal)
2. **Break the symlink**: Remove symlink and copy the file to customize locally (not recommended—you'll lose auto-updates)

---

## Instruction Loading System

### Simplified Mental Model (Current Implementation)

academicOps uses **ONE tiered file** and **explicit references** for everything else.

### SessionStart: `_CORE.md` Only (3-Tier)

Every session automatically loads `_CORE.md` from up to three tiers:

```
$ACADEMICOPS/bots/agents/_CORE.md              (Framework - REQUIRED)
$ACADEMICOPS_PERSONAL/bots/agents/_CORE.md         (Personal - optional)
$PWD/bots/agents/_CORE.md                          (Project - optional)
```

**Why tiered?** Core axioms, personal style, and project conventions legitimately vary:
- **Framework**: Core axioms (DO ONE THING, fail-fast, DRY)
- **Personal**: Your work style, preferences, accommodations
- **Project**: Project-specific conventions, team agreements

**Loading behavior:**
- Framework tier is REQUIRED (fails if missing)
- Personal and Project tiers are OPTIONAL (silently skipped if missing)
- All found tiers merged and presented together
- Priority in conflicts: Project > Personal > Framework

### Everything Else: Single-Tier, Explicit

**Slash commands** (like `/dev`, `/trainer`) load from **framework only**:

```bash
# /dev loads ONLY from framework
$ACADEMICOPS/bots/agents/DEVELOPER.md

# /trainer loads ONLY from framework
$ACADEMICOPS/bots/agents/trainer.md
```

**Why?** These are generic workflows that don't need project customization. If you need project-specific variations, reference them explicitly in your project's CLAUDE.md:

```markdown
# Project CLAUDE.md
@agents/_CORE.md                          # Gets 3-tier loading automatically
@bots/DEBUGGING.md                        # Project-specific debugging guide
@bots/DEPLOYMENT.md                       # Project-specific deployment process
@../.claude/skills/test-writing/SKILL.md  # Framework skill
```

**Project-specific instructions**: Put them in `bots/*.md` in your project and reference explicitly. No magic, clear ownership.

**Implementation note**: The `load_instructions.py` script technically supports 3-tier loading for any file, but we only use it for `_CORE.md` to keep the mental model simple. Other files are single-tier by convention.

### Quick Reference: Where Do Instructions Go?

**"Where do I put debugging instructions for my project?"**
→ `your-project/bots/DEBUGGING.md` and reference it in `CLAUDE.md`

**"Where do I put my personal work style preferences?"**
→ `$ACADEMICOPS_PERSONAL/bots/agents/_CORE.md`

**"Where do I put project-specific conventions?"**
→ `your-project/bots/agents/_CORE.md`

**"Where do generic development workflows go?"**
→ Already in framework at `$ACADEMICOPS/bots/agents/DEVELOPER.md`

**"How do I know what gets auto-loaded?"**
→ Only `_CORE.md` is auto-loaded at SessionStart. Everything else requires explicit invocation (`/dev`) or reference (`@bots/DEBUGGING.md`)

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

### Framework Repository (`$ACADEMICOPS`)

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
- `setup_academicops.sh` - Installation script (creates symlinks to ~/.claude/)

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
│   ├── .academicOps/              # Symlink to $ACADEMICOPS
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
- Installation script available (`scripts/setup_academicops.sh`)
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

   Load: ${ACADEMICOPS}/scripts/read_instructions.py bots/agents/trainer.md
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

### trainer (`/trainer`, `TRAINER.md`)

**Purpose**: Maintains and optimizes the agent framework itself

**Responsible for:**
- Agent instruction files (`bots/agents/*.md`)
- Framework documentation (`ARCHITECTURE.md`, `INSTRUCTION-INDEX.md`)
- Configuration files (`.claude/settings.json`, hooks)
- Instruction loading system
- Error message UX
- Pre-commit hook configuration

**Invoked via:** `/trainer` slash command or Task tool with subagent_type="trainer"

**Not responsible for:** Project-specific work, writing application code, research tasks

### strategist (`/STRATEGIST`, `STRATEGIST.md`)

**Purpose**: Planning, facilitation, context capture

**Responsible for:**
- Strategic thinking partnership
- Facilitation through questioning frameworks
- Silent context capture during conversations
- Planning and brainstorming sessions
- Meeting users where they are

**Invoked via:** `/STRATEGIST` slash command

**Not responsible for:** Writing code, modifying framework, committing changes

### supervisor (Task tool, `SUPERVISOR.md`)

**Purpose**: Orchestrates complex multi-step workflows

**Responsible for:**
- Breaking tasks into smallest atomic steps
- Calling specialized agents ONE AT A TIME
- Validating each step before proceeding
- Iterating until entire workflow complete

**Invoked via:** Task tool with subagent_type="supervisor"

**Not responsible for:** Direct code writing (delegates to other agents)

### developer (`/dev`, `DEV.md`)

**Purpose**: Application code implementation

**Responsible for:**
- Feature implementation following TDD
- Test writing (integration test patterns)
- Debugging and bug fixes
- MANDATORY exploration before implementation
- Running test suites

**Invoked via:** `/dev` slash command

**Not responsible for:** Framework changes, planning, committing code

### code-review (invoked by agents, `REVIEW.md`)

**Purpose**: Code review and git operations

**Responsible for:**
- Reviewing staged changes
- Running pre-commit hooks
- Creating git commits
- Creating pull requests
- Enforcing code standards

**Invoked via:** Task tool by other agents (not directly by users)

**Not responsible for:** Writing code, planning, framework modifications

---

## Skills vs Subagents vs Commands

**Skills** (HOW): Technical expertise - single source of truth for operations
- `tasks` - task script operations, `email` - Outlook MCP, `pdf`/`xlsx`/`docx` - documents
- Location: `~/.claude/skills/`

**Subagents** (WHAT): Workflows that invoke skills
- `scribe` - background capture (uses tasks skill), `strategist` - planning (uses tasks + email skills)
- Location: `agents/`

**Commands** (shortcuts): User convenience
- `/email` → strategist, `/dev` → developer
- Location: `commands/`

**Rule**: Subagents decide WHAT, skills provide HOW. Never duplicate HOW across subagents.

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
export ACADEMICOPS=/path/to/academicOps

# Optional (for personal context/preferences)
export ACADEMICOPS_PERSONAL=/path/to/your/writing
```

Add to shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to persist.

### One-Command Setup

```bash
$ACADEMICOPS/scripts/setup_academicops.sh
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
- Framework commands in `$ACADEMICOPS/.claude/commands/`
- Repo-local commands in `bots/commands/` (new standard)
- Commands symlinked to `.claude/commands` in project repos
- No formal override/shadowing specification

**Available framework commands:**
- `/analyst` - Load analyst skill for academic research data analysis (dbt & Streamlit)
- `/dev` - Load developer workflow (DEV.md with 6-step process, EXPLORE MANDATORY)
- `/error` - Quick experiment outcome logging (aOps repo only)
- `/log-failure` - Report agent/framework issues to academicOps
- `/ops` - academicOps framework help and commands
- `/STRATEGIST` - Strategic thinking partner with silent context capture
- `/trainer` - Activate trainer mode for framework improvements
- `/ttd` - Load test-driven development methodology

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
