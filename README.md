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
├── .gitignore
├── __init__.py
│
├── .github/workflows/       # CI/CD
│   ├── beta-release.yml     # Beta release automation
│   ├── claude-code-review.yml # Claude-powered code review
│   ├── claude.yml           # General Claude integration
│   ├── ios-note-capture.yml # iOS note capture workflow
│   └── test-setup.yml       # Test environment setup
│
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── README.md            # Skill catalog with descriptions
│   ├── analyst/             # Data analysis (dbt, Streamlit, stats)
│   │   ├── SKILL.md
│   │   ├── _CHUNKS/         # Skill documentation chunks
│   │   ├── references/      # Statistical analysis guides
│   │   │   ├── assumptions_and_diagnostics.md  # Test assumptions
│   │   │   ├── bayesian_statistics.md          # Bayesian methods
│   │   │   ├── context-discovery.md            # Finding analysis context
│   │   │   ├── dbt-workflow.md                 # dbt transformation patterns
│   │   │   ├── effect_sizes_and_power.md       # Power analysis
│   │   │   ├── matplotlib.md                   # Matplotlib viz patterns
│   │   │   ├── reporting_standards.md          # Statistical reporting
│   │   │   ├── seaborn.md                      # Seaborn viz patterns
│   │   │   ├── statistical-analysis.md         # Core stat methods
│   │   │   ├── statsmodels.md                  # Statsmodels usage
│   │   │   ├── streamlit.md                    # Streamlit basics
│   │   │   ├── streamlit-patterns.md           # Dashboard design patterns
│   │   │   └── test_selection_guide.md         # Choosing stat tests
│   │   └── scripts/
│   │       └── assumption_checks.py  # Statistical assumption validation
│   │
│   ├── bmem/                # Knowledge base ops (project="main")
│   │   ├── SKILL.md
│   │   └── references/      # bmem writing guides
│   │       ├── approved-categories-relations.md  # Valid entity categories
│   │       ├── detail-level-guide.md             # Detail vs summary
│   │       ├── observation-quality-guide.md      # Quality standards
│   │       ├── obsidian-compatibility.md         # Obsidian integration
│   │       └── obsidian-format-spec.md           # Format specification
│   │
│   ├── dashboard/           # Live task dashboard (Streamlit, auto-refresh)
│   │   ├── SKILL.md
│   │   └── dashboard.py     # Task dashboard implementation
│   │
│   ├── docs-update/         # Documentation validation and updates
│   │   └── SKILL.md
│   │
│   ├── excalidraw/          # Visual diagram generation
│   │   ├── SKILL.md
│   │   ├── libraries/       # Excalidraw icon libraries
│   │   ├── references/      # Excalidraw documentation
│   │   │   ├── graph-layouts.md           # Graph layout algorithms
│   │   │   ├── icon-integration.md        # Using icon libraries
│   │   │   ├── json-format.md             # Excalidraw JSON spec
│   │   │   ├── library-guide.md           # Library usage guide
│   │   │   ├── mcp-server-setup.md        # MCP server config
│   │   │   ├── mind-mapping-principles.md # Mind map design
│   │   │   ├── productivity-tips.md       # Productivity patterns
│   │   │   ├── technical-details.md       # Technical implementation
│   │   │   ├── text-container-pattern.md  # Text container design
│   │   │   └── theme-colors.md            # Color scheme guide
│   │   └── scripts/         # Task visualization scripts (moved from framework/)
│   │       ├── generate_task_viz.py  # JSON → Excalidraw format
│   │       ├── layout_task_graph.py  # DEPRECATED - use task_viz_layout.py
│   │       └── task_viz_layout.py    # Force-directed graph layout (networkx)
│   │
│   ├── extractor/           # Archive extraction → bmem
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── tests/
│   │
│   ├── feature-dev/         # Feature development workflow
│   │   ├── SKILL.md
│   │   └── templates/       # Development templates
│   │
│   ├── framework/           # Framework maintenance (strategic partner)
│   │   ├── SKILL.md
│   │   ├── TASK-SPEC-TEMPLATE.md
│   │   ├── references/      # Framework development guides
│   │   │   ├── basic-memory-ai-guide.md    # bmem AI usage patterns
│   │   │   ├── basic-memory-mcp-tools.md   # bmem MCP tool reference
│   │   │   ├── basic-memory-sync-guide.md  # bmem sync patterns
│   │   │   ├── claude-code-config.md       # Claude Code configuration
│   │   │   ├── e2e-test-harness.md         # End-to-end testing
│   │   │   ├── hooks_guide.md              # Hook development guide
│   │   │   ├── script-design-guide.md      # Python script design
│   │   │   ├── strategic-partner-mode.md   # Framework skill mode
│   │   │   └── testing-with-live-data.md   # Live data testing
│   │   ├── scripts/
│   │   │   └── validate_docs.py  # Documentation validation
│   │   ├── specs/           # Task specifications
│   │   ├── tests/           # Framework integration tests
│   │   └── workflows/       # Framework workflow guides
│   │       ├── 01-design-new-component.md
│   │       ├── 02-debug-framework-issue.md
│   │       ├── 03-experiment-design.md
│   │       ├── 04-monitor-prevent-bloat.md
│   │       ├── 05-review-pull-request.md
│   │       └── 06-develop-specification.md
│   │
│   ├── framework-debug/     # Framework debugging
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── errors.jq    # JQ script for error extraction
│   │
│   ├── pdf/                 # Markdown → PDF conversion
│   │   ├── SKILL.md
│   │   ├── assets/          # PDF styling and fonts
│   │   └── scripts/
│   │       └── generate_pdf.py  # PDF generation script
│   │
│   ├── python-dev/          # Production Python standards
│   │   ├── SKILL.md
│   │   └── references/      # Python development guides
│   │       ├── bigquery.md      # BigQuery best practices
│   │       ├── code-quality.md  # Code quality standards
│   │       ├── fail-fast.md     # Fail-fast principles
│   │       ├── fastapi.md       # FastAPI patterns
│   │       ├── fastmcp.md       # FastMCP server development
│   │       ├── hydra.md         # Hydra configuration
│   │       ├── modern-python.md # Modern Python patterns
│   │       ├── pandas.md        # Pandas best practices
│   │       ├── testing.md       # Testing standards
│   │       └── type-safety.md   # Type safety enforcement
│   │
│   ├── skill-creator/       # Skill packaging
│   │   ├── SKILL.md
│   │   ├── LICENSE.txt
│   │   └── scripts/
│   │       ├── init_skill.py      # Initialize new skill
│   │       ├── package_skill.py   # Package skill for distribution
│   │       └── quick_validate.py  # Quick skill validation
│   │
│   ├── tasks/               # Task management (MCP server)
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── models.py        # Task data models
│   │   ├── server.py        # MCP server implementation
│   │   ├── task_loader.py   # Task loading logic
│   │   ├── task_ops.py      # Task operations
│   │   ├── scripts/
│   │   │   ├── task_add.py     # Add new task
│   │   │   ├── task_archive.py # Archive completed tasks
│   │   │   ├── task_update.py  # Update task status/metadata
│   │   │   └── task_view.py    # View task details
│   │   ├── tests/
│   │   └── workflows/       # Task workflow guides
│   │
│   └── training-set-builder/  # Training data extraction
│       └── SKILL.md
│
├── hooks/                   # Lifecycle automation (Python)
│   ├── README.md            # Hook documentation
│   │
│   │   # Active hooks (configured in settings.json)
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md at session start
│   ├── user_prompt_submit.py        # Injects context on every prompt
│   ├── prompt_router.py             # Keyword analysis → skill suggestions
│   ├── autocommit_state.py          # Auto-commit data/ after state changes
│   │
│   │   # Shared modules
│   ├── session_logger.py            # Log file path management
│   ├── hook_logger.py               # Centralized event logging
│   ├── hook_debug.py                # Debug utilities
│   │
│   │   # Event loggers (→ ~/.cache/aops/sessions/)
│   ├── log_sessionstart.py
│   ├── log_userpromptsubmit.py
│   ├── log_pretooluse.py
│   ├── log_posttooluse.py
│   ├── log_subagentstop.py
│   │
│   │   # Experimental
│   ├── extract_session_knowledge.py # Knowledge extraction from sessions
│   ├── request_scribe.py            # Session documentation requests
│   ├── session_env_setup.sh         # Environment setup script
│   ├── test_marker_hook.py          # CI test hook
│   │
│   └── prompts/                     # Markdown loaded by hooks
│       └── user-prompt-submit.md
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
│   ├── log-agent.md         # Performance pattern logging agent
│   └── task-viz.md          # Task graph visualization (bmem → excalidraw)
│
├── experiments/             # Temporary experiment logs
│   ├── 2025-11-17_log-sufficiency-test.md
│   ├── 2025-11-17_multi-window-cognitive-load-solutions.md
│   ├── 2025-11-21_zotmcp-tdd-session.md
│   ├── 2025-12-01_discoverability-annotations.md
│   ├── session-bmem-fail.md
│   └── session-bmem-pass.md
│
├── scripts/                 # Deployment and utility scripts
│   ├── setup.sh             # Project setup script
│   ├── package_deployment.py        # Skill packaging
│   ├── measure_router_compliance.py # Prompt router analysis
│   └── migrate_log_entries.py       # Log migration utility
│
├── lib/                     # Shared Python
│   ├── __init__.py
│   ├── activity.py          # Activity logging
│   └── paths.py             # Path resolution (SSoT)
│
├── tests/                   # pytest suite
│   ├── README.md            # Test documentation
│   ├── HOOK_TEST_PROTOCOL.md
│   ├── conftest.py          # Fixtures
│   ├── test_*.py            # Unit tests
│   ├── integration/         # E2E tests (slow)
│   │   ├── README_SKILL_TESTS.md
│   │   └── test_*.py
│   └── tools/               # Tool-specific tests
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
│   ├── active/
│   ├── completed/
│   └── deferred/
│
├── sessions/                # Session logs
│   └── claude/              # Claude Code transcripts
│       └── YYYYMMDD-<slug>.md
│
├── projects/
│   └── aops/                # academicOps project
│       ├── VISION.md        # End state vision
│       ├── ROADMAP.md       # Maturity stages 0-5
│       ├── STATE.md         # Current state
│       ├── specs/           # Task specifications
│       └── experiments/
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
│   └── YYYYMMDD_HHMMSS_*.json
├── sessions/                # Hook execution logs
│   └── YYYY-MM-DD-<hash>-hooks.jsonl
└── session_end_*.flag       # Session termination markers

/tmp/claude-transcripts/     # On-demand transcripts
└── *_transcript.md
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
│   ├── skills/   → symlink
│   ├── hooks/    → symlink
│   └── commands/ → symlink
└── ...
```
