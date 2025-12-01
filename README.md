# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## Framework Repository Structure ($AOPS)

```
$AOPS/
├── AXIOMS.md                # Framework principles (injected at session start)
├── README.md                # THIS FILE
├── CLAUDE.md                # Framework repo instructions (@ syntax auto-loads)
├── BMEM-ARCHITECTURE.md     # bmem system architecture
├── BMEM-FORMAT.md           # bmem markdown format specification
├── BMEM-CLAUDE-GUIDE.md     # Using bmem from Claude Code
├── BMEM-OBSIDIAN-GUIDE.md   # Using bmem with Obsidian
├── pyproject.toml
├── uv.lock
├── setup.sh                 # Creates ~/.claude/ symlinks
├── .gitignore
├── __init__.py
│
├── .github/workflows/       # CI/CD (beta-release, code-review, tests)
│
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── README.md            # Skill catalog and usage
│   ├── analyst/             # Data analysis (dbt, Streamlit, statistics)
│   ├── bmem/                # Knowledge base ops (project="main")
│   ├── dashboard/           # Live task dashboard (Streamlit, auto-refresh, mobile)
│   ├── docs-update/         # Documentation validation
│   ├── excalidraw/          # Visual diagram generation
│   ├── extractor/           # Archive extraction → bmem
│   ├── feature-dev/         # Feature development workflow
│   ├── framework/           # Framework maintenance (strategic partner)
│   ├── framework-debug/     # Framework debugging
│   ├── pdf/                 # Markdown → PDF
│   ├── python-dev/          # Production Python standards
│   ├── skill-creator/       # Skill packaging
│   ├── tasks/               # Task management (MCP server)
│   └── training-set-builder/# Training data extraction
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
│
├── commands/                # Slash commands (main agent executes directly)
│   ├── advocate.md          # Framework oversight with epistemic standards
│   ├── archive-extract.md   # Extract archived info to bmem
│   ├── bmem.md              # Capture session info to knowledge base
│   ├── docs-update.md       # Update README.md structure
│   ├── email.md             # Email → task extraction
│   ├── learn.md             # Minor instruction adjustments
│   ├── log.md               # Log agent performance patterns
│   ├── meta.md              # Invoke framework skill
│   ├── parallel-batch.md    # Parallel file processing
│   ├── qa.md                # Quality assurance verification
│   ├── strategy.md          # Strategic planning
│   ├── task-viz.md          # Task visualization
│   ├── transcript.md        # Session transcript generation
│   └── ttd.md               # TDD orchestration
│
├── agents/                  # Spawnable subagents (Task tool with subagent_type)
│   ├── bmem-validator.md    # Fix bmem validation errors
│   ├── dev.md               # Development task routing
│   ├── email-extractor.md   # Email archive processing
│   ├── log-agent.md         # Performance pattern logging
│   └── task-viz.md          # Task graph visualization
│
├── experiments/             # Temporary experiment logs
│
├── scripts/                 # Deployment and utility scripts
│   ├── setup.sh             # Project setup script
│   ├── package_deployment.py# Skill packaging
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
│   ├── conftest.py          # Fixtures
│   ├── test_*.py            # Unit tests
│   ├── integration/         # E2E tests (slow)
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
