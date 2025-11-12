# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## Structure

```
bots/
├── CORE.md              # User context, tools, paths (loaded at session start)
├── AXIOMS.md            # Universal principles (loaded at session start)
├── ACCOMMODATIONS.md    # ADHD work style (loaded at session start)
├── STYLE-QUICK.md       # Writing style quick ref (loaded at session start)
├── STYLE.md             # Full writing style guide (referenced, not loaded)
├── README.md            # THIS FILE - framework documentation
│
├── skills/              # Agent skills (specialized workflows)
│   ├── framework/       # Framework maintenance skill
│   ├── analyst/         # Data analysis (dbt, Streamlit, stats)
│   ├── python-dev/      # Production Python code
│   └── feature-dev/     # Feature development workflow
│
├── hooks/               # Lifecycle hooks
│   ├── hooks.json       # Hook configuration
│   ├── README.md        # Hook documentation
│   ├── session_logger.py         # Session logging module
│   ├── log_session_stop.py       # Stop hook
│   ├── extract_session_knowledge.py  # LLM-powered knowledge extraction
│   └── prompts/         # Markdown prompts for hooks
│
├── commands/            # Slash commands (future)
├── agents/              # Agentic workflows (future)
└── config/              # Configuration files (future)
```

---

## What Are Skills?

**Skills** are specialized agent workflows for specific domains or tasks. Each skill provides:

- Domain expertise (e.g., statistical analysis, Python development)
- Specific tools and methods
- Quality standards and best practices
- Integration tests for validation

### Available Skills

| Skill           | Purpose                                                | When to Use                                |
| --------------- | ------------------------------------------------------ | ------------------------------------------ |
| **framework**   | Framework maintenance, experimentation, debugging      | Working on framework infrastructure itself |
| **analyst**     | Data analysis with dbt, Streamlit, statistical methods | Academic research, data processing         |
| **python-dev**  | Production-quality Python code with type safety        | Writing Python for research or tools       |
| **feature-dev** | Feature development workflow (future)                  | Building new features systematically       |

### Using Skills

Skills are invoked via the `Skill` tool in Claude Code:

```
Skill(framework)  # Launch framework skill
Skill(analyst)    # Launch analyst skill
```

Each skill file (`skills/*/SKILL.md`) contains complete instructions for that domain.

---

## What Are Hooks?

**Hooks** are Python scripts that execute automatically at Claude Code lifecycle events:

| Hook     | Event        | Purpose                                  |
| -------- | ------------ | ---------------------------------------- |
| **Stop** | Session ends | Log session activity to `data/sessions/` |

Hooks are configured in `hooks/hooks.json` and documented in `hooks/README.md`.

**Note**: Hooks are for automation, not for agent instructions. Agent behavior is controlled by CLAUDE.md and referenced files.

---

## Discovering Framework Capabilities

### For Agents: "Have we built X?"

When a user asks "have we built X" or "do we have Y capability":

1. **Check skills first**: `ls bots/skills/*/SKILL.md` and read relevant SKILL.md files
2. **Check experiment log**: `data/projects/aops/experiments/LOG.md` for recent work
3. **Check hooks**: `bots/hooks/README.md` for automation capabilities
4. **Only then explore**: If not found in framework docs, explore the codebase

**Pattern**: Framework questions → Framework documentation first, NOT codebase exploration.

### For Users: Quick Discovery

**See all skills**:

```bash
ls bots/skills/*/SKILL.md
```

**Read a skill**:

```bash
cat bots/skills/analyst/SKILL.md
```

**See framework experiments**:

```bash
cat data/projects/aops/experiments/LOG.md
```

---

## Adding New Components

**PROHIBITED** without integration tests. See `bots/skills/framework/SKILL.md` for complete workflow.

**Quick version**:

1. Design integration test FIRST
2. Run test (must fail before component exists)
3. Implement component
4. Run test (must pass)
5. Update this README.md
6. Commit only if all tests pass

---

## Core Principles

All framework work follows [[AXIOMS.md]].

---

## Migration from academicOps

The old `academicOps/` (also called `aOps/`) framework has been replaced by this minimal `bots/` framework.

**Why**: Bloat. Over-engineering. Complexity.

**What was migrated**:

- Core principles → `AXIOMS.md`, `CORE.md`
- analyst skill → `skills/analyst/`
- Session logging → `hooks/session_logger.py`
- Framework design philosophy → `skills/framework/SKILL.md`

**What was NOT migrated**:

- Tasks skill (now handled differently via `data/tasks/`)
- Email skill (use Outlook MCP directly)
- git-commit skill (use Claude Code native git workflow)
- bmem-ops skill (use bmem MCP directly)
- Various other specialized skills (re-add only if proven necessary)

The old `academicOps/` directory remains for reference but is no longer active.

---

## Testing

All framework changes require passing integration tests:

```bash
# Test documentation integrity
bash bots/skills/framework/tests/test_framework_integrity.sh

# Test specific components
bash bots/skills/framework/tests/test_*.sh
```

**Rule**: If tests fail, fix or revert. Never commit broken state.

---

## Learning & Evolution

The framework learns from successes and failures:

- **Experiment log**: `skills/framework/experiments/LOG.md`
- **Experiment designs**: `skills/framework/experiments/YYYY-MM-DD_*.md`

Experiments must be:

- Well-designed with clear hypothesis
- Discrete and evaluable
- Documented with decision (keep/revert/iterate)

---

**Last updated**: 2025-11-10 **Authoritative source**: This file (`bots/README.md`)
