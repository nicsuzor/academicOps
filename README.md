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

### Quick Stats

- 7 agents, 19 skills, 8 commands, 16 hooks
- 22 instruction files
- ⚠️ **6 orphaned files**: AGENT-BEHAVIOR.md, INSTRUCTIONS.md, DBT.md, HYDRA.md, README.md, STREAMLIT.md

**Potential overlaps:**
- ⚠️ `scribe` vs `task-manager` - both extract tasks from conversations

### Agents (7)

- ANALYST - An agent for data analysis
- DEVELOPER - A specialized developer. Your purpose is to write
- STRATEGIST - Strategic thinking partner for planning, task review, and context navigation
- SUPERVISOR - Orchestrates multi-agent workflows with comprehensive quality gates, test-first development, and
- end-of-session - Automated end-of-session workflow that orchestrates commit and accomplishment capture when
- scribe - Silent background processor that automatically captures tasks, priorities, and context
- task-manager - EXPERIMENTAL silent background processor that extracts tasks from emails and

### Skills (19)

- agent-initialization - This skill should be automatically invoked when initializing a workspace
- analyst - Support academic research data analysis using dbt and Streamlit [MATPLOTLIB, STATSMODELS, PYTHON-DEV, SEABORN]
- aops-bug - Track bugs, agent violations, and framework improvements in the academicOps
- aops-trainer - This skill should be used when reviewing and improving agents, [AXIOMS, SKILL-PRIMER, INFRASTRUCTURE]
- archiver - Archive experimental analysis and intermediate work into long-lived Jupyter notebooks
- claude-hooks - This skill should be used when working with Claude Code
- claude-md-maintenance - This skill maintains CLAUDE.md files across repositories by extracting substantive
- document-skills
- email - This skill provides expertise for interacting with Outlook email via
- git-commit - This skill should be used when committing code changes to [FAIL-FAST, TESTS, GIT-WORKFLOW]
- github-issue - Manage GitHub issues across any repository with exhaustive search, precise
- no-throwaway-code - Intervention skill that triggers when agents attempt temporary/throwaway Python code
- pdf - This skill should be used when converting markdown documents to
- scribe - A scribe automatically and silently captures tasks, priorities, and context
- skill-creator - Guide for creating effective skills
- skill-maintenance - This skill should be used for ongoing skill maintenance and
- strategic-partner - This skill provides strategic facilitation, questioning frameworks, and thinking partnership
- tasks - This skill provides expertise for task management operations using the
- test-writing - This skill should be proactively used for all test creation

### Commands (8)

- /STRATEGIST - Strategic thinking partner that facilitates planning while silently capturing context
- /analyst - Load analyst skill for academic research data analysis
- /dev - Load development workflow and coding standards
- /email - Check email, automatically update task database, and present digest
- /error - Quick experiment outcome logging to academicOps
- /log-failure - Log agent performance failure to experiment tracking system
- /ops - academicOps framework help and commands
- /trainer - Activate agent trainer mode

### Hooks (16)

- autocommit_tasks - Main hook entry point.
- hook_debug - Safely log hook invocation to a session-based JSONL debug file.
- hook_models - Complete output structure for Stop/SubagentStop hooks.
- load_instructions - Generate a manifest of available bot instruction files.
- log_notification - Main hook entry point
- log_posttooluse - Main hook entry point
- log_precompact - Main hook entry point
- log_session_stop - Main hook entry point.
- log_sessionend - Main hook entry point
- log_subagentstop - Main hook entry point
- log_todowrite - Main hook entry point.
- log_userpromptsubmit - Main hook entry point
- request_scribe_stop - Main hook entry point.
- stack_instructions - PostToolUse hook entry point.
- validate_stop - Main hook entry point with robust error handling.
- validate_tool - Main hook entry point.

### Instruction Flow

**SessionStart (all agents)**
└─ core/_CORE.md
   ├─ ../chunks/AXIOMS.md
   ├─ ../chunks/INFRASTRUCTURE.md
   └─ ../chunks/AGENT-BEHAVIOR.md

**/dev command** (3-tier)
├─ DEVELOPMENT.md
├─ TESTING.md
├─ DEBUGGING.md
└─ STYLE.md

**Skills**
├─ analyst → MATPLOTLIB.md, STATSMODELS.md, PYTHON-DEV.md, SEABORN.md
├─ git-commit → FAIL-FAST.md, TESTS.md, GIT-WORKFLOW.md
└─ aops-trainer → AXIOMS.md, SKILL-PRIMER.md, INFRASTRUCTURE.md

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
