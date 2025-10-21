# Python Development Context

When working in this Python codebase, follow these standards:

@../agents/_CORE.md
@../docs/_CHUNKS/FAIL-FAST.md
@../.claude/skills/python-dev/SKILL.md

## Key Principles

- Fail-fast: No defaults, no `.get(key, default)`, explicit configuration
- Type safety: Use Pydantic for validation
- Standard tools: `uv` for package management, `pytest` for testing
- Self-documenting code: Clear names, type hints, docstrings
