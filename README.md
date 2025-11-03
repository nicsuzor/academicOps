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
