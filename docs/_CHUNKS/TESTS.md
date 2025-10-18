Follow coding standards in `bot/agents/DEVELOPER.md`

## Test files

- TTD is non-negotiable. You may and must commit failing tests before writing impelmentation code.
- Tests are ONLY created in tests/ directories and are designed to last (no single use tests)
- Tests use REAL fixtures that work with our EXISTING initialisation and configuration process
- Tests NEVER mock or fake internal logic or objects. Any tests that operate WITHIN the bounds of our codebase MUST be live code
- Async tests are decorated with `@pytest.mark.anyio`

