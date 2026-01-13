# Archived Tests

Tests archived during v1.0 migration (2026-01-13).

## Why Archived

These tests cover v0.x framework components that were replaced by the v1.0 architecture:

1. **v0-hooks**: Tests for individual hook modules that were consolidated into `aops-core/hooks/`
   - Old: separate `hooks/skill_monitor.py`, `hooks/criteria_gate.py`, etc.
   - New: unified router in `aops-core/hooks/router.py`

2. **v0-lib**: Tests for old session state APIs
   - Old: `HydratorState`, `CustodietState` separate classes/files
   - New: unified `SessionState` in `lib/session_state.py`

3. **v0-integration**: Integration tests for old hook coordination
   - Old: `policy_enforcer.py`, `autocommit_state.py`, gate coordination
   - New: Simplified flow via `aops-core/` plugin structure

4. **v0-skills**: Tests for skills that were moved to `archived/skills/`
   - These skills exist but are not part of v1.0 core

## Restoration

If any archived component is restored to active development:
1. Move the test file back to `tests/` proper
2. Update imports to match current module structure
3. Verify tests pass with current APIs

## Source Modules

The modules these tests were written for now live in:
- `archived/hooks/` - v0.x hook scripts
- `archived/skills/` - v0.x skills
