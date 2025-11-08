---
name: python-dev
description: Write production-quality Python code following fail-fast philosophy, type safety, and modern best practices. Enforces rigorous standards for academic and research code where correctness and replicability are paramount.
permalink: aops/skills/python-dev
---

# Python Development

Production-quality Python development with fail-fast philosophy, type safety, and modern patterns.

## When to Use This Skill

Use python-dev when:

1. **Writing new Python code** - Functions, classes, modules
2. **Refactoring existing code** - Improving quality and maintainability
3. **Code review** - Validating Python code against standards
4. **Debugging Python issues** - Following systematic debugging workflow
5. **API design** - Creating Python interfaces and libraries

**Trigger examples**:

- "Write a function to process research data"
- "Refactor this module to use Pydantic"
- "Add type hints to this code"
- "Review this Python code for quality"
- "Fix this bug in the data pipeline"

## Core Philosophy

### 1. Fail-Fast: No Defaults, No Fallbacks

@references/fail-fast.md

**Critical rule**: Silent defaults corrupt research data. Fail immediately so problems are fixed, not hidden.

### 2. Type Safety Always

@references/type-safety.md

All function signatures, class attributes, and complex data structures must have type hints.

### 3. Testing: Mock Only at Boundaries

@references/testing.md

**Never mock your own code.** Mock only at system boundaries you don't control.

### 4. Modern Python Patterns

@references/modern-python.md

Use pathlib, f-strings, comprehensions, and modern Python idioms.

### 5. Code Quality Standards

@references/code-quality.md

Docstrings, clear names, focused functions, organized imports.

## Development Workflow

### Step 1: Design Before Code

Before writing any code:

1. **Define the interface** - Function signatures with type hints
2. **Write docstring** - What it does, Args, Returns, Raises
3. **Consider edge cases** - Empty inputs, None values, invalid data

**Example**:

```python
def process_records(
    records: List[Dict[str, Any]],
    output_path: Path,
) -> int:
    """Process records and write to file.

    Args:
        records: List of record dictionaries
        output_path: Where to save results

    Returns:
        Number of records processed

    Raises:
        ValueError: If records is empty
        IOError: If output_path cannot be written
    """
    if not records:
        raise ValueError("records cannot be empty")

    # Implementation follows design
```

### Step 2: Write Test First (TDD)

Write failing test in `tests/` directory:

```python
def test_process_records_basic():
    """Test basic record processing."""
    records = [{"id": 1, "value": "test"}]
    output_path = tmp_path / "output.json"

    count = process_records(records, output_path)

    assert count == 1
    assert output_path.exists()


def test_process_records_empty_raises():
    """Test that empty records raises ValueError."""
    with pytest.raises(ValueError, match="records cannot be empty"):
        process_records([], Path("output.json"))
```

### Step 3: Implement with Quality

Code quality checklist:

- [ ] Type hints on all parameters and returns
- [ ] Docstring with Args/Returns/Raises
- [ ] No `.get()` with defaults for required config
- [ ] No bare `except:` clauses
- [ ] Uses pathlib for file operations
- [ ] Uses f-strings for formatting
- [ ] Pydantic for configuration/validation
- [ ] Clear variable names
- [ ] Single responsibility

### Step 4: Run and Debug

```bash
# Run specific test
uv run pytest tests/test_module.py::test_function -xvs

# Run with coverage
uv run pytest tests/ --cov=src

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

**DO NOT**:

- Create `test.py`, `debug.py`, `verify.py` scripts
- Use `python -c "..."` to check things
- Add try/except to hide errors
- Guess at fixes

**DO**:

- Fix the root cause
- Add test for the bug
- Verify fix with pytest
- Use logger (not print) for debugging

## Critical Rules

**NEVER**:

- Use `.get()` with defaults for required configuration
- Use bare `except:` or overly broad exception handling
- Create standalone test/debug/verify scripts outside `tests/`
- Use `print()` for logging in production code
- Use `os.path` when pathlib works
- Skip type hints on public functions
- Add defaults to Pydantic required fields

**ALWAYS**:

- Fail immediately on missing required config
- Use specific exception types
- Use pytest for all testing
- Use logger for debugging/info messages
- Use pathlib for file operations
- Add type hints to all function signatures
- Validate at system boundaries with Pydantic

## Quick Reference

**Template for new function**:

```python
from typing import List, Dict, Any
from pathlib import Path


def function_name(
    param1: str,
    param2: List[int],
) -> Dict[str, Any]:
    """Short description.

    Args:
        param1: Description
        param2: Description

    Returns:
        Description of return value

    Raises:
        ValueError: When and why
    """
    if not param1:
        raise ValueError("param1 cannot be empty")

    result = {}
    return result
```

**Template for Pydantic config**:

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class MyConfig(BaseModel):
    """Configuration with validation."""

    # Required (no defaults)
    required_field: str
    required_path: Path

    # Optional (with defaults)
    optional_field: int = 10

    @field_validator("required_path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v
```

**Common commands**:

```bash
# Run tests
uv run pytest tests/test_module.py -xvs

# Type check
uv run mypy src/

# Lint
uv run ruff check --fix src/
```

## Reference Files

- @references/fail-fast.md - No defaults, explicit config
- @references/type-safety.md - Type hints, Pydantic validation
- @references/testing.md - Testing philosophy and pytest patterns
- @references/modern-python.md - Modern Python idioms
- @references/code-quality.md - Docstrings, naming, organization
