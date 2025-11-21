# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## academicOps Repository Structure

**Note**: User-specific files (ACCOMMODATIONS, CORE, STYLE, VISION, ROADMAP) live in `$ACA_DATA`, not in this repository. This repo contains only generic framework infrastructure.

```
$AOPS/
├── AXIOMS.md            # Framework principles (auto-injected via SessionStart hook)
├── README.md            # THIS FILE - framework directory map
├── CLAUDE.md            # Framework repo session start instructions
│
├── BMEM-FORMAT.md       # bmem markdown format specification
├── BMEM-CLAUDE-GUIDE.md # Using bmem from Claude Code
├── BMEM-OBSIDIAN-GUIDE.md # Using bmem with Obsidian
│
├── skills/              # Agent skills (specialized workflows - invoke via Skill tool)
│   ├── framework/       # Framework maintenance, experimentation, strategic partner
│   │   ├── SKILL.md     # Main skill instructions
│   │   ├── TASK-SPEC-TEMPLATE.md # Template for automation specifications
│   │   ├── workflows/   # Step-by-step procedures (design, debug, experiment, monitor, review, spec)
│   │   ├── references/  # Technical references (hooks guide, script design, testing patterns)
│   │   └── specs/       # Task specifications for planned automations
│   ├── analyst/         # Data analysis (dbt, Streamlit, statistical methods)
│   │   └── SKILL.md
│   ├── python-dev/      # Production Python code (type safety, fail-fast, research standards)
│   │   └── SKILL.md
│   ├── tasks/           # Task management system (MCP server)
│   │   ├── SKILL.md     # Task operations skill
│   │   ├── README.md    # Task system documentation
│   │   ├── server.py    # MCP server implementation
│   │   ├── task_ops.py  # Task operation functions
│   │   └── models.py    # Task data models
│   ├── bmem/            # Knowledge base operations (MCP wrapper)
│   │   └── SKILL.md
│   └── feature-dev/     # Feature development workflow (future)
│       └── SKILL.md
│
├── hooks/               # Lifecycle automation (Python scripts triggered by Claude Code events)
│   ├── README.md        # Hook documentation (configuration, available hooks, debugging)
│   ├── sessionstart_load_axioms.py  # SessionStart hook - injects AXIOMS.md at session start
│   ├── user_prompt_submit.py        # UserPromptSubmit hook - injects additional context on every prompt
│   ├── session_logger.py            # Session logging module
│   ├── log_session_stop.py          # Stop hook - logs session activity
│   ├── extract_session_knowledge.py # Knowledge extraction from session
│   └── prompts/         # Markdown prompts loaded by hooks
│
├── experiments/         # Temporary experiment logs (moved to $ACA_DATA/projects/aops/experiments/ when finalized)
│   └── YYYY-MM-DD_*.md  # Work-in-progress experiments
│                        # NOTE: Learning patterns LOG.md and completed experiments live at $ACA_DATA/projects/aops/experiments/
│
├── scripts/             # Deployment and maintenance scripts
│   └── package_deployment.py  # Release packaging for GitHub
│
├── lib/                 # Shared Python utilities
│   └── paths.py         # Path resolution (single source of truth for paths)
│
├── tests/               # Framework integration tests (pytest) - AUTHORITATIVE test location
│   ├── README.md        # Test documentation (markers, fixtures, coverage)
│   ├── conftest.py      # Unit test fixtures (paths)
│   ├── paths.py         # Path resolution utilities
│   ├── test_*.py        # Unit tests (paths, fixtures, documentation, skills, tasks)
│   ├── run_integration_tests.py  # Test runner script
│   └── integration/     # E2E tests (slow, require Claude execution)
│       ├── conftest.py          # Integration test fixtures (headless execution)
│       ├── test_bmem_skill.py   # Bmem skill integration tests
│       ├── test_session_start_content.py # Session start validation tests
│       └── test_task_viz.py     # Task visualization dashboard tests
│
├── commands/            # Slash commands (workflow triggers)
│   ├── bmem.md          # Invoke bmem skill
│   ├── email.md         # Extract tasks from emails
│   ├── learn.md         # Update memory/instructions
│   ├── log.md           # Log agent performance
│   ├── meta.md          # Invoke framework skill for strategic questions
│   ├── task-viz.md      # Generate visual task dashboard (mind-map)
│   └── ttd.md           # Test-driven development orchestration
│
├── agents/              # Agentic workflows (future)
└── config/              # Configuration files
```

---

## Knowledge Base (bmem)

**Single knowledge base per user**: bmem maintains ONE personal knowledge base across all projects.

**Location**: Knowledge base stored at `$ACA_DATA` (environment variable pointing to user's private data repository).

**Key architecture principles**:

1. **Single source of truth** - All notes, entities, and metadata stored in one place, regardless of current working directory
2. **Write location invariant** - bmem writes to `$ACA_DATA` always, enabling seamless access across projects
3. **Format** - Markdown files with YAML frontmatter for metadata (tags, types, relationships)
4. **Indexing** - Automatic background vector search indexing (full-text and semantic search)
5. **Access** - Claude Code integrates via MCP server and `mcp__bmem__*` function tools

**Result**: Work in any project, knowledge base stays consistent and queryable. No per-project duplication.

**CLI**: `uvx basic-memory --help`. See `skills/bmem/SKILL.md` for operations guide.

---

## User Data Repository Structure

academicOps stores user data separately from framework code. User-specific files live here:

```
$ACA_DATA/  (e.g., ~/writing/data/)
├── ACCOMMODATIONS.md    # Work style requirements (loaded via @ in user CLAUDE.md)
├── CORE.md              # User context, tools, paths (loaded via @ in user CLAUDE.md)
├── STYLE-QUICK.md       # Writing style reference (loaded via @ in user CLAUDE.md)
├── STYLE.md             # Full writing style guide (referenced, not @-loaded)
│
├── tasks/               # Task data (markdown files, bmem-compliant)
│   ├── active/          # Current tasks
│   ├── completed/       # Finished tasks
│   └── deferred/        # Postponed tasks
│
├── sessions/            # Claude Code session logs
│   └── YYYY-MM-DD_HH-MM-SS.md
│
├── projects/            # Project-specific data
│   └── aops/            # academicOps project data
│       ├── VISION.md    # End state: fully-automated academic workflow
│       ├── ROADMAP.md   # Maturity stages 0-5, progression plan
│       └── experiments/ # Framework experiment logs
│           └── LOG.md   # Learning patterns (append-only)
│
└── [other bmem entities] # People, orgs, concepts, work items, etc.
```

---

## Installation in Other Projects

academicOps installs via symlinks to user's `~/.claude/`:

```
project-repo/           # Any academic project repository
├── .claude/            # Claude Code configuration directory
│   ├── CLAUDE.md       # Project-specific instructions (uses @ syntax to auto-load files)
│   ├── skills/         # Symlink → $AOPS/skills/
│   ├── hooks/          # Symlink → $AOPS/hooks/
│   └── commands/       # Symlink → $AOPS/commands/
├── README.md           # Project structure (loaded via @README.md in project CLAUDE.md)
├── [project files...]
```

**Installation**: Download [latest release](https://github.com/nicsuzor/academicOps/releases), extract, run `bash setup.sh`.

**Session start context**:
1. **Automatic hook injection** - SessionStart hook (`hooks/sessionstart_load_axioms.py`) automatically injects AXIOMS.md content at every session start
2. **CLAUDE.md @ syntax** - Files prefixed with `@` in CLAUDE.md are auto-loaded by Claude Code
3. **UserPromptSubmit hook** - Additional context injected on every user prompt via `hooks/user_prompt_submit.py`

---

## Contact

- **Repository**: https://github.com/nicsuzor/academicOps
- **Releases**: https://github.com/nicsuzor/academicOps/releases
