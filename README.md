# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## academicOps Repository Structure

**Note**: User-specific files (ACCOMMODATIONS, CORE, STYLE, VISION, ROADMAP) live in `$ACA_DATA`, not in this repository. This repo contains only generic framework infrastructure.

### High-Level Overview

```
$AOPS/
├── AXIOMS.md                # Framework principles (auto-injected via SessionStart hook)
├── README.md                # THIS FILE - framework directory map
├── CLAUDE.md                # Framework repo session start instructions
├── BMEM-ARCHITECTURE.md     # bmem system architecture
├── BMEM-FORMAT.md           # bmem markdown format specification
├── BMEM-CLAUDE-GUIDE.md     # Using bmem from Claude Code
├── BMEM-OBSIDIAN-GUIDE.md   # Using bmem with Obsidian
├── pyproject.toml           # Python project configuration
├── setup.sh                 # Framework installation script
├── update_hooks.py          # Hook update utility
├── __init__.py
├── .gitignore
│
├── .github/workflows/       # GitHub Actions workflows
│   ├── beta-release.yml
│   ├── claude-code-review.yml
│   ├── claude.yml
│   ├── ios-note-capture.yml
│   └── test-setup.yml
│
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── README.md            # Skills documentation and index
│   ├── analyst/             # Data analysis (dbt, Streamlit, statistical methods)
│   ├── bmem/                # Knowledge base operations
│   ├── docs-update/         # Documentation update and verification
│   ├── excalidraw/          # Visual diagram generation
│   ├── extractor/           # Archive extraction
│   ├── feature-dev/         # Feature development workflow
│   ├── framework/           # Framework maintenance and strategic partner
│   ├── framework-debug/     # Framework debugging tools
│   ├── pdf/                 # PDF generation from markdown
│   ├── python-dev/          # Production Python development standards
│   ├── skill-creator/       # Skill creation and packaging
│   ├── tasks/               # Task management system (MCP server)
│   └── training-set-builder/ # Training data extraction from documents
│
├── hooks/                   # Lifecycle automation (Python scripts)
│   ├── README.md
│   ├── sessionstart_load_axioms.py      # SessionStart - inject AXIOMS.md
│   ├── user_prompt_submit.py            # UserPromptSubmit - inject context
│   ├── log_session_stop.py              # SessionStop - log session activity
│   ├── extract_session_knowledge.py     # Knowledge extraction
│   ├── session_logger.py                # Session logging module
│   ├── autocommit_state.py
│   ├── hook_debug.py
│   ├── hook_logger.py
│   ├── log_posttooluse.py
│   ├── log_pretooluse.py
│   ├── log_sessionstart.py
│   ├── log_subagentstop.py
│   ├── log_userpromptsubmit.py
│   ├── prompt_router.py
│   ├── request_scribe.py
│   ├── test_marker_hook.py
│   └── prompts/             # Markdown prompts loaded by hooks
│
├── commands/                # Slash commands (workflow triggers)
│   ├── archive-extract.md   # Extract archived information
│   ├── bmem.md              # Invoke bmem skill
│   ├── email.md             # Extract tasks from emails
│   ├── learn.md             # Update memory/instructions
│   ├── log.md               # Log agent performance
│   ├── meta.md              # Invoke framework skill
│   ├── parallel-batch.md    # Parallel batch processing
│   ├── strategy.md          # Strategic planning
│   ├── task-viz.md          # Generate task visualization
│   ├── transcript.md        # Generate session transcript
│   └── ttd.md               # Test-driven development orchestration
│
├── agents/                  # Agentic workflows
│   ├── dev.md               # Development task routing
│   ├── email-extractor.md   # Email archive processing
│   ├── log-agent.md         # Agent performance logging
│   └── task-viz.md          # Task visualization generation
│
├── experiments/             # Temporary experiment logs
│   ├── 2025-11-17_log-sufficiency-test.md
│   ├── 2025-11-17_multi-window-cognitive-load-solutions.md
│   ├── 2025-11-21_zotmcp-tdd-session.md
│   ├── session-bmem-fail.md
│   └── session-bmem-pass.md
│
├── scripts/                 # Deployment and maintenance scripts
│   ├── migrate_log_entries.py
│   ├── package_deployment.py
│   └── setup.sh
│
├── lib/                     # Shared Python utilities
│   ├── __init__.py
│   └── paths.py             # Path resolution (SSoT for paths)
│
├── tests/                   # Framework tests (pytest)
│   ├── README.md
│   ├── conftest.py
│   ├── paths.py
│   ├── run_integration_tests.py
│   ├── run_skill_tests.sh
│   ├── test_*.py            # Unit tests (30+ test files)
│   ├── integration/         # E2E tests (slow, require Claude execution)
│   └── tools/               # Test utilities
│
└── config/                  # Configuration files
    └── claude/
        ├── mcp.json         # MCP server configuration
        └── settings.json    # Claude Code settings
```

### Framework State (Authoritative)

**Current phase**: Production use with active development

**Component counts**:
- 13 skills (analyst, bmem, docs-update, excalidraw, extractor, feature-dev, framework, framework-debug, pdf, python-dev, skill-creator, tasks, training-set-builder)
- 15 hooks (SessionStart, UserPromptSubmit, SessionStop, logging hooks, etc.)
- 11 commands (/bmem, /meta, /ttd, /email, /log, etc.)
- 4 agents (dev, email-extractor, log-agent, task-viz)
- 5 GitHub Actions workflows
- 60+ tests (unit and integration)

**File structure**: See "High-Level Overview" section above for directory layout.

### Key Skills

**framework** (`skills/framework/`): Strategic partner for framework development decisions. Consult before adding/modifying framework components.

**Skills Overview (Full List):**
```
skills/
├── README.md                      # Skills documentation and index
├── analyst/                       # Data analysis (dbt, Streamlit, statistical methods)
├── bmem/                          # Knowledge base operations
├── docs-update/                   # Documentation update and verification
├── excalidraw/                    # Visual diagram generation
├── extractor/                     # Archive extraction
├── feature-dev/                   # Feature development workflow
├── framework/                     # Framework maintenance and strategic partner
├── framework-debug/               # Framework debugging tools
├── pdf/                           # PDF generation from markdown
├── python-dev/                    # Production Python development standards
├── skill-creator/                 # Skill creation and packaging
├── tasks/                         # Task management system (MCP server)
└── training-set-builder/          # Training data extraction from documents
```

---

### Claude Code Debug Locations

```
~/.claude/
├── debug/               # Human-readable session logs (session-id.txt, [ERROR]/[DEBUG]/[INFO] tagged)
├── projects/            # JSONL session data per repository
│   └── -repo-path/      # Path encoded with dashes (e.g., -home-nic-writing/)
│       ├── *.jsonl      # Main session messages (user/assistant turns)
│       └── agent-*.jsonl # Agent subprocess logs (tool calls, results, errors with is_error flag)
├── settings.json        # User settings (hooks, permissions, deny rules)
└── statsig/             # Feature flags and telemetry

/tmp/claude-sessions/
└── *-hooks.jsonl        # Hook execution logs (which hooks fired, inputs, hook_results)

/tmp/claude-transcripts/
└── *_transcript.md        # Human-readable session transcripts (on-demand via claude-transcript)
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
