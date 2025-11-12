# Framework Testing

Comprehensive test suite for the bots automation framework. Tests validate path resolution, documentation integrity, session start loading, and skill functionality.

## Test Organization

```
bots/tests/
├── conftest.py                      # Unit test fixtures (paths)
├── paths.py                         # Path resolution utilities
├── test_conftest.py                 # Fixture validation tests
├── test_paths.py                    # Path resolution tests
├── test_skills_readme_integrity.py  # Skills documentation tests
├── test_session_start_loading.py    # Session start file tests
├── test_core_md_task_guidance.py    # CORE.md guidance tests
└── integration/
    ├── conftest.py                  # Integration test fixtures
    ├── test_session_start_content.py # Session start E2E tests
    ├── test_headless_fixture.py     # Headless execution tests
    └── test_bmem_skill.py           # Bmem skill integration tests
```

## Test Categories

### Unit Tests (Fast, Default)

Run by default. Complete in ~4 seconds with 20 parallel workers.

**Path Resolution** (`test_paths.py`): 10 tests

- Writing root discovery (env var + file location)
- Subdirectory resolution (bots/, data/, hooks/)
- Hook script resolution
- Pathlib type enforcement
- Error handling for missing paths

**Fixtures** (`test_conftest.py`): 4 tests

- Pytest fixture validation
- Path fixture consistency

**Documentation Integrity**: 5 tests

- Skills README structure and content (`test_skills_readme_integrity.py`)
- Session start file references (`test_session_start_loading.py`)
- Task guidance in CORE.md (`test_core_md_task_guidance.py`)

**Total**: 20 unit tests

### Integration Tests (Require `-m integration`)

**Fast Integration Tests**: 7 tests (no Claude execution)

- Session start file validation
- Directory structure verification
- Documentation reference checking

**Slow Integration Tests**: 10 tests (require Claude Code execution)

- Headless execution fixture (8 tests)
- Session start content loading (2 tests)
- Bmem skill functionality (4 tests)

**Total**: 17 integration tests

## Running Tests

### Default: Fast Unit Tests Only

```bash
uv run pytest bots/tests/
```

Runs 20 unit tests in ~4 seconds. This is the default configuration in `pyproject.toml`.

### Fast Integration Tests

```bash
uv run pytest bots/tests/ -m "integration and not slow"
```

Adds 7 fast integration tests (~5 seconds total).

### All Integration Tests (Including Slow)

```bash
uv run pytest bots/tests/ -m integration
```

Runs all 17 integration tests. Slow tests execute Claude Code in headless mode (~60-180 seconds each).

### Slow Tests Only

```bash
uv run pytest bots/tests/ -m slow
```

Runs only the 10 slow integration tests that require Claude execution.

### Everything

```bash
uv run pytest bots/tests/ --deselect-marker=endtoend
```

Runs all tests except end-to-end tests that require real API credentials.

### Specific Test Files

```bash
# Path resolution tests
uv run pytest bots/tests/test_paths.py -v

# Documentation integrity tests
uv run pytest bots/tests/test_skills_readme_integrity.py -v

# Session start tests (fast only)
uv run pytest bots/tests/integration/test_session_start_content.py -m "not slow" -v

# Bmem skill tests
uv run pytest bots/tests/integration/test_bmem_skill.py -m integration -v
```

## Test Configuration

Configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
  "integration: integration tests (slower, mocked and faked at the edges)",
  "endtoend: tests that require real API calls with valid credentials",
  "slow: mark tests as slow (deselect with '-m \"not slow\"')",
]

timeout = 120
asyncio_default_fixture_loop_scope = "package"
asyncio_debug = true
addopts = [
  "--durations=10",
  "-n 20", # 20 parallel workers
  "-v",
  "-rfEX",
  "-s",
  "-m not slow and not integration", # Default: fast unit tests only
  "--tb=short",
]
```

## Test Infrastructure

### Fixtures

**Unit Test Fixtures** (`bots/tests/conftest.py`):

- `writing_root`: Path to repository root
- `bots_dir`: Path to bots/ directory
- `data_dir`: Path to data/ directory
- `hooks_dir`: Path to bots/hooks/ directory

**Integration Test Fixtures** (`bots/tests/integration/conftest.py`):

- `claude_headless`: Execute Claude Code in headless mode
- `run_claude_headless()`: Direct function for headless execution
- `writing_root`: Repository root path
- Auto-marking of integration tests

### Path Utilities (`bots/tests/paths.py`)

Path resolution functions for monorepo structure:

```python
from bots.tests.paths import (
    get_writing_root,    # Find repository root
    get_bots_dir,        # Get bots/ directory
    get_data_dir,        # Get data/ directory
    get_hooks_dir,       # Get bots/hooks/ directory
    get_hook_script,     # Get specific hook script
)
```

Resolution order:

1. `WRITING_ROOT` environment variable (if set)
2. Discover from `__file__` location by traversing up

Fails fast with `RuntimeError` if paths don't exist or can't be determined.

### Headless Execution (`run_claude_headless`)

Execute Claude Code in headless mode for integration testing:

```python
result = claude_headless(
    prompt="What is 2+2?",
    model="claude-sonnet-4-5-20250929",  # Optional
    timeout_seconds=120,                  # Optional
    permission_mode="plan",               # Optional
    cwd=writing_root,                     # Optional
)

# Returns dict with:
# - success (bool): Whether execution succeeded
# - output (str): Raw JSON output
# - result (dict): Parsed JSON result
# - error (str, optional): Error message if failed
```

## Test Coverage

### What We Test

1. **Path Resolution**
   - Environment variable configuration
   - Automatic discovery from file location
   - Subdirectory resolution
   - Error handling for missing paths
   - Type safety (Path objects, not strings)

2. **Documentation Integrity**
   - Skills README structure
   - Session start file references
   - Task skill "when to use" triggers
   - CORE.md task guidance
   - No conflicting path references

3. **Session Start Loading**
   - CLAUDE.md and @-referenced files exist
   - Files are readable
   - Content loads correctly in Claude sessions
   - Agent knows user info and work principles

4. **Bmem Skill Functionality**
   - Creates valid Obsidian-compatible files
   - Proper frontmatter structure
   - Observations add new information
   - Relations use WikiLink syntax
   - Files pass bmem validation

5. **Headless Execution Fixture**
   - Basic execution
   - Parameter passing (model, timeout, permission_mode)
   - JSON output parsing
   - Working directory handling

### What We Don't Test

- End-to-end workflows requiring real API credentials (marked `@pytest.mark.endtoend`)
- User interaction flows
- Git operations
- File system modifications outside test directories

## Writing New Tests

### Unit Tests

Use standard pytest patterns with provided fixtures:

```python
def test_something(bots_dir: Path) -> None:
    """Test description.

    Args:
        bots_dir: Path to bots/ directory (from fixture)

    Raises:
        AssertionError: If test condition fails
    """
    # Arrange
    expected_file = bots_dir / "CORE.md"

    # Act
    exists = expected_file.exists()

    # Assert
    assert exists, f"CORE.md not found at {expected_file}"
```

### Integration Tests (Fast)

Tests that validate configuration but don't execute Claude:

```python
@pytest.mark.integration
def test_config_valid(writing_root: Path) -> None:
    """Test configuration file is valid."""
    config_file = writing_root / ".claude" / "claude_desktop_config.json"

    assert config_file.exists()

    import json
    config = json.loads(config_file.read_text())

    assert "mcpServers" in config
```

### Integration Tests (Slow)

Tests that execute Claude Code in headless mode:

```python
@pytest.mark.slow
@pytest.mark.integration
def test_agent_behavior(claude_headless, writing_root: Path) -> None:
    """Test agent knows expected information.

    Args:
        claude_headless: Fixture for headless Claude execution
        writing_root: Path to repository root
    """
    result = claude_headless(
        prompt="What is my name?",
        timeout_seconds=60,
        cwd=writing_root,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    response = result.get("result", {}).get("result", "")
    assert "Nic" in response, f"Agent doesn't know user. Response: {response}"
```

## Test Markers

Use markers to categorize tests:

- `@pytest.mark.integration`: Test requires integration components (auto-added for tests in `integration/`)
- `@pytest.mark.slow`: Test takes >5 seconds to run (typically Claude execution)
- `@pytest.mark.endtoend`: Test requires real API credentials

## Debugging Tests

### Verbose Output

```bash
uv run pytest bots/tests/test_paths.py -v --tb=long
```

### Single Test

```bash
uv run pytest bots/tests/test_paths.py::TestGetWritingRoot::test_get_writing_root_from_env -v
```

### Print Statements

```bash
uv run pytest bots/tests/ -s  # Already in default config
```

### Failed Tests Only

```bash
uv run pytest bots/tests/ --lf  # Last failed
uv run pytest bots/tests/ --ff  # Failed first, then others
```

### Coverage Report

```bash
uv run pytest bots/tests/ --cov=bots --cov-report=html
```

## Continuous Integration

Tests run automatically on:

- Pre-commit hooks (fast unit tests only)
- Pull requests (all non-slow tests)
- Scheduled runs (all tests including slow)

See `.github/workflows/` for CI configuration.

## Philosophy

Following `AXIOMS.md`:

1. **Fail-Fast**: Tests fail immediately with clear error messages. No silent failures or workarounds.

2. **Self-Documenting**: Tests document expected behavior. Test names explain what they validate.

3. **DRY and Modular**: Fixtures provide reusable test infrastructure. Common utilities in `paths.py`.

4. **Standard Tools**: Uses pytest, standard test patterns, type hints.

5. **No Defaults**: Tests explicitly check for required configuration. No fallback behavior.

6. **Integration-First**: Integration tests validate real behavior, not just unit-level correctness.

## Current Status

**Unit Tests**: 20/20 passing (100%) ✅

**Fast Integration Tests**: 6/9 passing (67%)

- Fixed: test_no_conflicting_path_references (CORE.md now includes data/tasks/ path)
- Fixed: Invalid permission_mode (changed "disabled" to "bypassPermissions")
- Remaining failures: 3 bmem validation tests (pre-existing data format issues in data/goals/)

**Slow Integration Tests**: 8/11 passing (73%)

- Passing: test_bmem_skill_creates_valid_file (permission_mode fix verified)
- Passing: All 7 headless fixture tests
- Failing: 2 session start tests (timeout issues - need 120s not 60s)
- Failing: 1 bmem test (test design issue, unrelated to permission_mode)

**Fixes Applied** (commit ae388b0):

- Added explicit "data/tasks/" path reference to CORE.md
- Changed 4 instances of permission_mode from "disabled" to "bypassPermissions"

Run tests to validate framework integrity:

```bash
uv run pytest bots/tests/ -v
```
