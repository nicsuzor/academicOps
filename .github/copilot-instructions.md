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
uv run pytest tests/test_hooks.py -v

# Lint and format (MUST pass before committing)
uv run ruff check --fix . && uv run ruff format .  # Python
uv run dprint fmt                                     # Markdown/JSON/TOML

# Type checking
uv run basedpyright
```

## Project Structure

```
academicOps/
├── .agents/           # Rules for agents working ON this repo (READ-ONLY reference)
│   ├── rules/        # RULES.md (project-specific rules; axioms live in lib/axioms/)
│   └── skills/       # Meta skills for this repo's own dev workflow
├── .github/
│   ├── agents/       # Agent prompts (enforcer, mechanic, qa, pre-admission-responder)
│   └── workflows/    # GitHub Actions
├── lib/               # Shared source, injected into plugins at build time
│   ├── axioms/       # The axioms (single source of truth)
│   ├── hooks/         # Shared hook runtime
│   └── py/            # Shared Python helpers
├── build/              # Build system (build.py, install.py, client adapters)
├── plugins/            # Plugin sources: aops, pkb, ida, cope, ts, tools
│   └── aops/polecat/  # Polecat container executor
├── tests/              # Test suite, mirroring the source structure
└── specs/              # Design specifications
```

## Coding Conventions

### Python

- **Python 3.11+** required.
- **Fail-fast**: No defaults, no fallbacks, no silent failures. Raise exceptions early.
- **Type hints**: Use throughout. Pydantic for data models.
- **Imports**: Use absolute imports from `lib/hooks/`.
- **Line length**: 100 characters (ruff configured).
- **Tests**: Place in `tests/` at repo root, NOT inside `plugins/`. Mirror the source structure.

### Commit Messages

Use descriptive messages. Include task ID if working on a tracked task:

```
<descriptive summary>

Closes: <task-id>
```

### Key Principles (from `lib/axioms/`)

- **`do-one-thing`**: Complete the assigned task, nothing more. No scope creep.
- **`halt-on-failure`**: No workarounds. If something fails, stop and report. Never use `--no-verify`, `--force`, or skip flags.
- **`single-source-of-truth`**: Never create backup files (`.bak`, `_old`). Git is the backup system.
- **`honest-epistemics`**: Check actual state, never assume.
- **No single-use scripts.** Write proper tests.

### What NOT to Do

- Do NOT modify files under `.agents/rules/` — these are inviolable.
- Do NOT add tests inside `plugins/` — tests go in the root `tests/` directory.
- Do NOT create backup or archive files — git is the backup system.
- Do NOT disable pre-commit hooks or CI checks.
- Do NOT modify `.github/workflows/` without explicit justification.

## Pre-commit Hooks

This project uses pre-commit hooks: dprint (markdown/json/toml) only — see
`.pre-commit-config.yaml`. Run `uv run pre-commit run --all-files` to check before committing.
Ruff and basedpyright are enforced separately, by `make lint` / CI, not by pre-commit.

## PR Review Pipeline

PRs are reviewed by automated agents (enforcer/rbg + qa/marsha in Stage 1, mechanic in
Stage 2 after the human Environment-gate approval). The pipeline runs on PR open/push.
Write clear PR descriptions explaining what changed and why — the agents use this to
evaluate scope compliance.
