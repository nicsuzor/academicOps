# Test Development Context

@../agents/_CORE.md @../docs/_CHUNKS/FAIL-FAST.md @../.claude/skills/test-writing/SKILL.md

## Testing Philosophy

- Integration tests using real configurations and data
- Never mock internal code
- Test business behaviors, not implementation details
- Use real_bm or real_conf fixtures

## Test Organization

- Tests mirror source structure
- One test file per module
- Clear, descriptive test names
- Arrange-Act-Assert pattern

## Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_module.py

# With coverage
uv run pytest --cov=src
```
