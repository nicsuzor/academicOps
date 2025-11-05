# academicOps Agent Framework

Modular, hierarchical agent framework for rigorous, context-aware automation in academic research projects.

## Quick Start

```bash
# Set environment variable
export ACADEMICOPS=/path/to/academicOps

# Run setup in your project
cd /path/to/your/project
$ACADEMICOPS/scripts/setup_academicops.sh

# Launch Claude Code
claude
```

## What is academicOps?

**academicOps** provides:

- **Modular context system** - Chunks architecture with DRY symlinks
- **Specialized agents** - Development, analysis, strategy, framework maintenance
- **Automated validation hooks** - Quality standards enforced at runtime
- **Hierarchical instruction loading** - Framework → personal → project tiers
- **Zero-configuration context** - Loaded at every session start

## Core Principles

1. **Fail-Fast Philosophy**: No fallbacks, no defensive programming, no workarounds
2. **DRY (Don't Repeat Yourself)**: One source of truth, symlinks for reuse
3. **Project Isolation**: Project-specific content stays in project repos
4. **Self-Documenting**: Code and inline docs, not separate markdown files

**Full axioms**: `core/_CORE.md` (loaded automatically via SessionStart hook)

---

## Repository Structure

```
$ACADEMICOPS/                  # Framework repository (this repo)
├── chunks/                    # Shared context modules (DRY single sources)
│   ├── AXIOMS.md             # Universal principles
│   ├── INFRASTRUCTURE.md     # Framework paths, env vars, repo structure
│   ├── AGENT-BEHAVIOR.md     # Conversational/agent-specific rules
│   └── SKILL-PRIMER.md       # Skill execution context
├── core/
│   └── _CORE.md              # References chunks/ (loaded at SessionStart)
├── agents/                    # Subagent definitions
├── commands/                  # Slash command definitions
├── hooks/                     # SessionStart, PreToolUse, Stop hooks
├── scripts/                   # Automation tools
├── skills/                    # Packaged skill sources
├── docs/                      # Human documentation
└── tests/                     # Integration tests (including chunks loading tests)
```

<!-- INSTRUCTION_TREE_START -->
## Instruction Tree

This section is auto-generated from repository scan.
Last updated: bot repository

### Agents (7)

Specialized agent definitions loaded via slash commands or subagent invocation:

- **ANALYST** - An agent for data analysis, evaluation, and generating insights from experimental results with academic rigor. (`agents/ANALYST.md`)
- **DEVELOPER** - A specialized developer. Your purpose is to write, refactor, test, and debug code with precision and discipline. You must adhere strictly to the project's established architecture, conventions, and workflows. Your goal is to produce clean, maintainable, and correct code while avoiding common development pitfalls. Invoke any time you need to make code changes. (`agents/DEVELOPER.md`)
- **STRATEGIST** - Strategic thinking partner for planning, task review, and context navigation. Provides task display, strategic context analysis, and facilitation. Auto-invoke when user asks about tasks, deadlines, priorities, or strategic alignment. Uses tasks and email skills exclusively for operations. (`agents/STRATEGIST.md`)
- **SUPERVISOR** - Orchestrates multi-agent workflows with comprehensive quality gates, test-first development, and continuous plan validation. Ensures highest reliability through micro-iterations, independent reviews, and scope drift detection. Exception to DO ONE THING axiom - explicitly authorized to coordinate complex multi-step tasks. (`agents/SUPERVISOR.md`)
- **end-of-session** - Automated end-of-session workflow that orchestrates commit and accomplishment capture when substantial work is complete. Silently handles git commits and writes one-line accomplishment entries for completed work only. (`agents/end-of-session.md`)
- **scribe** - Silent background processor that automatically captures tasks, priorities, and context from conversations, maintaining the knowledge base in $ACADEMICOPS_PERSONAL/data. Auto-invoke proactively and constantly to extract tasks, projects, goals, and strategic information without interrupting user flow. Uses tasks skill for all task operations. (`agents/scribe.md`)
- **task-manager** - EXPERIMENTAL silent background processor that extracts tasks from emails and conversations, updates knowledge base invisibly. Auto-invoke proactively at end of substantial work sessions and whenever current/future task information is presented. Uses tasks and email skills exclusively for all operations. (`agents/task-manager.md`)

### Skills (19)

Packaged workflows installed to `~/.claude/skills/`:

- **agent-initialization** - This skill should be automatically invoked when initializing a workspace to create/update an AGENT.md file that instructs agents to search for and use existing skills before attempting tasks. The skill scans available skills and maintains an up-to-date index with descriptions of when to invoke each skill. (`skills/agent-initialization`)
- **analyst** - Support academic research data analysis using dbt and Streamlit. Use this skill when working with computational research projects (identified by dbt/ directory, Streamlit apps, or empirical data pipelines). The skill enforces academicOps best practices for reproducible, transparent, self-documenting research with collaborative single-step workflow. (`skills/analyst`)
  - Dependencies: MATPLOTLIB.md, STATSMODELS.md, PYTHON-DEV.md, SEABORN.md
- **aops-bug** - Track bugs, agent violations, and framework improvements in the academicOps agent system. Understand core axioms, categorize behavioral patterns, manage experiment logs, detect architecture drift, and maintain framework health. Calls github-issue skill for GitHub operations. Use when agents violate axioms, framework bugs occur, experiments complete, or architecture needs updating. Specific to academicOps framework. (`skills/aops-bug`)
- **aops-trainer** - This skill should be used when reviewing and improving agents, skills, hooks, permissions, and configurations. It enforces an experiment-driven, anti-bloat approach with enforcement hierarchy of Scripts, Hooks, Config, then Instructions. The skill prevents adding repetitive or overly specific instructions, understands how different enforcement mechanisms fit together, and makes strategic decisions about where to intervene. Use this skill when agent performance issues arise, when evaluating new techniques, or when maintaining the agent framework. Always test before claiming something works. Specific to academicOps framework. (`skills/aops-trainer`)
  - Dependencies: AXIOMS.md, SKILL-PRIMER.md, INFRASTRUCTURE.md
- **archiver** - Archive experimental analysis and intermediate work into long-lived Jupyter notebooks with HTML exports before data removal or major pipeline changes. Cleans up working directories to maintain only current state. Use when completing experiments that will become unreproducible due to data removal or when major analytical decisions need to be permanently documented. (`skills/archiver`)
- **claude-hooks** - This skill should be used when working with Claude Code hooks - creating, configuring, debugging, or understanding hook input/output schemas. Provides complete technical reference for all hook types, academicOps patterns, and real-world examples. (`skills/claude-hooks`)
- **claude-md-maintenance** - This skill maintains CLAUDE.md files across repositories by extracting substantive content to chunks, enforcing @reference patterns, and ensuring proper hierarchical organization. Use when CLAUDE.md files contain inline instructions, are too long, have duplication, or need refactoring to follow academicOps best practices. (`skills/claude-md-maintenance`)
- **document-skills** (`skills/document-skills`)
- **email** - This skill provides expertise for interacting with Outlook email via MCP tools. Use when agents or subagents need to fetch, read, list, or search emails. Includes email triage patterns, signal detection (urgent/deadlines), and filtering guidelines. Does NOT handle task extraction (use tasks skill for that). (`skills/email`)
- **git-commit** - This skill should be used when committing code changes to git repositories. It validates code quality against defined standards, enforces conventional commit format, handles submodule patterns, and executes commits only when all validation passes. The skill reports problems without fixing them, maintaining fail-fast principles. Use this skill any time code needs to be committed to ensure quality gates are enforced. (`skills/git-commit`)
  - Dependencies: FAIL-FAST.md, TESTS.md, GIT-WORKFLOW.md
- **github-issue** - Manage GitHub issues across any repository with exhaustive search, precise documentation, and proactive updates. Search existing issues before creating new ones, format technical content clearly, link commits and PRs, and maintain issue lifecycle. Works universally - not specific to any project or framework. Use when documenting bugs, tracking features, updating issue status, or searching for related work. (`skills/github-issue`)
- **no-throwaway-code** - Intervention skill that triggers when agents attempt temporary/throwaway Python code (python -c, temp scripts, one-off investigations). Enforces Axiom 15 - WRITE FOR THE LONG TERM. Nudges toward reusable solutions using dev agent or test-writing skill instead. (`skills/no-throwaway-code`)
- **pdf** - This skill should be used when converting markdown documents to professionally formatted PDFs. It provides academic-style typography with Roboto fonts, proper page layouts, and styling suitable for research documents, reviews, reports, and academic writing. Use when users request PDF generation from markdown files or need professional document formatting. (`skills/pdf`)
- **scribe** - A scribe automatically and silently captures tasks, priorities, and context throughout conversations, maintaining the user's knowledge base in $ACADEMICOPS_PERSONAL/data. Invoke proactively and constantly to extract information about tasks, projects, goals, and strategic priorities without interrupting flow. Your value is measured by how rarely the user needs to explicitly ask you to save something. (`skills/scribe`)
- **skill-creator** - Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations. (`skills/skill-creator`)
- **skill-maintenance** - This skill should be used for ongoing skill maintenance and evolution. It audits skills for outdated patterns, updates skills to current framework best practices, validates scripts and references, packages skills for distribution, and ensures deployment symlinks are correct. Use this when framework patterns evolve, skills need updates, or the entire skill ecosystem requires auditing. (`skills/skill-maintenance`)
- **strategic-partner** - This skill provides strategic facilitation, questioning frameworks, and thinking partnership capabilities for planning and brainstorming sessions. It focuses on meeting users where they are, exploring ideas organically through unstructured conversation, and helping them think through complex strategic issues without jumping to solutions. Use this skill when facilitating strategic discussions, exploring vision and constraints, or serving as a thinking partner. (`skills/strategic-partner`)
- **tasks** - This skill provides expertise for task management operations using the academicOps task scripts. Use when agents or subagents need to create, view, update, or archive tasks in the knowledge base. Includes prioritization framework, duplicate checking protocols, and strategic alignment enforcement. (`skills/tasks`)
- **test-writing** - This skill should be proactively used for all test creation and editing tasks. It enforces integration test patterns using real configurations and data, follows TDD methodology, and eliminates brittle unit tests. The skill ensures tests use real_bm or real_conf fixtures, never mock internal code, and test business behaviors rather than implementation details. Use this skill whenever writing new tests or refactoring existing test suites. (`skills/test-writing`)

### Commands (8)

Slash commands that load additional context:

- **/STRATEGIST** - Strategic thinking partner that facilitates planning while silently capturing context (`commands/STRATEGIST.md`)
- **/analyst** - Load analyst skill for academic research data analysis (dbt & Streamlit) (`commands/analyst.md`)
- **/dev** - Load development workflow and coding standards (`commands/dev.md`)
  - Loads: DEVELOPMENT.md, TESTING.md, DEBUGGING.md, STYLE.md (3-tier: framework → personal → project)
- **/email** - Check email, automatically update task database, and present digest (`commands/email.md`)
- **/error** - Quick experiment outcome logging to academicOps - works from any repository (`commands/error.md`)
- **/log-failure** - Log agent performance failure to experiment tracking system (`commands/log-failure.md`)
- **/ops** - academicOps framework help and commands (`commands/ops.md`)
- **/trainer** - Activate agent trainer mode (`commands/trainer.md`)

### Hooks (16)

Validation and enforcement hooks:

- **autocommit_tasks** - Main hook entry point. (`hooks/autocommit_tasks.py`)
- **hook_debug** - Safely log hook invocation to a session-based JSONL debug file. (`hooks/hook_debug.py`)
- **hook_models** - Complete output structure for Stop/SubagentStop hooks. (`hooks/hook_models.py`)
- **load_instructions** - Generate a manifest of available bot instruction files. (`hooks/load_instructions.py`)
- **log_notification** - Main hook entry point - logs and continues. (`hooks/log_notification.py`)
- **log_posttooluse** - Main hook entry point - logs and continues. (`hooks/log_posttooluse.py`)
- **log_precompact** - Main hook entry point - logs and continues. (`hooks/log_precompact.py`)
- **log_session_stop** - Main hook entry point. (`hooks/log_session_stop.py`)
- **log_sessionend** - Main hook entry point - logs and continues. (`hooks/log_sessionend.py`)
- **log_subagentstop** - Main hook entry point - logs and continues. (`hooks/log_subagentstop.py`)
- **log_todowrite** - Main hook entry point. (`hooks/log_todowrite.py`)
- **log_userpromptsubmit** - Main hook entry point - logs and continues. (`hooks/log_userpromptsubmit.py`)
- **request_scribe_stop** - Main hook entry point. (`hooks/request_scribe_stop.py`)
- **stack_instructions** - PostToolUse hook entry point. (`hooks/stack_instructions.py`)
- **validate_stop** - Main hook entry point with robust error handling. (`hooks/validate_stop.py`)
- **validate_tool** - Main hook entry point. (`hooks/validate_tool.py`)

### Core Instructions

- **File**: `core/_CORE.md`
- **References**: 3 chunks
  - `../chunks/AXIOMS.md`
  - `../chunks/INFRASTRUCTURE.md`
  - `../chunks/AGENT-BEHAVIOR.md`

### Instruction Files

Reverse index showing which components load each instruction file:

**./:**

- `DEBUGGING.md` - Used by: /dev command
- `DEVELOPMENT.md` - Used by: /dev command
- `STYLE.md` - Used by: /dev command
- `TESTING.md` - Used by: /dev command

**chunks/:**

- `AXIOMS.md` - Used by: aops-trainer skill
- `INFRASTRUCTURE.md` - Used by: aops-trainer skill
- `SKILL-PRIMER.md` - Used by: aops-trainer skill

**docs/_CHUNKS/:**

- `FAIL-FAST.md` - Used by: git-commit skill
- `GIT-WORKFLOW.md` - Used by: git-commit skill
- `MATPLOTLIB.md` - Used by: analyst skill
- `PYTHON-DEV.md` - Used by: analyst skill
- `SEABORN.md` - Used by: analyst skill
- `STATSMODELS.md` - Used by: analyst skill
- `TESTS.md` - Used by: git-commit skill

<!-- INSTRUCTION_TREE_END -->

## Context Architecture: Modular Chunks

**Problem**: Skills don't receive SessionStart hooks, so they lack framework context.

**Solution**: Modular `chunks/` with symlinks to skill `resources/` directories.

```
chunks/AXIOMS.md (single source)
    ↓ @reference from core/_CORE.md (agents receive via SessionStart)
    ↓ symlink to skills/*/resources/AXIOMS.md (skills load explicitly)
```

**Benefits**:
- ✅ DRY compliant (single source via filesystem symlinks)
- ✅ Skills know framework paths, conventions, axioms
- ✅ No duplication between _CORE.md and skill context
- ✅ Live integration tests verify infrastructure works

See `tests/test_chunks_loading.py` for verified behavior.

## Slash Commands

- `/analyst` - Data analysis (dbt & Streamlit)
- `/dev` - Development workflow and TDD
- `/email` - Email processing and task extraction
- `/error` - Quick experiment logging
- `/STRATEGIST` - Planning and context capture
- `/trainer` - Framework maintenance
- `/ttd` - Test-driven development methodology

## Skills

Portable workflows installed to `~/.claude/skills/`:

**Framework maintenance**: aops-trainer, skill-creator, skill-maintenance, claude-hooks, claude-md-maintenance

**Development**: test-writing, git-commit

**Documents**: pdf, docx, pptx, xlsx

**Academic**: analyst, archiver

**Context**: scribe (silent capture), strategic-partner

Skills are invoked automatically by agents or explicitly via Skill tool.

## Automated Enforcement

### Claude Code Hooks

- **SessionStart**: Loads 3-tier `_CORE.md` (framework → personal → project)
- **PreToolUse**: Validates tool calls, blocks `.md` creation, requires `uv run python`
- **SubagentStop/Stop**: Validates agent completion

### Git Pre-Commit Hooks

- Documentation bloat prevention (blocks new `.md` files)
- Python quality (ruff, mypy, pytest)

## Installation

See `INSTALL.md` for detailed setup.

## Testing

```bash
# Run all tests
uv run pytest

# Test chunks infrastructure
uv run pytest tests/test_chunks_loading.py -v
```

## Architecture

See `ARCHITECTURE.md` for system design.
