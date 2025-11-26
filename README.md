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
├── uv.lock                  # uv dependency lock file
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

### Detailed File Breakdown

Every file in the repository is listed below, organized by directory.

#### Root-Level Files

```
$AOPS/
├── __init__.py
├── .gitignore
├── AXIOMS.md
├── BMEM-ARCHITECTURE.md
├── BMEM-CLAUDE-GUIDE.md
├── BMEM-FORMAT.md
├── BMEM-OBSIDIAN-GUIDE.md
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── setup.sh
├── update_hooks.py
└── uv.lock
```

#### GitHub Workflows (`.github/workflows/`)

```
.github/workflows/
├── beta-release.yml
├── claude-code-review.yml
├── claude.yml
├── ios-note-capture.yml
└── test-setup.yml
```

#### Skills (`skills/`)

**Skills Overview:**
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

**analyst/** - Data analysis skill:
```
skills/analyst/
├── SKILL.md
├── _CHUNKS/
│   ├── data-investigation.md
│   ├── dbt-workflow.md
│   ├── experiment-logging.md
│   ├── experiment_archival.md
│   ├── exploratory-analysis.md
│   ├── methodology-files.md
│   ├── methods-vs-methodology.md
│   ├── research-documentation.md
│   └── streamlit-workflow.md
├── references/
│   ├── assumptions_and_diagnostics.md
│   ├── bayesian_statistics.md
│   ├── context-discovery.md
│   ├── dbt-workflow.md
│   ├── effect_sizes_and_power.md
│   ├── matplotlib.md
│   ├── reporting_standards.md
│   ├── seaborn.md
│   ├── statistical-analysis.md
│   ├── statsmodels.md
│   ├── streamlit-patterns.md
│   ├── streamlit.md
│   └── test_selection_guide.md
└── scripts/
    └── assumption_checks.py
```

**bmem/** - Knowledge base operations:
```
skills/bmem/
├── SKILL.md
└── references/
    ├── approved-categories-relations.md
    ├── detail-level-guide.md
    ├── observation-quality-guide.md
    ├── obsidian-compatibility.md
    └── obsidian-format-spec.md
```

**docs-update/** - Documentation update skill:
```
skills/docs-update/
└── SKILL.md
```

**excalidraw/** - Visual diagram generation:
```
skills/excalidraw/
├── SKILL.md
├── libraries/
│   ├── awesome-icons.excalidrawlib
│   ├── data-processing.excalidrawlib
│   ├── data-viz.excalidrawlib
│   ├── hearts.excalidrawlib
│   ├── stick-figures-collaboration.excalidrawlib
│   └── stick-figures.excalidrawlib
└── references/
    ├── graph-layouts.md
    ├── icon-integration.md
    ├── json-format.md
    ├── library-guide.md
    ├── mcp-server-setup.md
    ├── mind-mapping-principles.md
    ├── productivity-tips.md
    ├── technical-details.md
    ├── text-container-pattern.md
    └── theme-colors.md
```

**extractor/** - Archive extraction:
```
skills/extractor/
├── README.md
├── SKILL.md
└── tests/
    └── test_archive_integration.sh
```

**feature-dev/** - Feature development workflow:
```
skills/feature-dev/
├── SKILL.md
└── templates/
    ├── dev-plan.md
    ├── experiment-plan.md
    ├── test-spec.md
    └── user-story.md
```

**framework/** - Framework maintenance and strategic partner:
```
skills/framework/
├── SKILL.md
├── TASK-SPEC-TEMPLATE.md
├── references/
│   ├── basic-memory-ai-guide.md
│   ├── basic-memory-mcp-tools.md
│   ├── basic-memory-sync-guide.md
│   ├── claude-code-config.md
│   ├── e2e-test-harness.md
│   ├── hooks_guide.md
│   ├── script-design-guide.md
│   ├── strategic-partner-mode.md
│   └── testing-with-live-data.md
├── scripts/
│   ├── generate_task_viz.py
│   └── validate_docs.py
├── specs/
│   ├── 2025-11-17_task-visualization-dashboard.md
│   ├── 2025-11-18_clarify-hook-behavior.md
│   ├── 2025-11-18_document-data-architecture.md
│   ├── 2025-11-18_fix-log-references.md
│   ├── 2025-11-18_fix-path-references.md
│   ├── 2025-11-18_framework-debugging-skill.md
│   ├── 2025-11-18_framework-logger-agent.md
│   ├── 2025-11-20_topic-based-learning-logs.md
│   ├── 2025-11-22_deny-rules-configuration.md
│   ├── docs-update-skill.md
│   └── task-management-rebuild.md
├── tests/
│   ├── manual_test_skill_discovery.md
│   ├── test_core_md_task_guidance.py
│   ├── test_email_workflow_guidance.py
│   ├── test_email_workflow_tools.py
│   ├── test_feature_dev_integration.sh
│   ├── test_framework_integrity.sh
│   ├── test_knowledge_extraction.sh
│   ├── test_session_start_content.sh
│   ├── test_task_management.sh
│   └── test_user_prompt_hook_integration.sh
└── workflows/
    ├── 01-design-new-component.md
    ├── 02-debug-framework-issue.md
    ├── 03-experiment-design.md
    ├── 04-monitor-prevent-bloat.md
    ├── 05-review-pull-request.md
    └── 06-develop-specification.md
```

**framework-debug/** - Framework debugging tools:
```
skills/framework-debug/
├── SKILL.md
└── scripts/
    └── errors.jq
```

**pdf/** - PDF generation from markdown:
```
skills/pdf/
├── SKILL.md
├── assets/
│   ├── academic-style.css
│   ├── letter-style.css
│   └── fonts/
│       ├── Roboto-Bold.ttf
│       ├── Roboto-BoldItalic.ttf
│       ├── Roboto-Italic.ttf
│       ├── Roboto-Light.ttf
│       ├── Roboto-Medium.ttf
│       ├── Roboto-Regular.ttf
│       ├── RobotoMonoNerdFont-Bold.ttf
│       ├── RobotoMonoNerdFont-Italic.ttf
│       └── RobotoMonoNerdFont-Regular.ttf
└── scripts/
    └── generate_pdf.py
```

**python-dev/** - Production Python development:
```
skills/python-dev/
├── SKILL.md
└── references/
    ├── bigquery.md
    ├── code-quality.md
    ├── fail-fast.md
    ├── fastapi.md
    ├── fastmcp.md
    ├── hydra.md
    ├── modern-python.md
    ├── pandas.md
    ├── testing.md
    └── type-safety.md
```

**skill-creator/** - Skill creation and packaging:
```
skills/skill-creator/
├── LICENSE.txt
├── SKILL.md
└── scripts/
    ├── init_skill.py
    ├── package_skill.py
    └── quick_validate.py
```

**tasks/** - Task management system (MCP server):
```
skills/tasks/
├── __init__.py
├── README.md
├── SKILL.md
├── models.py
├── server.py
├── task_loader.py
├── task_ops.py
├── scripts/
│   ├── task_add.py
│   ├── task_archive.py
│   └── task_view.py
├── tests/
│   └── test_task_scripts.sh
└── workflows/
    └── email-capture.md
```

**training-set-builder/** - Training data extraction:
```
skills/training-set-builder/
└── SKILL.md
```

#### Hooks (`hooks/`)

```
hooks/
├── README.md
├── autocommit_state.py
├── extract_session_knowledge.py
├── hook_debug.py
├── hook_logger.py
├── log_posttooluse.py
├── log_pretooluse.py
├── log_session_stop.py
├── log_sessionstart.py
├── log_subagentstop.py
├── log_userpromptsubmit.py
├── prompt_router.py
├── request_scribe.py
├── session_logger.py
├── sessionstart_load_axioms.py
├── test_marker_hook.py
├── user_prompt_submit.py
└── prompts/
    └── user-prompt-submit.md
```

#### Commands (`commands/`)

```
commands/
├── archive-extract.md
├── bmem.md
├── email.md
├── learn.md
├── log.md
├── meta.md
├── parallel-batch.md
├── strategy.md
├── task-viz.md
├── transcript.md
└── ttd.md
```

#### Agents (`agents/`)

```
agents/
├── dev.md
├── email-extractor.md
├── log-agent.md
└── task-viz.md
```

#### Experiments (`experiments/`)

```
experiments/
├── 2025-11-17_log-sufficiency-test.md
├── 2025-11-17_multi-window-cognitive-load-solutions.md
├── 2025-11-21_zotmcp-tdd-session.md
├── session-bmem-fail.md
└── session-bmem-pass.md
```

Note: Completed experiments and learning patterns LOG.md live at `$ACA_DATA/projects/aops/experiments/`

#### Scripts (`scripts/`)

```
scripts/
├── migrate_log_entries.py
├── package_deployment.py
└── setup.sh
```

#### Lib (`lib/`)

```
lib/
├── __init__.py
└── paths.py            # Path resolution (single source of truth for paths)
```

#### Tests (`tests/`)

```
tests/
├── __init__.py
├── README.md
├── conftest.py
├── manual_test_skill_discovery.md
├── paths.py
├── run_integration_tests.py
├── run_skill_tests.sh
├── test_bmem_default_project.py
├── test_bmem_documentation.py
├── test_bmem_retrieval.py
├── test_conftest.py
├── test_core_md_exists.py
├── test_core_md_task_guidance.py
├── test_dashboard_task_loader.py
├── test_email_workflow_guidance.py
├── test_email_workflow_tools.py
├── test_excalidraw_skill.py
├── test_framework_debug_skill.py
├── test_framework_installation.py
├── test_ios_note_capture_workflow.py
├── test_lib_paths.py
├── test_log_agent.py
├── test_package_deployment.py
├── test_paths.py
├── test_prompt_router.py
├── test_readme_paths.py
├── test_session_logging.py
├── test_session_start_loading.py
├── test_sessionstart_hook_format.py
├── test_skills_imports.py
├── test_skills_readme_integrity.py
├── test_task_ops.py
├── test_task_server_integration.py
├── test_yaml_frontmatter.py
├── integration/
│   ├── __init__.py
│   ├── README_SKILL_TESTS.md
│   ├── conftest.py
│   ├── test_autocommit_data.py
│   ├── test_bmem_diagnostic.py
│   ├── test_bmem_skill.py
│   ├── test_bmem_yaml_escaping.py
│   ├── test_deny_rules.py
│   ├── test_file_loading_e2e.py
│   ├── test_git_safety_hook.py
│   ├── test_headless_fixture.py
│   ├── test_session_start_content.py
│   ├── test_settings_discovery.py
│   ├── test_skill_discovery_standalone.py
│   ├── test_skill_invocation_e2e.py
│   ├── test_skill_script_discovery.py
│   ├── test_subagent_skill_invocation.py
│   ├── test_task_ops_integration.py
│   ├── test_task_script_invocation.py
│   └── test_task_viz.py
└── tools/
    ├── __init__.py
    ├── conftest.py
    └── test_bmem_retrieve.py
```

#### Config (`config/`)

```
config/
└── claude/
    ├── mcp.json
    └── settings.json
```

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
