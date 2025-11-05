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

- **ANALYST** (`agents/ANALYST.md`)
- **DEVELOPER** (`agents/DEVELOPER.md`)
- **STRATEGIST** (`agents/STRATEGIST.md`)
- **SUPERVISOR** (`agents/SUPERVISOR.md`)
- **end-of-session** (`agents/end-of-session.md`)
- **scribe** (`agents/scribe.md`)
- **task-manager** (`agents/task-manager.md`)

### Skills (19)

Packaged workflows installed to `~/.claude/skills/`:

- **agent-initialization** (`skills/agent-initialization`)
- **analyst** (`skills/analyst`)
- **aops-bug** (`skills/aops-bug`)
- **aops-trainer** (`skills/aops-trainer`)
- **archiver** (`skills/archiver`)
- **claude-hooks** (`skills/claude-hooks`)
- **claude-md-maintenance** (`skills/claude-md-maintenance`)
- **document-skills** (`skills/document-skills`)
- **email** (`skills/email`)
- **git-commit** (`skills/git-commit`)
- **github-issue** (`skills/github-issue`)
- **no-throwaway-code** (`skills/no-throwaway-code`)
- **pdf** (`skills/pdf`)
- **scribe** (`skills/scribe`)
- **skill-creator** (`skills/skill-creator`)
- **skill-maintenance** (`skills/skill-maintenance`)
- **strategic-partner** (`skills/strategic-partner`)
- **tasks** (`skills/tasks`)
- **test-writing** (`skills/test-writing`)

### Commands (8)

Slash commands that load additional context:

- **/STRATEGIST** (`commands/STRATEGIST.md`)
- **/analyst** (`commands/analyst.md`)
- **/dev** (`commands/dev.md`)
- **/email** (`commands/email.md`)
- **/error** (`commands/error.md`)
- **/log-failure** (`commands/log-failure.md`)
- **/ops** (`commands/ops.md`)
- **/trainer** (`commands/trainer.md`)

### Hooks (16)

Validation and enforcement hooks:

- **autocommit_tasks** (`hooks/autocommit_tasks.py`)
- **hook_debug** (`hooks/hook_debug.py`)
- **hook_models** (`hooks/hook_models.py`)
- **load_instructions** (`hooks/load_instructions.py`)
- **log_notification** (`hooks/log_notification.py`)
- **log_posttooluse** (`hooks/log_posttooluse.py`)
- **log_precompact** (`hooks/log_precompact.py`)
- **log_session_stop** (`hooks/log_session_stop.py`)
- **log_sessionend** (`hooks/log_sessionend.py`)
- **log_subagentstop** (`hooks/log_subagentstop.py`)
- **log_todowrite** (`hooks/log_todowrite.py`)
- **log_userpromptsubmit** (`hooks/log_userpromptsubmit.py`)
- **request_scribe_stop** (`hooks/request_scribe_stop.py`)
- **stack_instructions** (`hooks/stack_instructions.py`)
- **validate_stop** (`hooks/validate_stop.py`)
- **validate_tool** (`hooks/validate_tool.py`)

### Core Instructions

- **File**: `core/_CORE.md`
- **References**: 3 chunks
  - `../chunks/AXIOMS.md`
  - `../chunks/INFRASTRUCTURE.md`
  - `../chunks/AGENT-BEHAVIOR.md`

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
