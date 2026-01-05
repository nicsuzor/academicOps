---
name: index
title: Framework Index
type: reference
description: Complete file accounting for audits. NOT injected to agents - use FRAMEWORK.md for paths.
permalink: framework-index
audience: maintainers, audit-scripts
tags:
  - framework
  - structure
  - audit
---

# Framework Index

Complete file accounting for audit processes. See [[documentation-architecture]] for document purposes.

**Audience**: Maintainers and audit scripts only. Agents use [[FRAMEWORK.md]] for paths.

For human-readable overview, see [[README]].

## File Tree

```
$AOPS/
├── [[AXIOMS.md]]                # Inviolable principles (injected at session start)
├── [[HEURISTICS.md]]            # Empirically validated rules (injected at session start)
├── [[FRAMEWORK.md]]             # Resolved paths for this session (injected at session start)
├── [[README.md]]                # Brief overview, feature inventory
├── [[INDEX.md]]                 # THIS FILE - complete file tree
├── [[RULES.md]]                 # Current enforcement rules (auto-generated)
├── [[WORKFLOWS.md]]             # Task routing and workflow selection
├── [[ROADMAP.md]]               # Current development status
├── [[VISION.md]]                # End state vision
├── [[CLAUDE.md]]                # Repo instructions (@ syntax auto-loads)
├── [[AGENTS.md]]                # Agent context (shared by all agents)
├── [[GEMINI.md]]                # Gemini agent instructions
├── pyproject.toml               # Python project config
├── uv.lock                      # Dependency lock file
├── setup.sh                     # Main installation script
├── .mcp.json                    # MCP server discovery config
├── .pre-commit-config.yaml      # Pre-commit hooks configuration
├── .gitignore                   # Git ignore patterns
├── .gitmodules                  # Git submodules
├── __init__.py                  # Package init
├── reference-graph.csv          # Framework reference graph (wrong location)
├── current-tasks.excalidraw     # Visual task board (orphan - flagged)
│
├── .github/workflows/           # CI/CD workflows
│   ├── beta-release.yml         # Beta release automation
│   ├── claude-code-review.yml   # Automated code review
│   ├── claude.yml               # Claude Code bot integration
│   ├── framework-health.yml     # Framework health enforcement
│   ├── ios-note-capture.yml     # iOS note capture workflow
│   └── test-setup.yml           # Setup script validation
│
├── agents/                      # Spawnable subagents (Task tool)
│   ├── critic.md                # Second-opinion review of plans/conclusions
│   ├── effectual-planner.md     # Effectual planning (Sarasvathy) - plans as hypotheses
│   ├── planner.md               # Implementation planning with memory + critic review
│   └── prompt-hydrator.md       # Context gathering + workflow selection for every prompt
│
├── commands/                    # Slash commands (main agent executes)
│   ├── add.md                   # Quick-add task from context
│   ├── aops.md                  # Show framework capabilities
│   ├── audit.md                 # → audit skill (framework governance)
│   ├── consolidate.md           # Consolidate learning-log entries
│   ├── convert-to-md.md         # Batch document → markdown conversion
│   ├── diag.md                  # Quick diagnostic of session state
│   ├── do.md                    # Execute with context enrichment + guardrails
│   ├── email.md                 # Email → task extraction
│   ├── encode.md                # Capture work patterns as workflows/skills
│   ├── learn.md                 # Minor instruction adjustments
│   ├── log.md                   # → learning-log skill
│   ├── meta.md                  # Strategic brain + executor
│   ├── parallel-batch.md        # Parallel file processing
│   ├── q.md                     # Queue task for later (delayed /do)
│   ├── qa.md                    # Quality assurance verification
│   ├── reflect.md               # Agent self-audit of process compliance
│   ├── review-training-cmd.md   # Process review/source pairs
│   ├── strategy.md              # Strategic thinking partner
│   ├── task-viz.md              # Task graph visualization
│   └── ttd.md                   # TDD orchestration
│
├── config/
│   └── claude/                  # Reference config
│       ├── mcp.json             # MCP server configuration (main)
│       ├── mcp-base.json        # Base MCP config
│       ├── mcp-outlook-macos.json   # macOS Outlook config
│       ├── mcp-outlook-proxy.json   # Proxy Outlook config
│       ├── mcp-outlook-windows.json # Windows Outlook config
│       ├── settings.json        # Claude Code settings
│       └── settings-web.json    # Web environment settings
│
├── docs/                        # Extended documentation
│   ├── ENFORCEMENT.md           # Enforcement mechanism selection guide
│   ├── execution-flow.md        # Execution flow diagrams (Mermaid)
│   ├── HOOKS.md                 # Hook architecture overview
│   ├── JIT-INJECTION.md         # Just-in-time context injection
│   ├── OBSERVABILITY.md         # Observability and logging schema
│   └── WEB-BUNDLE.md            # Web bundle sync documentation
│
├── hooks/                       # Session lifecycle (Python)
│   ├── CLAUDE.md                # Hook design principles (JIT context)
│   ├── hooks.md                 # Hook inventory and descriptions
│   ├── guardrails.md            # Guardrail definitions for task types
│   ├── router.py                # Central hook dispatcher
│   ├── sessionstart_load_axioms.py  # Injects AXIOMS.md, FRAMEWORK.md, HEURISTICS.md
│   ├── session_env_setup.sh     # Environment setup at session start
│   ├── user_prompt_submit.py    # Writes context to temp file, returns short instruction
│   ├── autocommit_state.py      # Auto-commit data/ changes
│   ├── policy_enforcer.py       # Block destructive operations (PreToolUse)
│   ├── fail_fast_watchdog.py    # Detect errors, inject fail-fast reminder
│   ├── session_reflect.py       # Session end reflection prompt
│   ├── session_logger.py        # Log file path management
│   ├── hook_logger.py           # Centralized event logging
│   ├── unified_logger.py        # Universal event logger
│   ├── hook_debug.py            # Hook debugging
│   ├── request_scribe.py        # Memory reminder (PostToolUse)
│   ├── terminal_title.py        # Set terminal title
│   ├── marker_hook.py           # Test hook for verification
│   ├── verify_conclusions.py    # Disabled stub
│   ├── git-post-commit-sync-aops    # Git post-commit hook for sync
│   ├── prompts/
│   │   ├── user-prompt-submit.md    # Context for UserPromptSubmit hook
│   │   └── memory-reminder.md       # PostToolUse memory prompt
│   └── templates/
│       ├── prompt-hydrator-context.md     # Full context template (written to temp file)
│       └── prompt-hydration-instruction.md # Short instruction template for main agent
│
├── lib/                         # Shared Python
│   ├── __init__.py              # Package init
│   ├── lib.md                   # Library module documentation
│   ├── paths.py                 # Path resolution (SSoT)
│   ├── session_reader.py        # Unified session parser (JSONL + agents + hooks)
│   └── session_analyzer.py      # Session data extraction for LLM analysis
│
├── scripts/                     # Utility scripts
│   ├── __init__.py              # Package init
│   ├── scripts.md               # Script inventory and documentation
│   ├── audit_framework_health.py    # Framework health metrics
│   ├── audit_skill_compliance.py    # Skill compliance audit
│   ├── check_broken_wikilinks.py    # Pre-commit: broken wikilink check
│   ├── check_index_completeness.py  # Pre-commit: INDEX.md accounting
│   ├── check_orphan_files.py        # Pre-commit: orphan file detection
│   ├── check_skill_line_count.py    # Pre-commit: SKILL.md size limit
│   ├── claude_transcript.py     # Session JSONL → markdown
│   ├── measure_router_compliance.py # Router performance metrics
│   ├── migrate_log_entries.py   # Log entry migration
│   ├── package_deployment.py    # Skill packaging
│   ├── regenerate_task_index.py # Task index regeneration
│   ├── remove_relation_sections.py  # Remove relation sections from markdown
│   ├── sync_web_bundle.py       # Web bundle synchronization
│   ├── synthesize_dashboard.py  # Dashboard synthesis script
│   ├── transcribe_recording.sh  # Recording transcription
│   └── user_prompt_fetch.py     # User prompt fetching
│
├── skills/
│   ├── analyst/                 # Data analysis (dbt, Streamlit, stats)
│   │   ├── SKILL.md             # Main skill file
│   │   ├── scripts/
│   │   │   └── assumption_checks.py  # Statistical assumption checks
│   │   ├── instructions/
│   │   │   ├── data-investigation.md     # Data investigation workflow
│   │   │   ├── dbt-workflow.md           # dbt workflow guide
│   │   │   ├── experiment_archival.md    # Experiment archival process
│   │   │   ├── experiment-logging.md     # Experiment logging guide
│   │   │   ├── exploratory-analysis.md   # Exploratory analysis workflow
│   │   │   ├── methodology-files.md      # Methodology file conventions
│   │   │   ├── methods-vs-methodology.md # Methods vs methodology distinction
│   │   │   ├── research-documentation.md # Research documentation standards
│   │   │   └── streamlit-workflow.md     # Streamlit development workflow
│   │   └── references/
│   │       ├── assumptions_and_diagnostics.md  # Diagnostic assumptions
│   │       ├── bayesian_statistics.md          # Bayesian methods
│   │       ├── context-discovery.md            # Context discovery patterns
│   │       ├── dbt-workflow.md                 # dbt reference
│   │       ├── effect_sizes_and_power.md       # Effect sizes and power
│   │       ├── matplotlib.md                   # Matplotlib guide
│   │       ├── reporting_standards.md          # Reporting standards
│   │       ├── seaborn.md                      # Seaborn guide
│   │       ├── statistical-analysis.md         # Statistical analysis
│   │       ├── statsmodels.md                  # Statsmodels guide
│   │       ├── streamlit.md                    # Streamlit basics
│   │       ├── streamlit-patterns.md           # Streamlit patterns
│   │       └── test_selection_guide.md         # Statistical test selection
│   │
│   ├── audit/                   # Framework governance audit
│   │   ├── SKILL.md             # Main skill file
│   │   └── scripts/
│   │       ├── build_reference_map.py  # Reference graph extraction
│   │       └── find_orphans.py         # Orphan file detection
│   │
│   ├── convert-to-md/           # Batch document → markdown conversion
│   │   └── SKILL.md             # Main skill file
│   │
│   ├── dashboard/               # Live task dashboard (Streamlit)
│   │   ├── SKILL.md             # Main skill file
│   │   └── dashboard.py         # Streamlit app
│   │
│   ├── excalidraw/              # Visual diagram generation
│   │   ├── SKILL.md             # Main skill file
│   │   ├── libraries/
│   │   │   ├── awesome-icons.excalidrawlib      # Icon library
│   │   │   ├── data-processing.excalidrawlib   # Data processing shapes
│   │   │   ├── data-viz.excalidrawlib          # Data viz shapes
│   │   │   ├── hearts.excalidrawlib            # Heart shapes
│   │   │   ├── stick-figures-collaboration.excalidrawlib  # Collab figures
│   │   │   └── stick-figures.excalidrawlib     # Stick figures
│   │   └── references/
│   │       ├── graph-layouts.md         # Graph layout patterns
│   │       ├── icon-integration.md      # Icon integration guide
│   │       ├── json-format.md           # Excalidraw JSON format
│   │       ├── library-guide.md         # Library usage guide
│   │       ├── mcp-server-setup.md      # MCP server setup
│   │       ├── mind-mapping-principles.md  # Mind mapping guide
│   │       ├── productivity-tips.md     # Productivity tips
│   │       ├── technical-details.md     # Technical details
│   │       ├── text-container-pattern.md  # Text container patterns
│   │       └── theme-colors.md          # Theme color reference
│   │
│   ├── extractor/               # Archive → memory extraction
│   │   ├── SKILL.md             # Main skill file
│   │   ├── README.md            # Extractor documentation
│   │   └── tests/
│   │       └── test_archive_integration.sh  # Integration test
│   │
│   ├── fact-check/              # Verify claims against sources
│   │   ├── SKILL.md             # Main skill file
│   │   └── templates/
│   │       └── verification-report.md  # Verification report template
│   │
│   ├── feature-dev/             # Feature development templates
│   │   ├── SKILL.md             # Main skill file
│   │   └── templates/
│   │       ├── dev-plan.md          # Development plan template
│   │       ├── experiment-plan.md   # Experiment plan template
│   │       ├── test-spec.md         # Test specification template
│   │       └── user-story.md        # User story template
│   │
│   ├── framework/               # Convention reference for infrastructure
│   │   ├── SKILL.md             # Paths, patterns, anti-bloat rules
│   │   ├── TASK-SPEC-TEMPLATE.md  # Task spec template
│   │   ├── scripts/
│   │   │   └── validate_docs.py     # Documentation validator
│   │   ├── references/
│   │   │   ├── claude-code-config.md     # Claude Code config guide
│   │   │   ├── e2e-test-harness.md       # E2E test harness
│   │   │   ├── hooks_guide.md            # Hooks development guide
│   │   │   ├── script-design-guide.md    # Script design guide
│   │   │   └── strategic-partner-mode.md # Strategic partner mode
│   │   ├── workflows/
│   │   │   ├── 01-design-new-component.md  # Design workflow
│   │   │   ├── 02-debug-framework-issue.md # Debug workflow
│   │   │   ├── 03-experiment-design.md     # Experiment workflow
│   │   │   ├── 04-monitor-prevent-bloat.md # Anti-bloat workflow
│   │   │   └── 06-develop-specification.md # Spec development workflow
│   │   └── tests/
│   │       ├── manual_test_skill_discovery.md  # Manual test guide
│   │       ├── test_core_md_task_guidance.py   # Core.md tests
│   │       ├── test_email_workflow_guidance.py # Email workflow tests
│   │       ├── test_email_workflow_tools.py    # Email tools tests
│   │       ├── test_feature_dev_integration.sh # Feature dev tests
│   │       ├── test_framework_integrity.sh     # Framework integrity tests
│   │       ├── test_knowledge_extraction.sh    # Knowledge extraction tests
│   │       ├── test_session_start_content.sh   # Session start tests
│   │       ├── test_task_management.sh         # Task management tests
│   │       └── test_user_prompt_hook_integration.sh  # Hook integration tests
│   │
│   ├── garden/                  # Incremental PKM maintenance
│   │   └── SKILL.md             # Main skill file
│   │
│   ├── ground-truth/            # Ground truth label management
│   │   └── SKILL.md             # Main skill file
│   │
│   ├── learning-log/            # Pattern logging to thematic files
│   │   └── SKILL.md             # → may invoke transcript skill
│   │
│   ├── osb-drafting/            # IRAC analysis for OSB cases
│   │   ├── SKILL.md             # Main skill file
│   │   └── templates/
│   │       ├── case-analysis.md           # Case analysis template
│   │       └── verification-checklist.md  # Verification checklist
│   │
│   ├── pdf/                     # Markdown → PDF
│   │   ├── SKILL.md             # Main skill file
│   │   ├── scripts/
│   │   │   └── generate_pdf.py  # PDF generation script
│   │   └── assets/
│   │       ├── academic-style.css   # Academic styling
│   │       ├── letter-style.css     # Letter styling
│   │       └── fonts/
│   │           ├── Roboto-Bold.ttf
│   │           ├── Roboto-BoldItalic.ttf
│   │           ├── Roboto-Italic.ttf
│   │           ├── Roboto-Light.ttf
│   │           ├── Roboto-Medium.ttf
│   │           ├── Roboto-Regular.ttf
│   │           ├── RobotoMonoNerdFont-Bold.ttf
│   │           ├── RobotoMonoNerdFont-Italic.ttf
│   │           └── RobotoMonoNerdFont-Regular.ttf
│   │
│   ├── python-dev/              # Production Python standards
│   │   ├── SKILL.md             # Fail-fast, types, TDD
│   │   └── references/
│   │       ├── bigquery.md          # BigQuery guide
│   │       ├── code-quality.md      # Code quality standards
│   │       ├── fail-fast.md         # Fail-fast patterns
│   │       ├── fastapi.md           # FastAPI guide
│   │       ├── fastmcp.md           # FastMCP guide
│   │       ├── hydra.md             # Hydra config guide
│   │       ├── modern-python.md     # Modern Python patterns
│   │       ├── pandas.md            # Pandas guide
│   │       ├── testing.md           # Testing guide
│   │       └── type-safety.md       # Type safety guide
│   │
│   ├── remember/                # Memory server operations
│   │   ├── SKILL.md             # Write & retrieve from memory server
│   │   ├── references/
│   │   │   ├── detail-level-guide.md      # Detail level guidance
│   │   │   └── obsidian-format-spec.md    # Obsidian format spec
│   │   └── workflows/
│   │       ├── capture.md       # Capture workflow
│   │       ├── prune.md         # Prune workflow
│   │       └── validate.md      # Validate workflow
│   │
│   ├── review-training/         # Training data from reviews
│   │   ├── SKILL.md             # Main skill file
│   │   ├── README.md            # Documentation
│   │   ├── scripts/
│   │   │   └── batch_next.py    # Batch processing script
│   │   └── tests/
│   │       └── test_integration.sh  # Integration test
│   │
│   ├── session-insights/        # Accomplishments + learning extraction
│   │   ├── SKILL.md             # Orchestrates transcripts, daily summary, Gemini mining
│   │   ├── mining-prompt.md     # Gemini extraction prompt template
│   │   └── scripts/
│   │       ├── extract_narrative.py  # Narrative extraction
│   │       └── find_sessions.py      # Session file discovery
│   │
│   ├── supervisor/              # Workflow templates (tdd, batch-review)
│   │   └── workflows/
│   │       ├── batch-review.md  # Batch review workflow
│   │       └── tdd.md           # TDD workflow
│   │
│   ├── tasks/                   # Task management (MCP server)
│   │   ├── SKILL.md             # Main skill file
│   │   ├── README.md            # Documentation
│   │   ├── __init__.py          # Package init
│   │   ├── server.py            # MCP server implementation
│   │   ├── models.py            # Task data models
│   │   ├── task_loader.py       # Task loading utilities
│   │   ├── task_ops.py          # Task operations
│   │   ├── scripts/
│   │   │   ├── task_add.py      # Add task CLI
│   │   │   ├── task_archive.py  # Archive task CLI
│   │   │   ├── task_item_add.py # Add task item CLI
│   │   │   ├── task_update.py   # Update task CLI
│   │   │   ├── task_view.py     # View task CLI
│   │   │   └── task_viz.py      # Visualize tasks CLI
│   │   ├── workflows/
│   │   │   └── email-capture.md # Email capture workflow
│   │   └── tests/
│   │       └── test_task_scripts.sh  # Task script tests
│   │
│   ├── training-set-builder/    # Training data extraction
│   │   └── SKILL.md             # Main skill file
│   │
│   └── transcript/              # Session JSONL → markdown
│       └── SKILL.md             # Wraps scripts/claude_transcript.py
│
├── specs/                       # Design specifications
│   ├── specs.md                 # Spec index with Mermaid diagram
│   ├── agent-behavior-watchdog.md   # Agent behavior monitoring
│   ├── analyst-skill.md             # Analyst skill spec
│   ├── audit-skill.md               # Audit skill spec
│   ├── cloudflare-prompt-logging.md # Cloudflare logging spec
│   ├── dashboard-skill.md           # Dashboard skill spec (consolidated)
│   ├── command-discoverability.md   # Command discovery spec
│   ├── conclusion-verification-hook.md  # Conclusion verification
│   ├── daily notes.md               # Daily notes spec
│   ├── dashboard-narrative.md       # Dashboard narrative spec
│   ├── dashboard-skill.md           # Dashboard skill spec
│   ├── effectual-planning-agent.md  # Effectual planning spec
│   ├── email-to-tasks-workflow.md   # Email to tasks spec
│   ├── encode-command-spec.md       # Encode command spec
│   ├── enforcement.md               # Enforcement philosophy
│   ├── excalidraw-skill.md          # Excalidraw skill spec
│   ├── execution-flow-spec.md       # Execution flow spec
│   ├── feature-dev-skill.md         # Feature dev skill spec
│   ├── framework-aware-operations.md  # Framework-aware ops spec
│   ├── framework-health.md          # Framework health metrics spec
│   ├── framework-skill.md           # Framework skill spec
│   ├── garden-skill.md              # Garden skill spec
│   ├── generated-indices.md         # Generated indices spec
│   ├── hook-router.md               # Hook router spec
│   ├── informed-improvement-options.md  # Improvement options spec
│   ├── knowledge-management-philosophy.md  # KM philosophy
│   ├── learning-log-skill.md        # Learning log skill spec
│   ├── meta-framework-advisor.md    # Meta framework spec
│   ├── multi-terminal-sync.md       # Multi-terminal sync spec
│   ├── parallel-batch-command.md    # Parallel batch spec
│   ├── plan-quality-gate.md         # Plan quality gate spec
│   ├── prompt-hydration.md          # Prompt hydration spec
│   ├── prompt-queue.md              # Prompt queue spec
│   ├── python-dev-skill.md          # Python dev skill spec
│   ├── reference-map skill.md       # Reference map skill spec
│   ├── remember-skill.md            # Remember skill spec
│   ├── session-insights-skill.md    # Session insights skill spec (consolidated)
│   ├── session-start-injection.md   # Session start injection spec
│   ├── session-sync-user-story.md   # Session sync spec
│   ├── session-transcript-extractor.md  # Transcript extractor spec
│   ├── skills.md                    # Skills overview
│   ├── spec-maintenance.md          # Spec maintenance spec
│   ├── supervisor-skill.md          # Supervisor skill spec
│   ├── task-list-overwhelm.md       # Task overwhelm spec
│   ├── tasks-mcp-server.md          # Tasks MCP server spec
│   ├── tasks-skill.md               # Tasks skill spec
│   ├── testing-framework-overview.md  # Testing framework spec
│   ├── transcript-skill.md          # Transcript skill spec
│   ├── ultra-vires-custodiet.md     # Ultra vires spec
│   └── web-bundle-sync.md           # Web bundle sync spec
│
├── templates/                   # GitHub workflow templates
│   ├── github-workflow-sync-aops.yml         # Sync workflow
│   └── github-workflow-sync-aops-nightly.yml # Nightly sync workflow
│
└── tests/                       # pytest suite
    ├── __init__.py              # Package init
    ├── conftest.py              # Fixtures
    ├── paths.py                 # Test path utilities
    ├── README.md                # Test documentation
    ├── HOOK_TEST_PROTOCOL.md    # Hook testing protocol
    ├── manual_test_skill_discovery.md  # Manual test guide
    ├── run_integration_tests.py # Integration test runner
    ├── run_skill_tests.sh       # Skill test runner
    ├── test_conftest.py         # Conftest tests
    ├── test_core_md_exists.py   # Core.md existence test
    ├── test_dashboard_layout.py # Dashboard layout tests
    ├── test_dashboard_session_context.py  # Dashboard context tests
    ├── test_dashboard_task_loader.py      # Task loader tests
    ├── test_email_workflow_tools.py       # Email tools tests
    ├── test_excalidraw_skill.py # Excalidraw tests
    ├── test_framework_debug_skill.py      # Debug skill tests
    ├── test_framework_installation.py     # Installation tests
    ├── test_hook_logger_serialization.py  # Logger tests
    ├── test_ios_note_capture_workflow.py  # iOS capture tests
    ├── test_lib_paths.py        # Lib paths tests
    ├── test_package_deployment.py         # Deployment tests
    ├── test_paths.py            # Path tests
    ├── test_request_scribe_hook.py        # Request scribe tests
    ├── test_router_compliance.py          # Router compliance tests
    ├── test_router_context.py   # Router context tests
    ├── test_session_analyzer_dashboard.py # Analyzer tests
    ├── test_session_insights_outputs.py   # Insights output tests
    ├── test_sessionstart_hook_format.py   # Hook format tests
    ├── test_session_start_loading.py      # Session start tests
    ├── test_skill_compliance_audit.py     # Compliance tests
    ├── test_skills_imports.py   # Skills import tests
    ├── test_sync_web_bundle.py  # Web bundle tests
    ├── test_task_ops.py         # Task ops tests
    ├── test_task_server_integration.py    # Task server tests
    ├── test_user_prompt_submit_hook.py    # Prompt hook tests
    ├── test_yaml_frontmatter.py # YAML frontmatter tests
    ├── data/
    │   └── sample_transcript_new_format.md  # Test data
    ├── hooks/
    │   ├── test_cloudflare_logging.py  # Cloudflare logging tests
    │   └── test_router.py       # Router tests
    ├── integration/
    │   ├── __init__.py          # Package init
    │   ├── conftest.py          # Integration fixtures
    │   ├── README_SKILL_TESTS.md  # Skill test docs
    │   ├── test_autocommit_data.py        # Autocommit tests
    │   ├── test_deny_rules.py   # Deny rules tests
    │   ├── test_doc_policy_hook.py        # Doc policy tests
    │   ├── test_file_loading_e2e.py       # File loading tests
    │   ├── test_gemini_mcp_e2e.py         # Gemini MCP tests
    │   ├── test_git_safety_hook.py        # Git safety tests
    │   ├── test_headless_fixture.py       # Headless fixture tests
    │   ├── test_multi_agent_workflows.py  # Multi-agent tests
    │   ├── test_policy_enforcer_e2e.py    # Policy enforcer tests
    │   ├── test_session_insights_e2e.py   # Session insights tests
    │   ├── test_session_start_content.py  # Session start tests
    │   ├── test_settings_discovery.py     # Settings discovery tests
    │   ├── test_skill_delegation_pattern.py  # Delegation tests
    │   ├── test_skill_discovery_standalone.py  # Discovery tests
    │   ├── test_skill_invocation_e2e.py   # Invocation tests
    │   ├── test_skill_script_discovery.py # Script discovery tests
    │   ├── test_subagent_skill_invocation.py  # Subagent tests
    │   ├── test_task_ops_integration.py   # Task ops integration
    │   ├── test_task_script_invocation.py # Task script tests
    │   └── test_task_viz.py     # Task viz tests
    └── tools/
        ├── __init__.py          # Package init
        └── conftest.py          # Tools fixtures
```

## Cross-References

### Command → Skill/Agent Invocations

| Command | Invokes |
|---------|---------|
| /do | Full pipeline (context, plan, execute, verify) |
| /q | tasks skill (delayed /do) |
| /meta | framework, python-dev skills |
| /ttd | TDD workflow (via /do) |
| /log | learning-log skill |
| /transcript | transcript skill |
| /remember | remember skill |

### Workflow Templates

| Location | Workflows | Loaded By |
|----------|-----------|-----------|
| `skills/supervisor/workflows/` | tdd, batch-review | `/ttd`, `/do` |
| `skills/framework/workflows/` | 01-design, 02-debug, 03-experiment, 04-bloat, 06-spec | `Skill("framework")` |

### Skill → Skill Dependencies

| Skill | May Invoke |
|-------|------------|
| log | transcript (when given session JSONL) |
| transcript | (none - wraps script) |
| session-insights | transcript, learning-log |

### Agent → Skill Routing

| Agent | Routes To |
|-------|-----------|
| effectual-planner | tasks skill |
| planner | memory search, critic review |

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
