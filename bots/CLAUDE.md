# Bot Framework Development Context

@../agents/_CORE.md
@../docs/_CHUNKS/FAIL-FAST.md

## Repository Structure

This directory contains the core academicOps framework:

- `agents/` - Agent instruction files
- `hooks/` - Hook scripts for Claude Code
- `prompts/` - Legacy instruction files (being migrated to skills)

## Development Standards

- Python 3.12+ with uv package manager
- Type hints required
- Pydantic for configuration
- pytest for testing
- No defaults, explicit configuration only

## Hook Development

Hooks must:
- Be executable (`chmod +x`)
- Accept JSON on stdin
- Output JSON on stdout
- Fail gracefully (exit 0 even on error)
- Use `uv run --directory "$ACADEMICOPS_BOT"` for dependencies
