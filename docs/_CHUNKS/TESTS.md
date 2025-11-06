Follow coding standards in `bot/agents/DEVELOPER.md`

## Test File Standards

- TTD is non-negotiable. You may and must commit failing tests before writing implementation code.
- Tests are ONLY created in tests/ directories and are designed to last (no single use tests)
- Tests use REAL fixtures that work with our EXISTING initialisation and configuration process
- Tests NEVER mock or fake internal logic or objects. Any tests that operate WITHIN the bounds of our codebase MUST be live code
- Async tests are decorated with `@pytest.mark.anyio`

## CRITICAL VALIDATION RULE: Config Loading in Tests

**Applies to**: All files in `tests/` directories

### Requirements
- ✅ MUST use `real_bm` or `real_conf` fixtures from conftest.py
- ❌ MUST NOT use `initialize_config_dir()`
- ❌ MUST NOT use `compose()`
- ❌ MUST NOT use `GlobalHydra`
- ❌ MUST NOT create fixtures that load Hydra configs

### Detection Patterns (for code review)
Search test files for these FORBIDDEN patterns:
- `initialize_config_dir`
- `compose(`
- `GlobalHydra`
- `@pytest.fixture` followed by Hydra config loading

### If Violated
**BLOCK commit** with message:
"Test file {filename} loads configs directly. Use real_bm or real_conf fixtures instead. See TEST-CLEANER.md for details."
