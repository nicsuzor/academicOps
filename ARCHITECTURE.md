# academicOps Architecture

Single source of truth for the academicOps agent framework: what exists, how it works, and who is responsible.

## Agent Responsibilities

### @agent-trainer
**Scope:** Agent framework infrastructure and meta-system maintenance

- Agent instruction files (`agents/*.md`)
- Framework documentation (`docs/`, this file)
- Configuration (`.claude/settings.json`, validation hooks)
- Instruction loading system (SessionStart hooks, discovery patterns)
- Error message UX for validation failures
- Pre-commit hook configuration

**NOT responsible for:** Project-specific work, writing application code, research tasks

### @agent-strategist
**Scope:** Planning, scheduling, project management, context capture

- Task management (creating, organizing, prioritizing tasks)
- Project planning and milestone tracking
- Meeting notes and decision documentation
- Goal setting and progress reviews
- Context capture from conversations

**NOT responsible for:** Writing code, modifying agent instructions, framework changes

### @agent-developer
**Scope:** Writing, testing, and debugging application code

- Implementing features in project code
- Writing tests (following TDD methodology)
- Debugging and fixing bugs
- Refactoring application code
- Running test suites

**NOT responsible for:** Agent framework changes, project planning, committing code

### @agent-code-review
**Scope:** Code review and git commit operations

- Reviewing staged changes for quality
- Running pre-commit validation hooks
- Creating git commits with conventional messages
- Creating pull requests
- Enforcing code standards

**NOT responsible for:** Writing code, planning features, modifying agent instructions

### @agent-analyst
**Scope:** Data analysis workflows (dbt, SQL, data pipelines)

- dbt model development and testing
- SQL query optimization
- Data pipeline debugging
- Analytics code review

**NOT responsible for:** General application development, agent framework changes

## Instruction Loading Hierarchy

### Automatic Loading (SessionStart Hook)

**Order of execution:**
1. `bot/agents/_CORE.md` - Core axioms (all agents)
2. `docs/agents/INSTRUCTIONS.md` - User context (if exists in parent repo)
3. Project `CLAUDE.md` files - Discovered when accessing files in subdirectories

**Hook location:** Configured in `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": "uv run python bot/scripts/validate_env.py"
  }
}
```

### Agent-Specific Loading

When you invoke `@agent-{name}`, Claude loads:
- All SessionStart instructions (above)
- Agent-specific file: `bot/agents/{NAME}.md`

**Example:** `@agent-developer` loads:
1. `_CORE.md` (axioms)
2. `docs/agents/INSTRUCTIONS.md` (your context)
3. `DEVELOPER.md` (agent-specific instructions)

### Project Discovery Pattern

**Polyrepo structure:**
```
/your-research-repo/          ← Parent repo
├── docs/agents/
│   └── INSTRUCTIONS.md       ← Your team context
├── projects/
│   └── project-a/
│       └── CLAUDE.md         ← Project-specific rules (auto-discovered)
└── bot/                      ← academicOps submodule
    └── agents/               ← Agent instructions
```

**Discovery mechanism:** When agents access files in `projects/project-a/`, Claude automatically discovers and loads `CLAUDE.md` from that directory.

## Validation & Enforcement System

### Pre-Tool-Use Hook

**File:** `bot/scripts/validate_tool.py`

**Purpose:** Enforces tool usage rules before agents execute tools

**Rules enforced:**
- Markdown file creation restricted (prevents documentation bloat)
- Python execution requires `uv run` prefix
- Inline Python (`python -c`) blocked
- Git commits warn for non-code-review agents
- `/tmp` test files blocked

**Configuration:** Runs automatically via Claude Code's PreToolUse hook

### Pre-Commit Hooks

**File:** `bot/.pre-commit-config.yaml`

**Purpose:** Code quality enforcement before git commits

**Hooks:**
- `ruff-check` - Python linting with auto-fixes
- `ruff-format` - Python code formatting
- `mypy` - Static type checking
- `radon` - Complexity and maintainability metrics
- `test-architecture` - Test file location validation
- `pytest` - Fast unit tests only

**Performance:** Only runs on Python file changes (optimized for fast doc commits)

## Active Files Registry

### Agent Instructions (6 files)

- `agents/_CORE.md` - Core axioms loaded for all agents
- `agents/TRAINER.md` - Agent framework maintenance
- `agents/STRATEGIST.md` - Planning and project management
- `agents/DEVELOPER.md` - Code implementation
- `agents/CODE.md` - Code review and commits (invoked as @agent-code-review)
- `agents/ANALYST.md` - Data analysis workflows (dbt, SQL)

### Framework Documentation (4 files)

- `ARCHITECTURE.md` - This file (system overview)
- `INSTALL.md` - Installation guide for new adopters
- `README.md` - Project introduction
- `docs/INSTRUCTION-INDEX.md` - Detailed file-by-file index (maintenance tracking)

### Configuration Files (2 files)

- `CLAUDE.md` - Points to `_CORE.md` for SessionStart loading
- `GEMINI.md` - Gemini CLI configuration (experimental)

### User Context Layer (2 files)

- `docs/agents/INSTRUCTIONS.md` - Template for user-specific context
- `docs/agents/README.md` - Guidance on customizing instructions

### Validation & Hooks (multiple files)

**Scripts:**
- `scripts/validate_env.py` - SessionStart hook (loads core instructions)
- `scripts/validate_tool.py` - PreToolUse hook (enforces tool rules)
- `scripts/code_review.py` - Code quality validation rules
- `scripts/check_test_architecture.py` - Test file location validation

**Pre-commit:**
- `.pre-commit-config.yaml` - Hook configuration

### Methodologies (2 files)

- `docs/methodologies/computational-research.md` - Research workflows
- `docs/methodologies/dbt-practices.md` - Analytics engineering patterns

### Experimental Methodology Chunks (3 files)

**Location:** `docs/_CHUNKS/` (Issue #111 Phase 2)

- `_CHUNKS/FAIL-FAST.md` - Fail-fast philosophy for agents
- `_CHUNKS/GIT-WORKFLOW.md` - Git submodule workflow patterns
- `_CHUNKS/README.md` - Chunk usage and promotion process

**Status:** Experimental - awaiting Phase 3 integration experiments

### Test Infrastructure (3 files)

- `tests/prompts/CONTEXT-AWARENESS-TESTS.md` - Test scenarios for context loading
- `tests/prompts/README.md` - Test prompt organization
- `tests/results/TEMPLATE.md` - Test result documentation template

### Issue Templates (1 file)

- `.github/ISSUE_TEMPLATE/agent_failure_analysis.md` - Template for reporting agent failures

### Experimental/Deprecated (1 file)

- `prompts/editor-structural.md` - Structural editing prompts (status unclear)

## Archived Files

**Location:** `bot/docs/_UNUSED/` (34 files)

**Status:** Archived obsolete documentation (Issue #111 Phase 2 complete)

**Categories:**
- Obsolete architecture docs (superseded by ARCHITECTURE.md)
- Deprecated agent templates
- Outdated indexes and references
- Project-specific content (not framework-level)

**Note:** 2 chunks extracted to `_CHUNKS/` for experimental use. Remaining 32 files archived as-is.

**Do not reference these files** - they are obsolete or duplicative.

## Design Principles

### Complete Modularity (Issue #111)

**Every concept documented exactly once, referenced everywhere else.**

- ONE canonical source per concept
- Agent files reference, never duplicate
- Predictable file locations for discovery
- Validation hooks prevent duplication

**Reference pattern:**
```markdown
# Agent Instructions

Load methodologies:
- @bot/docs/methodologies/dbt-practices.md
- @docs/agents/INSTRUCTIONS.md (if exists)
```

### Enforcement Hierarchy

**Reliability order (most → least):**
1. **Scripts** - Code that prevents bad behavior
2. **Hooks** - Automated checks at key moments
3. **Configuration** - Permissions and restrictions
4. **Instructions** - Last resort (agents forget in long conversations)

**Principle:** If agents consistently disobey instructions, move enforcement up the hierarchy.

### Fail-Fast Philosophy

- Agents should fail immediately on errors
- Fix underlying infrastructure, don't teach workarounds
- Reliable systems > defensive programming instructions

## File Lifecycle

### Adding New Files

**Process:**
1. Create GitHub issue describing purpose
2. Add file to appropriate directory
3. Update this ARCHITECTURE.md file registry
4. Update `docs/INSTRUCTION-INDEX.md` (detailed tracking)
5. Commit with issue reference

**Trainer approval required for:**
- New agent instruction files
- New framework documentation
- Changes to validation hooks

### Removing/Archiving Files

**Process:**
1. Move to `docs/_UNCHECKED/` or `docs/_UNUSED/`
2. Update this registry (remove from active list)
3. Document reason in GitHub issue
4. Commit with issue reference

### Promoting Experimental Chunks

**Process (Phase 3 of Issue #111):**
1. Create experiment issue with success metrics
2. Link chunk in agent instruction
3. Track metrics over evaluation period
4. Document results in issue
5. If successful: Move to `docs/` (becomes canonical)
6. If failed: Move to `docs/_UNUSED/`

## Maintenance

**Responsibility:** @agent-trainer

**Frequency:** Update this file whenever:
- New agent files added
- Documentation structure changes
- Validation rules change
- Instruction loading mechanism changes

**Related files:**
- `docs/INSTRUCTION-INDEX.md` - More detailed file-by-file tracking
- Issue #111 - Modular documentation architecture project

**Last updated:** 2025-10-17
