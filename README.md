# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## Structure

```
$AOPS/
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

1. **Check skills first**: `ls $AOPS/skills/*/SKILL.md` and read relevant SKILL.md files
2. **Check experiment log**: `$ACA_DATA/projects/aops/experiments/LOG.md` for recent work
3. **Check hooks**: `$AOPS/hooks/README.md` for automation capabilities
4. **Only then explore**: If not found in framework docs, explore the codebase

**Pattern**: Framework questions → Framework documentation first, NOT codebase exploration.

### For Users: Quick Discovery

**See all skills**:

```bash
ls $AOPS/skills/*/SKILL.md
```

**Read a skill**:

```bash
cat $AOPS/skills/analyst/SKILL.md
```

**See framework experiments**:

```bash
cat $ACA_DATA/projects/aops/experiments/LOG.md
```

---

## Adding New Components

**PROHIBITED** without integration tests. See `skills/framework/SKILL.md` for complete workflow.

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

## Architecture Evolution

The framework has been streamlined for run-from-anywhere operation using environment variables.

**Key changes**:

- Core principles → `AXIOMS.md`, `CORE.md`
- analyst skill → `skills/analyst/`
- Session logging → `hooks/session_logger.py`
- Framework design philosophy → `skills/framework/SKILL.md`
- Data storage → `$ACA_DATA/` (separate from code)
- Path resolution → `lib/paths.py` (single source of truth)

**Not included**:

- Tasks skill (now handled differently via `$ACA_DATA/tasks/`)
- Email skill (use Outlook MCP directly)
- git-commit skill (use Claude Code native git workflow)
- bmem-ops skill (use bmem MCP directly)
- Various other specialized skills (re-add only if proven necessary)

---

## Testing

All framework changes require passing integration tests:

```bash
# Test documentation integrity
bash $AOPS/skills/framework/tests/test_framework_integrity.sh

# Test specific components
bash $AOPS/skills/framework/tests/test_*.sh
```

**Rule**: If tests fail, fix or revert. Never commit broken state.

---

## Learning & Evolution

The framework learns from successes and failures:

- **Experiment log**: `$ACA_DATA/projects/aops/experiments/LOG.md`
- **Experiment designs**: `$ACA_DATA/projects/aops/experiments/YYYY-MM-DD_*.md`

Experiments must be:

- Well-designed with clear hypothesis
- Discrete and evaluable
- Documented with decision (keep/revert/iterate)

---

## Deployment

### Creating a Release Package

To package the framework for distribution to GitHub releases:

```bash
# Create deployment package (auto-versioned from git tags or date)
python3 scripts/package_deployment.py

# Or specify a custom version
python3 scripts/package_deployment.py --version v1.0.0

# Output will be in dist/aops-VERSION.tar.gz
```

The packaging script:

- Includes all necessary files (skills, hooks, scripts, config, docs)
- Excludes development files (tests, experiments, .git, __pycache__)
- Generates INSTALL.md with installation instructions
- Creates MANIFEST.json with package metadata

### Publishing to GitHub

```bash
# Create a new release with the generated archive
gh release create v1.0.0 dist/aops-v1.0.0.tar.gz \
  --title "aOps v1.0.0" \
  --notes "Release notes here"

# Or upload manually through GitHub web interface
```

### Beta Releases

Pushes to the `dev` branch automatically trigger beta releases via GitHub Actions. Beta versions follow the format: `<latest-tag>-beta.YYYYMMDD.<commit>` and are marked as pre-releases.

---

**Last updated**: 2025-11-16 **Authoritative source**: This file (`README.md`)
