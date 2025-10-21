# Script Development Standards

@../agents/_CORE.md
@../docs/_CHUNKS/FAIL-FAST.md

## Key Principles

- **Scripts must be executable in git**: `git update-index --chmod=+x script.sh`
- **Fail-fast**: No defensive programming, no error recovery
- **Explicit configuration**: Use Pydantic, no defaults
- **Standard tools**: Use `uv run python` for Python scripts

## What NOT to Do

❌ Check if script exists before running
❌ Verify permissions before executing
❌ Try/except with fallback values
❌ Retry on failure

## What to Do Instead

✅ Make scripts reliable in repository
✅ Fail immediately if configuration missing
✅ Report errors and stop
✅ Let trainer fix infrastructure issues
