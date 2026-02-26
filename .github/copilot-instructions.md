# academicOps — Copilot Coding Agent Instructions

## Project Overview

academicOps (aops) is a Python framework for managing academic workflows through
LLM-driven automation with structured enforcement, task management, and governance.

## Build & Test

```bash
# Install dependencies (Python 3.11+, managed by uv)
uv sync --dev

# Run tests (parallel by default, excludes slow tests)
uv run pytest

# Run specific test file
uv run pytest tests/hooks/test_router.py -v

# Lint and format (MUST pass before committing)
uv run ruff check --fix . && uv run ruff format .  # Python
uv run dprint fmt                                     # Markdown/JSON/TOML

# Type checking
uv run basedpyright
```

## Project Structure

```
academicOps/
├── .agent/           # Agent instructions, rules, skills (READ-ONLY reference)
│   ├── rules/        # AXIOMS.md (inviolable principles)
│   └── skills/       # Domain skills
├── .github/
│   ├── agents/       # Agent personas (gatekeeper, custodiet, qa, etc.)
│   └── workflows/    # GitHub Actions (18 workflows)
├── aops-core/        # Framework core
│   ├── hooks/        # Session lifecycle hooks
│   ├── lib/          # Shared libraries (gates, hydration, tasks, etc.)
│   ├── mcp_servers/  # MCP servers (tasks, memory)
│   └── scripts/      # Utility scripts
├── tests/            # All tests (unit, integration, e2e)
│   ├── hooks/
│   ├── integration/
│   ├── lib/
│   └── e2e/
├── specs/            # Design specifications
└── config/           # Configuration files
```

## Coding Conventions

### Python

- **Python 3.11+** required.
- **Fail-fast**: No defaults, no fallbacks, no silent failures. Raise exceptions early.
- **Type hints**: Use throughout. Pydantic for data models.
- **Imports**: Use absolute imports from `aops-core/lib/`, `aops-core/hooks/`.
- **Line length**: 100 characters (ruff configured).
- **Tests**: Place in `tests/` at repo root, NOT inside `aops-core/`. Mirror the source structure.

### Commit Messages

Use descriptive messages. Include task ID if working on a tracked task:

```
<descriptive summary>

Closes: <task-id>
```

### Key Principles (from AXIOMS.md)

- **Do One Thing (P#5)**: Complete the assigned task, nothing more. No scope creep.
- **Fail-Fast (P#8, P#9)**: No workarounds. If something fails, stop and report.
- **No Workarounds (P#25)**: Never use `--no-verify`, `--force`, or skip flags.
- **Trust Version Control (P#24)**: Never create backup files (`.bak`, `_old`).
- **Write For The Long Term (P#28)**: No single-use scripts. Write proper tests.
- **Verify First (P#26)**: Check actual state, never assume.

### What NOT to Do

- Do NOT modify files under `.agent/rules/` — these are inviolable.
- Do NOT add tests inside `aops-core/` — tests go in the root `tests/` directory.
- Do NOT create backup or archive files — git is the backup system.
- Do NOT disable pre-commit hooks or CI checks.
- Do NOT modify `.github/workflows/` without explicit justification.

## Pre-commit Hooks

This project uses pre-commit hooks: dprint (markdown/json/toml), markdownlint,
trailing-whitespace, end-of-file-fixer, check-yaml, check-json, ruff (lint + format),
workflow-length-check. Run `uv run pre-commit run --all-files` to check before committing.

## PR Review Pipeline

PRs are reviewed by automated agents (gatekeeper, custodiet, QA, merge-prep).
The pipeline runs on PR open/push. Write clear PR descriptions explaining what
changed and why — the agents use this to evaluate scope compliance.
