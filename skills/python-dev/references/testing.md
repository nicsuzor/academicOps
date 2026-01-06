---
title: Python Testing Philosophy
type: reference
category: ref
permalink: python-dev-testing
description: Testing patterns, mocking strategy, and pytest best practices
---

# Python Testing Philosophy

## Core Principle: Mock Only at the Boundary

We mock only at system boundaries—where our code interfaces with external systems. The "inside" of our application should be tested with real logic and plain assertions.

### System Boundaries (OK to Mock)

- **Network**: HTTP calls, API requests, websockets
- **Filesystem**: File I/O when real temp dirs not feasible
- **Time**: System clock, delays, timeouts
- **Randomness**: Random number generation
- **Environment**: Environment variables, system properties
- **External Services**: Third-party APIs you can't call in tests

### Our Code (NEVER Mock)

- Anything in your project namespace
- Your business logic
- Your data transformations
- Your internal APIs
- Your utilities and helpers

## Why This Philosophy?

### Problems with Over-Mocking

```python
# ❌ BAD: Testing the mock, not the code
@patch("myproject.processors.DataProcessor._process")
def test_processor(mock_process):
    mock_process.return_value = "mocked result"
    processor = DataProcessor()
    result = processor.run()
    assert result == "mocked result"  # Proves nothing!
```

### Benefits of Boundary-Only Mocking

```python
# ✅ GOOD: Testing real behavior, mocking only external calls
@respx.mock
async def test_processor():
    # Mock only the external HTTP call
    respx.post("https://api.example.com/process").mock(
        return_value=httpx.Response(200, json={"result": "processed"})
    )

    # Test real processor logic
    processor = DataProcessor(api_url="https://api.example.com")
    result = await processor.process_data({"input": "test"})

    # Assert on actual behavior
    assert result.status == "success"
    assert result.data == "processed"
```

## Test Types

### Unit Tests

- Test single function/class in isolation
- Mock external dependencies only
- Fast execution (< 100ms)
- Location: `tests/unit/`

### Integration Tests

- Test 2-3 components working together
- Use real configuration
- May mock external APIs
- Moderate execution (< 5s)
- Location: `tests/integration/`

### End-to-End (E2E) Tests

- Test complete workflows
- REAL everything: APIs, storage, processors
- Minimal mocking (only flaky external services)
- Slower execution (OK to take 30s+)
- Location: `tests/e2e/` or `tests/endtoend/`

## E2E Testing Pattern

### TRUE E2E = Real APIs + Real Storage + Real Data

```python
@pytest.mark.anyio
async def test_complete_pipeline():
    """TRUE E2E test - uses REAL everything."""

    # REAL data processor
    processor = DataProcessor(model="gpt-4")

    # REAL external API call
    result = await processor.fetch_from_api("https://api.example.com/data")

    # REAL storage (temp location for isolation)
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(path=Path(tmpdir))
        await storage.save(result)

        # Verify complete workflow
        retrieved = await storage.load(result.id)
        assert retrieved == result
```

### Success Criteria for E2E Tests

1. ✅ Use real configuration
2. ✅ Call real APIs (document any mocked external systems)
3. ✅ Store data in real databases (temp locations OK)
4. ✅ Exercise complete workflow from input to output
5. ✅ Validate end-to-end behavior
6. ✅ Use realistic test data
7. ✅ Clean up resources after test

## Demo Tests

**Goal**: Create _executable demonstrations_ that show behavior (narrative + observable output) and prove real-world utility.

A good demo test should:

- **Read like documentation** (scenario names, clear setup)
- **Show behavior** (prints/logs/trace-friendly asserts) when run in "demo mode"
- **Use real data** (prove _and demonstrate_ real-world utility)

### Demo Test Rules

1. **Add demo marker** (required): `@pytest.mark.demo`
2. **Names explain behavior**: Use "Given / When / Then" naming structure
3. **Log intermediate state**: Include `log.info(...)` calls showing key steps
4. **Direct object comparisons**: Prefer dicts/lists/dataclasses for readable diffs
5. **Human-readable parametrization IDs**: Create a mini "example catalog"
6. **Asserts that teach**: Compare **dicts**, **lists**, **dataclasses** directly

### Demo Test Example

```python
import logging
import pytest

log = logging.getLogger(__name__)


@pytest.mark.demo
@pytest.mark.parametrize(
    "input_data,expected",
    [
        pytest.param({"name": "Alice"}, {"greeting": "Hello, Alice!"}, id="basic_greeting"),
        pytest.param({"name": ""}, {"greeting": "Hello, stranger!"}, id="empty_name_fallback"),
    ],
)
def test_given_user_when_greeted_then_personalized_message(input_data, expected):
    """Demo: Greeting service personalizes messages based on user data."""
    log.info(f"Input: {input_data}")

    result = greeting_service.greet(input_data)
    log.info(f"Result: {result}")

    assert result == expected  # Direct dict comparison = readable diff
```

### Running Demo Tests

```bash
# Run all demo tests with verbose output
uv run pytest -m demo -xvs --log-cli-level=INFO

# Run demos for specific module
uv run pytest -m demo tests/test_module.py -xvs --log-cli-level=INFO
```

## Pytest Patterns

### Test Naming Conventions

```python
# tests/test_module.py
import pytest


def test_function_with_valid_input():
    """Test function processes valid input correctly."""
    result = my_function("valid input")
    assert result == "expected output"


def test_function_with_empty_input_raises():
    """Test function raises ValueError on empty input."""
    with pytest.raises(ValueError, match="input cannot be empty"):
        my_function("")


def test_function_with_none_returns_none():
    """Test function returns None when input is None."""
    result = my_function(None)
    assert result is None
```

### Fixtures for Reusable Setup

**CRITICAL**: Use real captured data, not fabricated fixtures. See [[HEURISTICS.md#H33]].

```python
import pytest
from pathlib import Path

# Location for real captured test data
TESTS_DATA = Path(__file__).parent / "data"


@pytest.fixture
def sample_session() -> Path:
    """Real session transcript captured from production.

    To refresh: cp ~/.claude/projects/.../session.jsonl tests/data/
    """
    return TESTS_DATA / "sample_session.jsonl"


@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


def test_with_real_data(sample_session: Path):
    """Test using real captured data."""
    assert sample_session.exists(), "Run capture command to refresh test data"
    # Parse and test against real format
```

**Why real data?** Fabricated fixtures encode format assumptions. Real data guarantees format accuracy. When formats drift, tests fail - signaling the need to refresh captures.

### Async Tests

```python
import pytest


@pytest.mark.anyio
async def test_async_function():
    """Test async function."""
    result = await async_function("input")
    assert result == "expected"
```

## Standalone Validation - FORBIDDEN

**❌ NEVER create standalone validation**:

**Forbidden patterns**:

- `test_*.py` files OUTSIDE `tests/` directory
- `verify_*.py`, `check_*.py`, `validate_*.py` anywhere
- `examples/*.py`, `demo_*.py` scripts
- `uv run python -c "..."` for validation
- Bash heredocs with embedded Python test code

**✅ ALWAYS use proper pytest tests in `tests/` directory**

**Example of correct approach**:

```python
# ❌ DON'T: Create debug_connection.py in project root
# ✅ DO: Create tests/test_database_connection.py

import pytest


def test_database_connection():
    """Test database connection works."""
    db = Database(url="postgresql://localhost/test")
    assert db.ping()
```

## Test Isolation

### Temporary Resources

```python
import tempfile
import uuid
from pathlib import Path


def test_with_temp_dir():
    """Test using temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage = FileStorage(db_path)
        # Use real storage, just in temp location


def test_with_unique_id():
    """Test using unique identifier."""
    collection_name = f"test_{uuid.uuid4()}"
    # Use real service with unique collection name
```

## Practical Mocking Patterns

### 1. Network Boundaries (httpx/respx)

```python
import respx
import httpx


@respx.mock
async def test_api_call():
    """Test API call with mocked HTTP."""
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    result = await fetch_external_data()
    assert result["status"] == "ok"
```

### 2. Filesystem Boundaries (tmp_path)

```python
def test_file_processing(tmp_path):
    """Test file processing with temp files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    result = process_file(test_file)
    assert result == "PROCESSED: test content"
```

### 3. Time Boundaries (freezegun)

```python
from freezegun import freeze_time


@freeze_time("2024-01-01")
def test_timestamp():
    """Test timestamp generation."""
    record = create_record()
    assert record.timestamp == "2024-01-01T00:00:00"
```

## Red Flags in Tests

If you see these patterns, the test needs refactoring:

1. **Mocking your own code**
   ```python
   @patch("myproject.internal.something")  # ❌ Internal code!
   ```

2. **Complex mock setup**
   ```python
   mock = MagicMock()
   mock.method.return_value.attribute.side_effect = ...  # ❌ Too complex!
   ```

3. **Testing mock behavior**
   ```python
   mock.assert_called_with(...)  # ❌ Testing the mock!
   ```

4. **Mocking data transformations**
   ```python
   @patch("transform_data")
   def test(mock_transform):
       mock_transform.return_value = {"transformed": True}  # ❌ Not testing logic!
   ```

## Command Reference

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_module.py

# Run specific test
uv run pytest tests/test_module.py::test_function -xvs

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run only fast tests (skip e2e)
uv run pytest -m "not slow"

# Run only e2e tests
uv run pytest -m "slow"
```
