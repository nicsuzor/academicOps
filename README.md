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
├── BMEM-*.md                # bmem documentation (architecture, format, guides)
├── pyproject.toml
├── setup.sh                 # Creates ~/.claude/ symlinks
├── update_hooks.py
│
├── .github/workflows/
│
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── README.md
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
│   └── training-set-builder/
│
├── hooks/                   # Lifecycle automation (Python)
│   ├── README.md
│   │
│   │   # Active hooks (configured in settings.json)
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md at session start
│   ├── user_prompt_submit.py        # Injects context on every prompt
│   ├── prompt_router.py             # Keyword analysis → skill suggestions
│   ├── autocommit_state.py          # Auto-commit data/ after state changes
│   ├── log_session_stop.py          # Session activity logging
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
│   ├── extract_session_knowledge.py
│   ├── request_scribe.py            # Session documentation requests
│   ├── test_marker_hook.py          # CI test hook
│   │
│   └── prompts/                     # Markdown loaded by hooks
│
├── commands/                # Slash commands
│   ├── archive-extract.md
│   ├── bmem.md
│   ├── docs-update.md
│   ├── email.md
│   ├── learn.md
│   ├── log.md
│   ├── meta.md              # Invoke framework skill
│   ├── parallel-batch.md
│   ├── qa.md
│   ├── strategy.md
│   ├── task-viz.md
│   ├── transcript.md
│   └── ttd.md               # TDD orchestration
│
├── agents/                  # Agentic workflows (thin routing wrappers)
│   ├── dev.md
│   ├── email-extractor.md
│   ├── log-agent.md
│   └── task-viz.md
│
├── experiments/             # Temporary experiment logs
│
├── scripts/                 # Deployment scripts
│
├── lib/                     # Shared Python
│   ├── activity.py
│   └── paths.py             # Path resolution (SSoT)
│
├── tests/                   # pytest suite
│   ├── README.md
│   ├── conftest.py
│   ├── test_*.py
│   ├── integration/         # E2E tests (slow)
│   └── tools/
│
└── config/claude/           # Reference config (copied during install)
    ├── mcp.json
    └── settings.json
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
│   └── YYYY-MM-DD_HH-MM-SS.md
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
