---
name: index
title: Framework Index
type: reference
description: Complete file-to-function mapping and directory structure reference.
permalink: framework-index
tags:
  - framework
  - structure
  - reference
---

# Framework Index

Complete file-to-function mapping. For overview, see [[README]].

## File Tree

```
$AOPS/
├── [[AXIOMS.md]]                # Inviolable principles (injected at session start)
├── [[HEURISTICS.md]]            # Empirically validated rules (injected at session start)
├── [[FRAMEWORK.md]]             # Resolved paths for this session (injected at session start)
├── [[README.md]]                # Brief overview, feature inventory
├── [[INDEX.md]]                 # THIS FILE - complete file tree
├── [[RULES.md]]                 # Current enforcement rules (auto-generated)
├── [[CLAUDE.md]]                # Repo instructions (@ syntax auto-loads)
├── [[AGENTS.md]]                # Agent context (shared by all agents)
├── [[GEMINI.md]]                # Gemini MCP integration guide
├── pyproject.toml               # Python project config
├── setup.sh                     # Main installation script
├── install.sh                   # Alternative installer
├── reference-graph.json         # Framework reference graph (generated)
│
├── commands/                    # Slash commands (main agent executes)
│   ├── add.md                   # Quick-add task from context
│   ├── aops.md                  # Show framework capabilities
│   ├── audit.md                 # → audit skill (framework governance)
│   ├── consolidate.md           # Consolidate learning-log entries
│   ├── diag.md                  # Quick diagnostic of session state
│   ├── do.md                    # Execute with context enrichment + guardrails
│   ├── email.md                 # Email → task extraction
│   ├── learn.md                 # Minor instruction adjustments
│   ├── log.md                   # → learning-log skill
│   ├── meta.md                  # Strategic brain + executor
│   ├── parallel-batch.md        # Parallel file processing
│   ├── qa.md                    # Quality assurance verification
│   ├── review-training-cmd.md   # Process review/source pairs
│   ├── strategy.md              # Strategic thinking partner
│   ├── supervise.md             # → hypervisor agent
│   ├── task-viz.md              # Task graph visualization
│   └── ttd.md                   # TDD orchestration
│
├── skills/
│   ├── framework/               # Convention reference for infrastructure
│   │   ├── SKILL.md             # Paths, patterns, anti-bloat rules
│   │   ├── references/          # 5 guides (hooks, config, testing, scripts, strategic)
│   │   ├── workflows/           # 5 workflows (design, debug, experiment, bloat, spec)
│   │   ├── tests/               # Framework-specific tests
│   │   ├── TASK-SPEC-TEMPLATE.md
│   │   └── scripts/validate_docs.py
│   │
│   ├── learning-log/            # Pattern logging to thematic files
│   │   └── SKILL.md             # → may invoke transcript skill
│   │
│   ├── transcript/              # Session JSONL → markdown
│   │   └── SKILL.md             # Wraps scripts/claude_transcript.py
│   │
│   ├── session-insights/        # Accomplishments + learning extraction
│   │   ├── SKILL.md             # Orchestrates transcripts, daily summary, Gemini mining
│   │   ├── mining-prompt.md     # Gemini extraction prompt template
│   │   └── scripts/find_sessions.py  # Session file discovery
│   │
│   ├── python-dev/              # Production Python standards
│   │   ├── SKILL.md             # Fail-fast, types, TDD
│   │   └── references/          # 10 guides (pandas, FastAPI, testing)
│   │
│   ├── analyst/                 # Data analysis (dbt, Streamlit, stats)
│   │   ├── SKILL.md
│   │   ├── instructions/        # 9 workflow instructions
│   │   ├── references/          # 12 statistical guides
│   │   └── scripts/assumption_checks.py
│   │
│   ├── remember/                # Memory server operations
│   │   ├── SKILL.md             # Write & retrieve from memory server
│   │   ├── references/          # Format specs, quality guides
│   │   └── workflows/           # capture, validate, prune
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
│   ├── dashboard/               # Live task dashboard (Streamlit)
│   │   ├── SKILL.md
│   │   └── dashboard.py
│   │
│   ├── reference-map/           # Framework reference graph extraction
│   │   ├── SKILL.md
│   │   └── scripts/build_reference_map.py
│   │
│   ├── link-audit/              # Reference graph analysis
│   │   ├── SKILL.md
│   │   └── scripts/find_orphans.py
│   │
│   ├── audit/                   # Framework governance audit
│   │   └── SKILL.md
│   │
│   ├── extractor/               # Archive → memory extraction
│   ├── feature-dev/             # Feature development templates
│   ├── framework-debug/         # Framework debugging
│   ├── framework-review/        # Transcript analysis for improvements
│   ├── garden/                  # Incremental PKM maintenance
│   ├── ground-truth/            # Ground truth label management
│   ├── osb-drafting/            # IRAC analysis for OSB cases
│   ├── review-training/         # Training data from reviews
│   ├── supervisor/              # Multi-agent workflow orchestration
│   ├── task-expand/             # Intelligent task breakdown
│   └── training-set-builder/    # Training data extraction
│
├── hooks/                       # Session lifecycle (Python)
│   ├── CLAUDE.md                    # Hook design principles (JIT context)
│   ├── hooks.md                     # Hook inventory and descriptions
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md, FRAMEWORK.md, HEURISTICS.md
│   ├── user_prompt_submit.py        # Context injection per prompt
│   ├── router.py                    # Central hook dispatcher
│   ├── autocommit_state.py          # Auto-commit data/ changes
│   ├── policy_enforcer.py           # Block destructive operations (PreToolUse)
│   ├── session_logger.py            # Log file path management
│   ├── hook_logger.py               # Centralized event logging
│   ├── unified_logger.py            # Universal event logger
│   ├── hook_debug.py                # Hook debugging
│   ├── request_scribe.py            # Memory reminder (PostToolUse)
│   ├── terminal_title.py            # Set terminal title
│   ├── marker_hook.py               # Test hook for verification
│   ├── verify_conclusions.py        # Disabled stub
│   └── prompts/
│       ├── user-prompt-submit.md    # Context for UserPromptSubmit hook
│       └── memory-reminder.md       # PostToolUse memory prompt
│
├── agents/                      # Spawnable subagents (Task tool)
│   ├── critic.md                # Second-opinion review of plans/conclusions
│   ├── effectual-planner.md     # Effectual planning (Sarasvathy) - plans as hypotheses
│   ├── hypervisor.md            # Multi-step workflow orchestrator (phases 0-5)
│   ├── intent-router.md         # LLM intent classifier (Haiku)
│   └── planner.md               # Implementation planning with memory + critic review
│
├── scripts/                     # Utility scripts
│   ├── scripts.md               # Script inventory and documentation
│   ├── claude_transcript.py     # Session JSONL → markdown
│   ├── package_deployment.py    # Skill packaging
│   ├── measure_router_compliance.py  # Router performance metrics
│   ├── migrate_log_entries.py   # Log entry migration
│   ├── regenerate_task_index.py # Task index regeneration
│   ├── remove_relation_sections.py  # Remove relation sections from markdown
│   ├── sync_web_bundle.py       # Web bundle synchronization
│   ├── synthesize_dashboard.py  # Dashboard synthesis script
│   ├── transcribe_recording.sh  # Recording transcription
│   └── user_prompt_fetch.py     # User prompt fetching
│
├── lib/                         # Shared Python
│   ├── __init__.py
│   ├── lib.md                   # Library module documentation
│   ├── paths.py                 # Path resolution (SSoT)
│   ├── session_reader.py        # Unified session parser (JSONL + agents + hooks)
│   └── session_analyzer.py      # Session data extraction for LLM analysis
│
├── tests/                       # pytest suite
│   ├── conftest.py              # Fixtures
│   ├── integration/             # E2E tests
│   └── tools/                   # Tool-specific tests
│
├── docs/                        # Extended documentation
│   ├── ENFORCEMENT.md           # Enforcement mechanism selection guide
│   ├── execution-flow.md        # Execution flow diagrams
│   ├── HOOKS.md                 # Hook architecture overview
│   ├── JIT-INJECTION.md         # Just-in-time context injection
│   ├── OBSERVABILITY.md         # Observability and logging schema
│   └── WEB-BUNDLE.md            # Web bundle sync documentation
│
├── templates/                   # GitHub workflow templates
│   └── github-workflow-*.yml    # Auto-sync workflow templates
│
├── config/
│   └── claude/                  # Reference config
│       ├── mcp.json             # MCP server configuration (main)
│       ├── mcp-base.json        # Base MCP config
│       ├── mcp-outlook-*.json   # Platform-specific Outlook configs
│       ├── settings.json        # Claude Code settings
│       └── settings-web.json    # Web environment settings
```

## Cross-References

### Command → Skill Invocations

| Command | Invokes Skill |
|---------|---------------|
| /meta | framework, python-dev |
| /supervise | supervisor (loads workflow from `skills/supervisor/workflows/`) |
| /ttd | supervisor (alias for `/supervise tdd`) |
| /log | learning-log |
| /transcript | transcript |
| /remember | remember |

### Workflow Templates

| Location | Workflows | Loaded By |
|----------|-----------|-----------|
| `skills/supervisor/workflows/` | tdd, batch-review, skill-audit | `/supervise {name}` |
| `skills/framework/workflows/` | 01-design, 02-debug, 03-experiment, 04-bloat, 06-spec | `Skill("framework")` |

**Decision pending**: Workflow selection criteria - see `$AOPS/specs/workflow-selection.md`

### Skill → Skill Dependencies

| Skill                             | May Invoke                            |
| --------------------------------- | ------------------------------------- |
| [[academicOps/commands/log\|log]] | transcript (when given session JSONL) |
| [[transcript]]                    | (none - wraps script)                 |
| [[session-insights]]              | transcript, learning-log              |

### Agent → Skill Routing

| Agent | Routes To |
|-------|-----------|
| hypervisor | supervisor, framework workflows |
| effectual-planner | tasks skill |

**Note**: For Python development, use `general-purpose` subagent and invoke `Skill(skill="python-dev")` directly.

## User Data ($ACA_DATA) - SEMANTIC ONLY

```
$ACA_DATA/
├── ACCOMMODATIONS.md            # Work style (binding)
├── CORE.md                      # User context, tools
├── STYLE*.md                    # Writing style
├── tasks/                       # Task data (active/, completed/, deferred/)
├── queue/                       # Prompt queue (executable prompts, chained)
│   └── done/                    # Completed prompts (archived)
└── projects/aops/
    ├── VISION.md                # End state
    ├── ROADMAP.md               # Current status
    └── specs/                   # Design documents (timeless)

# Episodic content → GitHub Issues (nicsuzor/academicOps repo)
# Labels: bug, experiment, devlog, decision, learning

# Archive
~/writing/sessions/              # Session transcripts (raw data)
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