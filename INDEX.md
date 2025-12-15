# Framework Index

Complete file-to-function mapping. For overview, see README.md.

## File Tree

```
$AOPS/
├── AXIOMS.md                    # Inviolable principles (injected at session start)
├── HEURISTICS.md                # Empirically validated rules (injected at session start)
├── FRAMEWORK.md                 # Resolved paths for this session (injected at session start)
├── README.md                    # Brief overview, feature inventory
├── INDEX.md                     # THIS FILE - complete file tree
├── RULES.md                     # Current enforcement rules (auto-generated)
├── CLAUDE.md                    # Repo instructions (@ syntax auto-loads)
├── BMEM-*.md                    # bmem documentation (4 files)
├── pyproject.toml               # Python project config
│
├── commands/                    # Slash commands (main agent executes)
│   ├── meta.md                  # Strategic brain + executor → framework, python-dev skills
│   ├── log.md                   # → learning-log skill
│   ├── transcript.md            # → transcript skill
│   ├── bmem.md                  # → bmem skill
│   ├── email.md                 # Email → task extraction
│   ├── learn.md                 # Minor instruction adjustments
│   ├── qa.md                    # Quality assurance verification
│   ├── ttd.md                   # TDD orchestration
│   ├── parallel-batch.md        # Parallel file processing
│   ├── strategy.md              # Strategic planning
│   └── task-viz.md              # Task graph visualization
│
├── skills/
│   ├── framework/               # Convention reference for infrastructure
│   │   ├── SKILL.md             # Paths, patterns, anti-bloat rules
│   │   ├── references/          # 9 guides (hooks, testing, MCP, etc.)
│   │   ├── workflows/           # 6 workflows (design, debug, experiment)
│   │   └── scripts/validate_docs.py
│   │
│   ├── learning-log/            # Pattern logging to thematic files
│   │   └── SKILL.md             # → may invoke transcript skill
│   │
│   ├── transcript/              # Session JSONL → markdown
│   │   └── SKILL.md             # Wraps scripts/claude_transcript.py
│   │
│   ├── python-dev/              # Production Python standards
│   │   ├── SKILL.md             # Fail-fast, types, TDD
│   │   └── references/          # 10 guides (pandas, FastAPI, testing)
│   │
│   ├── analyst/                 # Data analysis (dbt, Streamlit, stats)
│   │   ├── SKILL.md
│   │   ├── _CHUNKS/             # 9 workflow chunks
│   │   ├── references/          # 12 statistical guides
│   │   └── scripts/assumption_checks.py
│   │
│   ├── bmem/                    # Knowledge base operations
│   │   ├── SKILL.md             # Always project="main"
│   │   └── references/          # 5 guides (format, quality, Obsidian)
│   │
│   ├── tasks/                   # Task management (MCP server)
│   │   ├── SKILL.md
│   │   ├── server.py            # MCP server implementation
│   │   ├── models.py            # Task data models
│   │   ├── scripts/             # CLI: task_add, task_update, task_archive, task_view, task_viz
│   │   └── workflows/email-capture.md
│   │
│   ├── pdf/                     # Markdown → PDF
│   │   ├── SKILL.md
│   │   ├── scripts/generate_pdf.py
│   │   └── assets/              # CSS styles, Roboto fonts
│   │
│   ├── excalidraw/              # Visual diagram generation
│   │   ├── SKILL.md
│   │   ├── references/          # 10 guides (JSON format, layouts)
│   │   └── libraries/           # Icon libraries
│   │
│   │
│   ├── skill-creator/           # Skill packaging
│   │   ├── SKILL.md
│   │   └── scripts/             # init_skill, package_skill, quick_validate
│   │
│   ├── dashboard/               # Live task dashboard (Streamlit)
│   │   ├── SKILL.md
│   │   └── dashboard.py
│   │
│   ├── extractor/               # Archive → bmem extraction
│   ├── feature-dev/             # Feature development templates
│   ├── framework-debug/         # Framework debugging
│   └── training-set-builder/    # Training data extraction
│
├── hooks/                       # Session lifecycle (Python)
│   ├── CLAUDE.md                    # Hook design principles (JIT context)
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md
│   ├── user_prompt_submit.py        # Context injection per prompt
│   ├── prompt_router.py             # Keyword → skill suggestions
│   ├── autocommit_state.py          # Auto-commit data/ changes
│   ├── session_logger.py            # Log file path management
│   ├── hook_logger.py               # Centralized event logging
│   ├── hook_debug.py                # Hook debugging
│   ├── request_scribe.py            # Request logging
│   ├── log_*.py                     # Event logging (6 files)
│   └── prompts/user-prompt-submit.md
│
├── agents/                      # Spawnable subagents (Task tool)
│   ├── dev.md                   # → python-dev skill
│   ├── bmem-validator.md        # Parallel bmem validation
│   ├── email-extractor.md       # Email archive processing
│   └── task-viz.md              # Task graph → Excalidraw
│
├── scripts/                     # Utility scripts
│   ├── claude_transcript.py     # Session JSONL → markdown
│   ├── setup.sh                 # Creates ~/.claude/ symlinks
│   ├── package_deployment.py    # Skill packaging
│   ├── measure_router_compliance.py
│   ├── migrate_log_entries.py   # Log entry migration
│   ├── transcribe_recording.sh  # Recording transcription
│   └── extract_session_knowledge.py  # DEPRECATED (use /log, /bmem)
│
├── lib/                         # Shared Python
│   ├── paths.py                 # Path resolution (SSoT)
│   ├── session_reader.py        # Unified session parser (JSONL + agents + hooks)
│   └── activity.py              # Activity logging
│
├── tests/                       # pytest suite
│   ├── conftest.py              # Fixtures
│   ├── integration/             # E2E tests
│   └── tools/                   # Tool-specific tests
│
├── experiments/                 # Experiment logs (6 files)
│
└── config/claude/               # Reference config
    ├── mcp.json                 # MCP server configuration
    └── settings.json            # Claude Code settings
```

## Cross-References

### Command → Skill Invocations

| Command | Invokes Skill |
|---------|---------------|
| /meta | framework, python-dev |
| /log | learning-log |
| /transcript | transcript |
| /bmem | bmem |

### Skill → Skill Dependencies

| Skill | May Invoke |
|-------|------------|
| learning-log | transcript (when given session JSONL) |
| transcript | (none - wraps script) |

### Agent → Skill Routing

| Agent | Routes To |
|-------|-----------|
| dev | python-dev |
| bmem-validator | bmem |

## User Data ($ACA_DATA)

```
$ACA_DATA/
├── ACCOMMODATIONS.md            # Work style (binding)
├── CORE.md                      # User context, tools
├── STYLE*.md                    # Writing style
├── tasks/                       # Task data (active/, completed/, deferred/)
├── sessions/claude/             # Session transcripts
└── projects/aops/
    ├── VISION.md                # End state
    ├── ROADMAP.md               # Maturity stages
    ├── STATE.md                 # Current state
    └── learning/                # Thematic pattern files
```

## Runtime (~/.claude/)

```
~/.claude/
├── skills/      → $AOPS/skills/     (symlink)
├── hooks/       → $AOPS/hooks/      (symlink)
├── commands/    → $AOPS/commands/   (symlink)
├── agents/      → $AOPS/agents/     (symlink)
├── settings.json                    # User settings
├── projects/                        # Session JSONL per repo
└── debug/                           # Hook output logs
```
