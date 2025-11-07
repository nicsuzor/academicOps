# Integration Test Guidelines

@../../docs/TESTING.md @../../docs/_CHUNKS/TESTS.md

## Critical Rules

- **ALWAYS use `model="haiku"`** for Claude invocations (15x cheaper than Sonnet)
- Test integration points, NOT business logic (that's for unit tests)
- Keep tests under 30s timeout
- Use `claude_headless()` fixture from conftest.py
- Maximum ~5-7 tests per integration boundary

## What to Test

✅ Hook output → Claude Code → tool execution ✅ Agent type detection → hook receives correct metadata ✅ Permission decision → Claude response behavior

## What NOT to Test

❌ Business logic (covered by unit tests) ❌ LLM intelligence (we test machinery, not reasoning) ❌ Multiple scenarios of same pattern (one test per pattern)

See TESTING.md for detailed philosophy and examples.
