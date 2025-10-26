# Validation Rules Reference

Common validation patterns for code quality gates.

## Core Principles

1. **Fail-Fast**: No defaults, no fallbacks, explicit configuration required
2. **Real Fixtures**: Tests use real objects, never mock internal code
3. **TDD**: Tests exist before implementation
4. **No Secrets**: Never commit credentials, API keys, `.env` files
5. **Explicit Config**: All configuration in YAML files, not code or environment variables

## File-Specific Rules

### Test Files (`test_*.py`, `tests/**/*.py`)

**Required Patterns**:
- ✅ MUST use `real_bm` or `real_conf` fixtures from conftest
- ✅ MUST use `@pytest.mark.anyio` for async tests
- ✅ MUST test against real data and live configured objects

**Forbidden Patterns**:
- ❌ MUST NOT use `initialize_config_dir()`
- ❌ MUST NOT use `compose()` directly
- ❌ MUST NOT use `GlobalHydra`
- ❌ MUST NOT create fixtures that load Hydra configs
- ❌ MUST NOT mock internal code (only external APIs)

**Detection**:
```python
# Search test files for these forbidden patterns:
grep -n "initialize_config_dir" tests/**/*.py
grep -n "compose(" tests/**/*.py
grep -n "GlobalHydra" tests/**/*.py
```

**Example Violation**:
```python
# ❌ WRONG
def test_config():
    initialize_config_dir(config_path="conf")
    cfg = compose(config_name="config")

# ✅ CORRECT
def test_config(real_bm):
    # real_bm fixture provides configured ButtermilkManager
    assert real_bm.config is not None
```

### Configuration Files (`config/**/*.yaml`, `conf/**/*.yaml`)

**Required Patterns**:
- ✅ MUST use composable YAML structure (Hydra patterns)
- ✅ MUST define all required fields explicitly
- ✅ MUST NOT include sensitive data

**Forbidden Patterns**:
- ❌ MUST NOT reference environment variables directly in YAML
- ❌ MUST NOT include default values for critical settings
- ❌ MUST NOT commit API keys, passwords, or secrets

### Python Source Files (`**/*.py` excluding tests)

**Required Patterns**:
- ✅ MUST access configuration through config objects, not env vars
- ✅ MUST fail immediately if required config missing (`config["key"]`)
- ✅ MUST use type hints for function signatures
- ✅ MUST include docstrings for public functions/classes

**Forbidden Patterns**:
- ❌ MUST NOT use `os.getenv()` or `os.environ`
- ❌ MUST NOT use `.get(key, default)` for required config
- ❌ MUST NOT use bare `except:` clauses
- ❌ MUST NOT have hardcoded file paths (use config or Path)

**Example Violation**:
```python
# ❌ WRONG - uses default fallback
api_key = config.get("api_key", "default_key")

# ✅ CORRECT - fails fast if missing
api_key = config["api_key"]  # Raises KeyError if not configured
```

## Language-Specific Standards

### Python

- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use f-strings for formatting (not %)
- Use pathlib.Path for file operations (not os.path)
- Async functions must have `async def`

### Markdown

- ATX-style headers (`#` not underlines)
- Fenced code blocks with language tags
- No trailing whitespace
- One blank line between sections

## Project-Wide Conventions

**Required**:
- ✅ All new functionality must have tests
- ✅ Public APIs must have docstrings
- ✅ Breaking changes must update documentation
- ✅ Commit messages follow conventional commits format

**Forbidden**:
- ❌ No commented-out code (delete it, git remembers)
- ❌ No TODO comments without issue references
- ❌ No print() statements (use logging)
- ❌ No debugging code (breakpoints, ipdb, etc.)

## Security Requirements

**Secrets Detection**:
```bash
# Files that should NEVER be committed:
- .env
- .env.*
- **/secrets.*
- **/credentials.*
- **/*_secret.*
- **/*_key.*
- **/*.pem
- **/*.key
```

**Required Checks**:
- ✅ No API keys in source code
- ✅ No passwords in configuration files
- ✅ No AWS credentials in code
- ✅ No database connection strings with passwords
- ✅ `.gitignore` includes all secret file patterns

**Detection Patterns**:
```bash
# Search for common secret patterns:
grep -rn "api[_-]key\s*=\s*['\"]" src/
grep -rn "password\s*=\s*['\"]" src/
grep -rn "secret\s*=\s*['\"]" src/
grep -rn "token\s*=\s*['\"]" src/
```

## Testing Requirements

**Test Coverage**:
- ✅ All new features must have tests
- ✅ Bug fixes must have regression tests
- ✅ Tests must pass before commit
- ✅ Integration tests for API endpoints
- ✅ Unit tests for business logic

**Test Quality**:
- ✅ Tests use descriptive names (`test_user_can_login_with_valid_credentials`)
- ✅ Tests have clear arrange-act-assert structure
- ✅ Tests are independent (can run in any order)
- ✅ Tests clean up after themselves

**Forbidden in Tests**:
- ❌ No time.sleep() (use proper async waits)
- ❌ No random data without seeds
- ❌ No network calls to external services (mock at boundary)
- ❌ No tests marked skip/xfail without issue reference

## Documentation Requirements

**Code Documentation**:
```python
def process_data(data: Dict[str, Any], config: Config) -> Result:
    """Process input data according to configuration.

    Args:
        data: Raw input data dictionary
        config: Processing configuration object

    Returns:
        Processed result object

    Raises:
        ValueError: If data is invalid or missing required fields
        ConfigError: If configuration is incomplete
    """
```

**Project Documentation**:
- ✅ README explains purpose and setup
- ✅ API changes update relevant docs
- ✅ Breaking changes documented in commit message
- ✅ Examples updated when behavior changes

## Repository-Specific Rules

These vary by project. Common locations:

- `docs/agents/CODE.md` - Project coding standards
- `docs/agents/COMMIT.md` - Project commit requirements
- `.github/CONTRIBUTING.md` - Contribution guidelines
- `docs/STYLE_GUIDE.md` - Style preferences

Load and apply these in addition to core rules.

## Validation Workflow

1. **Load all applicable rules** (core + project + user)
2. **Build checklist** from rules
3. **Validate each changed file** against checklist
4. **Collect evidence** for failures (file:line)
5. **Generate report** with pass/fail and remediation
6. **Block commit** if any critical rule fails
7. **Report specific violations** with exact fixes needed

## Common Violations and Fixes

### Violation: Test uses initialize_config_dir

**Detection**: `grep -n "initialize_config_dir" test_*.py`

**Fix**:
```python
# Before
def test_config():
    initialize_config_dir(config_path="conf")
    cfg = compose(config_name="config")

# After
def test_config(real_bm):
    cfg = real_bm.config
```

### Violation: Config uses .get() with default

**Detection**: `grep -n "\.get(" **/*.py | grep "config"`

**Fix**:
```python
# Before
api_key = config.get("api_key", "default")

# After
api_key = config["api_key"]  # Will raise KeyError if missing - that's GOOD
```

### Violation: Hardcoded file path

**Detection**: `grep -n "'/home/" **/*.py`

**Fix**:
```python
# Before
data_path = "/home/user/data/file.csv"

# After
from pathlib import Path
data_path = Path(config["data_dir"]) / "file.csv"
```

### Violation: Environment variable access

**Detection**: `grep -n "os.getenv\|os.environ" **/*.py`

**Fix**:
```python
# Before
api_url = os.getenv("API_URL", "https://default.com")

# After
api_url = config["api"]["url"]  # From YAML config
```

## References

- Fail-Fast Philosophy: `references/FAIL-FAST.md`
- Test Standards: `references/TESTS.md`
- Hydra Configuration: `references/HYDRA.md`
- Git Workflow: `references/GIT-WORKFLOW.md`
