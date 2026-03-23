# academicOps Project Context

This project contains the **academicOps** framework itself. You are currently working on the framework's source code.

## Key Components

- **.agent/**: Instructions for working on the framework
- **aops-core/**: Framework core (hooks, enforcement, skills)
- **aops-tools/**: Additional tools and utilities
- **specs/**: Framework specifications and architecture
- **tests/**: All tests (at repo root, NOT in aops-core/). Subdirs: `hooks/`, `integration/`, `lib/`, `e2e/`

## Development Procedures

- **Pre-commit Hooks**: Run `./scripts/format.sh` before committing to avoid failures.
- **Testing**: Run tests using `uv run pytest tests/` or `uv run pytest aops-core/`.
- **Building**: Use `uv run python scripts/build.py` to build the distribution.
- **Installing**: Use `./setup.sh` or `uv run python scripts/install.py` to install locally.

## PR Review Management

- **Dismiss stale reviews** when you have addressed the reviewer's concerns or the human has overridden them.
- **Always include a clear dismissal message** explaining why: what was fixed, or which human decision overrides the concern.
- **Never dismiss a review you haven't addressed.**

See [[README.md]] for framework usage documentation.
