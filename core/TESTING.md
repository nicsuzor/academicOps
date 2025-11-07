---
title: "Testing Philosophy"
type: methodology
description: "Generic testing principles and pytest patterns for agents. Project-specific testing requirements in project-tier TESTING.md files."
tags:
  - testing
  - methodology
  - pytest
  - TDD
relations:
  - "[[chunks/AXIOMS]]"
  - "[[core/DEVELOPMENT]]"
---

# Testing Philosophy

Generic testing principles and pytest patterns. Project-specific testing requirements in project-tier TESTING.md files.

## Test Types

**Unit Tests**:

- Test single function/class in isolation
- Mock all dependencies
- Fast, focused
- Location: `tests/unit/`

**Integration Tests**:

- Test 2-3 components working together
- Use real configuration (via `real_*` fixtures if available)
- May mock external APIs
- Location: `tests/integration/`

**End-to-End (E2E) Tests**:

- Test complete workflow start to finish
- REAL everything: APIs, storage, processors
- Slower but validates production workflow
- NO mocks except unavoidable external systems
- Location: `tests/endtoend/` or `tests/e2e/`

## When to Mock

**Mock ONLY at system boundaries you don't control**:

- External third-party APIs you can't call in tests
- Services requiring paid credentials for every run
- Infrastructure you don't own (document why)

**NEVER mock**:

- Your own code (internal modules, classes, functions)
- Your own services/APIs
- Internal processors or utilities

**Example**:

```python
# ❌ DON'T mock this (it's OUR code):
# @patch("myproject.data.Database")

# ✅ DO mock this (external service):
# @patch("google.cloud.aiplatform.Endpoint")  # Only if needed
```

**Prefer real calls when possible**: If you have test credentials, use real APIs.

## Pytest Patterns

**✅ CORRECT - Proper pytest structure**:

```python
# tests/unit/test_mymodule.py
import pytest
from myproject.mymodule import MyClass

def test_myclass_initialization():
    """Test MyClass initializes with correct defaults."""
    obj = MyClass(param="value")

    assert obj.param == "value"
    assert obj.state == "initialized"

def test_myclass_process_valid_input():
    """Test MyClass processes valid input correctly."""
    obj = MyClass()
    result = obj.process("input")

    assert result.success is True
    assert result.output == "expected"
```

**Test Naming Conventions**:

- Files: `test_*.py` in `tests/` subdirectories
- Functions: `def test_<component>_<scenario>()`
- Descriptive docstrings explaining what's being tested

**Fixtures**:

```python
@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

## Standalone Validation - FORBIDDEN

**❌ NEVER create standalone validation**:

**Forbidden file-based**:

- `test_*.py` files OUTSIDE `tests/` directory
- "Quick test scripts" in project root
- `verify_*.py`, `check_*.py`, `validate_*.py` anywhere
- `examples/*.py`, `demo_*.py` scripts

**Forbidden command-based**:

- `uv run python -c "..."` for validation
- `python -c "..."` for testing
- Bash heredocs with embedded Python test code
- Any "quick verification" one-liners

**✅ ALWAYS use proper pytest tests in `tests/` directory**

## Red Flag Phrases

**STOP immediately if you think**:

- "Let me create a test to verify..."
- "I'll write a quick test script..."
- "Let me check if this works with python -c..."
- "I'll validate this with a simple command..."
- "Let me create an example to demonstrate..."

**Instead**:

- Create proper pytest test in `tests/`
- Use existing test infrastructure
- Extend existing test files
- Follow project's test patterns

## Test Isolation

**Use temporary resources**:

```python
import tempfile
from pathlib import Path

def test_with_temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        # Use real database, just in temp location
        result = process_with_db(db_path)
        assert result.success
```

**Unique identifiers for shared resources**:

```python
import uuid

def test_with_unique_collection():
    collection_name = f"test_{uuid.uuid4()}"
    # Use real service, unique collection name
    result = store_in_collection(collection_name, data)
    assert result.success
```

## Success Criteria

**Tests must**:

1. ✅ Be in `tests/` directory with proper structure
2. ✅ Follow pytest conventions (`def test_*()`)
3. ✅ Have descriptive names and docstrings
4. ✅ Use appropriate fixtures
5. ✅ Assert specific, testable outcomes
6. ✅ Clean up resources after execution
7. ✅ Run reliably in CI/CD pipeline

See project-tier TESTING.md for project-specific testing requirements and patterns.
