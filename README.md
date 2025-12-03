# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## Framework Repository Structure ($AOPS)

```
$AOPS/
├── AXIOMS.md                # Framework principles (injected at session start)
├── README.md                # THIS FILE - structure reference
├── CLAUDE.md                # Framework repo instructions (@ syntax auto-loads)
├── BMEM-ARCHITECTURE.md     # bmem system architecture
├── BMEM-FORMAT.md           # bmem markdown format specification
├── BMEM-CLAUDE-GUIDE.md     # Using bmem from Claude Code
├── BMEM-OBSIDIAN-GUIDE.md   # Using bmem with Obsidian
├── pyproject.toml           # Python project config
├── uv.lock                  # Dependency lockfile
├── setup.sh                 # Creates ~/.claude/ symlinks
├── .gitignore               # Git ignore patterns
├── __init__.py              # Python package marker
│
├── .github/workflows/       # CI/CD automation
│   ├── beta-release.yml     # Beta release automation
│   ├── claude-code-review.yml # Claude-powered code review
│   ├── claude.yml           # General Claude integration
│   ├── ios-note-capture.yml # iOS note capture workflow
│   └── test-setup.yml       # Test environment setup
│
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── analyst/             # Data analysis (dbt, Streamlit, stats)
│   │   ├── _CHUNKS/         # Skill documentation chunks (exploratory analysis, dbt, streamlit)
│   │   ├── references/      # 13 statistical guides (test selection, assumptions, power, reporting)
│   │   └── scripts/
│   │       └── assumption_checks.py  # Statistical assumption validation
│   │
│   ├── bmem/                # Knowledge base ops (project="main")
│   │   └── references/      # Writing guides (quality, detail levels, Obsidian compat)
│   │
│   ├── dashboard/           # Live task dashboard (Streamlit, auto-refresh)
│   │   └── dashboard.py     # Task dashboard implementation
│   │
│   ├── docs-update/         # Documentation validation and updates
│   │
│   ├── excalidraw/          # Visual diagram generation (manual refinement)
│   │   ├── libraries/       # 6 icon libraries (stick-figures, data-viz, hearts, etc.)
│   │   └── references/      # 10 guides (JSON format, graph layouts, mind mapping)
│   │
│   ├── extractor/           # Archive extraction → bmem
│   │   └── tests/
│   │       └── test_archive_integration.sh  # Integration tests
│   │
│   ├── feature-dev/         # Feature development workflow
│   │   └── templates/       # 4 templates (dev plan, user story, test spec, experiment)
│   │
│   ├── framework/           # Framework maintenance (strategic partner)
│   │   ├── TASK-SPEC-TEMPLATE.md  # Task specification template
│   │   ├── references/      # 9 guides (hooks, testing, MCP tools, strategic mode)
│   │   ├── scripts/
│   │   │   └── validate_docs.py  # Documentation validation
│   │   ├── specs/
│   │   │   └── docs-update-skill.md  # Docs update spec
│   │   ├── tests/           # 10 integration tests (skill discovery, email workflow, etc.)
│   │   └── workflows/       # 6 workflows (design, debug, experiment, bloat prevention)
│   │
│   ├── framework-debug/     # Framework debugging
│   │   └── scripts/
│   │       └── errors.jq    # JQ script for error extraction
│   │
│   ├── learning-log/        # Performance pattern logging to thematic files
│   │
│   ├── pdf/                 # Markdown → PDF conversion
│   │   ├── assets/
│   │   │   ├── academic-style.css  # Academic document styles
│   │   │   ├── letter-style.css    # Letter format styles
│   │   │   └── fonts/              # 9 Roboto fonts (regular, bold, italic, mono)
│   │   └── scripts/
│   │       └── generate_pdf.py  # PDF generation script
│   │
│   ├── python-dev/          # Production Python standards
│   │   └── references/      # 10 guides (fail-fast, type safety, testing, pandas, FastAPI)
│   │
│   ├── skill-creator/       # Skill packaging
│   │   ├── LICENSE.txt      # Skill license template
│   │   └── scripts/         # 3 scripts (init, package, validate)
│   │
│   ├── tasks/               # Task management (MCP server)
│   │   ├── __init__.py      # Python package marker
│   │   ├── models.py        # Task data models
│   │   ├── server.py        # MCP server implementation
│   │   ├── task_loader.py   # Task loading logic
│   │   ├── task_ops.py      # Task operations
│   │   ├── scripts/         # 5 CLI utilities
│   │   │   ├── task_add.py       # Create new task
│   │   │   ├── task_update.py    # Modify task
│   │   │   ├── task_archive.py   # Archive task
│   │   │   ├── task_view.py      # View task details
│   │   │   └── task_viz.py       # Force-directed task graph → Excalidraw
│   │   ├── tests/
│   │   │   └── test_task_scripts.sh  # Task script tests
│   │   └── workflows/
│   │       └── email-capture.md  # Email → task workflow
│   │
│   ├── training-set-builder/  # Training data extraction
│   │
│   └── transcript/          # Session JSONL → markdown transcripts
│
├── hooks/                   # Lifecycle automation (Python)
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md at session start
│   ├── user_prompt_submit.py        # Injects context on every prompt
│   ├── prompt_router.py             # Keyword analysis → skill suggestions
│   ├── autocommit_state.py          # Auto-commit data/ after state changes
│   │
│   ├── session_logger.py            # Log file path management
│   ├── hook_logger.py               # Centralized event logging
│   ├── hook_debug.py                # Debug utilities
│   │
│   ├── log_sessionstart.py          # Log session start events
│   ├── log_userpromptsubmit.py      # Log user prompt submissions
│   ├── log_pretooluse.py            # Log before tool execution
│   ├── log_posttooluse.py           # Log after tool execution
│   ├── log_subagentstop.py          # Log subagent termination
│   │
│   ├── extract_session_knowledge.py # Knowledge extraction from sessions
│   ├── request_scribe.py            # Session documentation requests
│   ├── session_env_setup.sh         # Environment setup script
│   ├── test_marker_hook.py          # CI test hook
│   │
│   └── prompts/
│       └── user-prompt-submit.md    # User prompt context injection
│
├── commands/                # Slash commands (main agent executes directly)
│   ├── advocate.md          # Framework oversight with epistemic standards
│   ├── archive-extract.md   # Extract archived info to bmem
│   ├── bmem.md              # Capture session info to knowledge base
│   ├── bmem-validate.md     # Batch validate and fix bmem files
│   ├── docs-update.md       # Update README.md structure
│   ├── email.md             # Email → task extraction
│   ├── learn.md             # Minor instruction adjustments
│   ├── log.md               # Log agent performance patterns
│   ├── meta.md              # Invoke framework skill (strategic decisions)
│   ├── parallel-batch.md    # Parallel file processing with subagents
│   ├── qa.md                # Quality assurance verification
│   ├── strategy.md          # Strategic planning with Plan agent
│   ├── task-viz.md          # Launch task-viz agent (wrapper only)
│   ├── transcript.md        # Session transcript generation
│   └── ttd.md               # TDD orchestration workflow
│
├── agents/                  # Spawnable subagents (Task tool with subagent_type)
│   ├── bmem-validator.md    # Fix bmem validation errors in parallel
│   ├── dev.md               # Development task routing to python-dev
│   ├── email-extractor.md   # Email archive processing agent
│   └── task-viz.md          # Task graph visualization (bmem → excalidraw)
│
├── experiments/             # Temporary experiment logs
│   ├── 2025-11-17_log-sufficiency-test.md  # Log completeness test
│   ├── 2025-11-17_multi-window-cognitive-load-solutions.md  # UI research
│   ├── 2025-11-21_zotmcp-tdd-session.md    # TDD session log
│   ├── 2025-12-01_discoverability-annotations.md  # Annotation experiment
│   ├── session-bmem-fail.md # Failed bmem session
│   └── session-bmem-pass.md # Successful bmem session
│
├── scripts/                 # Deployment and utility scripts
│   ├── setup.sh             # Project setup script
│   ├── claude_transcript.py         # Session JSONL → markdown converter
│   ├── package_deployment.py        # Skill packaging
│   ├── measure_router_compliance.py # Prompt router analysis
│   └── migrate_log_entries.py       # Log migration utility
│
├── lib/                     # Shared Python
│   ├── __init__.py          # Python package marker
│   ├── activity.py          # Activity logging
│   └── paths.py             # Path resolution (SSoT)
│
├── tests/                   # pytest suite
│   ├── HOOK_TEST_PROTOCOL.md  # Hook testing protocol
│   ├── __init__.py          # Python package marker
│   ├── conftest.py          # Fixtures
│   ├── paths.py             # Test path utilities
│   ├── run_integration_tests.py  # Integration test runner
│   ├── run_skill_tests.sh   # Skill test runner
│   ├── manual_test_skill_discovery.md  # Manual test protocol
│   │
│   ├── test_*.py            # 31 unit tests (activity logger, bmem, hooks, paths, etc.)
│   │
│   ├── integration/         # E2E tests (slow)
│   │   ├── README_SKILL_TESTS.md  # Skill test documentation
│   │   ├── __init__.py      # Python package marker
│   │   ├── conftest.py      # Integration test fixtures
│   │   └── test_*.py        # 19 integration tests (bmem, skills, tasks, sessions)
│   │
│   └── tools/               # Tool-specific tests
│       ├── __init__.py      # Python package marker
│       ├── conftest.py      # Tool test fixtures
│       └── test_bmem_retrieve.py  # bmem retrieval tests
│
└── config/claude/           # Reference config (copied during install)
    ├── mcp.json             # MCP server configuration
    └── settings.json        # Claude Code settings
```

---

## Installed Structure (~/.claude/)

After `setup.sh`, symlinks connect framework components:

```
~/.claude/
│   # Symlinks to $AOPS (created by setup.sh)
├── skills/      → $AOPS/skills/
├── hooks/       → $AOPS/hooks/
├── commands/    → $AOPS/commands/
├── agents/      → $AOPS/agents/
│
│   # Claude Code runtime
├── settings.json            # User settings (hooks, permissions)
├── debug/                   # Session logs (hook output visible here)
├── projects/                # JSONL session data per repository
│   └── -repo-path/          # Path encoded with dashes
│       ├── *.jsonl          # User/assistant turns
│       └── agent-*.jsonl    # Subagent logs
├── history.jsonl
├── file-history/
├── session-env/
├── shell-snapshots/
├── todos/                   # TodoWrite persistence
└── statsig/
```

---

## User Data Repository ($ACA_DATA)

User-specific data lives separately from framework. Also the bmem knowledge base (project="main"):

```
$ACA_DATA/  (e.g., ~/writing/data/)
│
│   # Session start (@ syntax in CLAUDE.md auto-loads)
├── ACCOMMODATIONS.md        # Work style requirements
├── CORE.md                  # User context, tools, paths
├── STYLE-QUICK.md           # Writing style reference
├── STYLE.md                 # Full guide (not @-loaded)
│
├── tasks/                   # Task data (bmem markdown)
│   ├── active/              # Active tasks
│   ├── completed/           # Completed tasks
│   └── deferred/            # Deferred tasks
│
├── sessions/                # Session logs
│   └── claude/              # Claude Code transcripts
│       └── YYYYMMDD-<slug>.md  # Daily session transcripts
│
├── projects/
│   └── aops/                # academicOps project
│       ├── VISION.md        # End state vision
│       ├── ROADMAP.md       # Maturity stages 0-5
│       ├── STATE.md         # Current state
│       ├── specs/           # Task specifications
│       └── experiments/     # Experiment logs
│           └── LOG.md       # Learning patterns (append-only)
│
└── [bmem entities]          # People, orgs, concepts, etc.
```

---

## Framework Cache (~/.cache/aops/)

Hook-generated data:

```
~/.cache/aops/
├── prompt-router/           # Prompt analysis for classifier
│   └── YYYYMMDD_HHMMSS_*.json  # Timestamped prompt logs
├── sessions/                # Hook execution logs
│   └── YYYY-MM-DD-<hash>-hooks.jsonl  # Per-session hook logs
└── session_end_*.flag       # Session termination markers

/tmp/claude-transcripts/     # On-demand transcripts
└── *_transcript.md          # Generated session transcripts
```

---

## Knowledge Base (bmem)

**Project**: Always use `project="main"` with all `mcp__bmem__*` tools.

**Location**: `$ACA_DATA` (single knowledge base per user, shared across projects).

**Key principles**:
1. Single source of truth - all notes in one place
2. Write location invariant - bmem writes to `$ACA_DATA` regardless of cwd
3. Format - Markdown with YAML frontmatter
4. Access - MCP server + `mcp__bmem__*` function tools

**CLI**: `uvx basic-memory --help`. See `skills/bmem/SKILL.md` for operations.

---

## Installation

Run `bash setup.sh` to create symlinks in `~/.claude/` pointing to `$AOPS`.

Each project gets `.claude/CLAUDE.md` with `@` references:

```
project-repo/
├── .claude/
│   ├── CLAUDE.md            # @ syntax loads ACCOMMODATIONS, CORE, etc.
│   ├── skills/   → symlink  # Symlink to $AOPS/skills/
│   ├── hooks/    → symlink  # Symlink to $AOPS/hooks/
│   └── commands/ → symlink  # Symlink to $AOPS/commands/
└── ...                      # Project files
```

---

## Contact

**Author**: Nic Suzor
**Email**: nic@suzor.com
**Repository**: github.com/yourusername/academicOps (update this)
