# Python Development

## Overview

Write production-quality Python code following fail-fast philosophy, type safety, and modern best practices. This skill enforces rigorous standards for academic and research code where correctness and replicability are paramount.

## When to Use This Skill

Use python-dev when:

1. **Writing new Python code** - Functions, classes, modules
2. **Refactoring existing code** - Improving quality and maintainability
3. **Code review** - Validating Python code against standards
4. **Debugging Python issues** - Following systematic debugging workflow
5. **API design** - Creating Python interfaces and libraries

**Concrete trigger examples**:
- "Write a function to process user data"
- "Refactor this module to use Pydantic"
- "Add type hints to this code"
- "Review this Python code for quality"
- "Fix this bug in the data pipeline"

## Core Python Philosophy

### 1. Fail-Fast: No Defaults, No Fallbacks

**FORBIDDEN**:
```python
# ❌ Silent defaults
value = config.get("api_key", "default_key")
value = os.getenv("API_KEY", "fallback")

# ❌ Silent fallbacks
try:
    result = risky_operation()
except Exception:
    result = default_value  # Hides errors!

# ❌ Defensive checks
if value is None:
    value = fallback  # Should fail instead
```

**REQUIRED**:
```python
# ✅ Explicit, fails immediately
value = config["api_key"]  # KeyError if missing - GOOD
value = os.environ["API_KEY"]  # Fails if not set - GOOD

# ✅ Pydantic validation (fails at startup)
class Config(BaseModel):
    api_key: str  # No default - required field
    timeout: int  # No default - required field

# ✅ Explicit checks with errors
if "api_key" not in config:
    raise ValueError("api_key is required in configuration")
```

**Why**: Silent failures corrupt research data. Fail immediately so problems are fixed, not hidden.

### 2. Type Safety: Always Use Type Hints

**Required for ALL**:
- Function signatures (parameters and return types)
- Class attributes
- Complex data structures
- Public APIs

**Type Hint Patterns**:
```python
from typing import Optional, List, Dict, Set, Tuple, Union, Any
from pathlib import Path
from datetime import datetime

# ✅ Function signatures
def process_records(
    records: List[Dict[str, Any]],
    output_path: Path,
    filter_active: bool = False,  # Only simple types can have defaults
) -> int:
    """Process records and write to file.

    Args:
        records: List of record dictionaries
        output_path: Where to save results
        filter_active: Whether to filter for active records only

    Returns:
        Number of records processed

    Raises:
        ValueError: If records is empty
        IOError: If output_path cannot be written
    """
    if not records:
        raise ValueError("records cannot be empty")

    # Implementation
    return len(records)

# ✅ Class with typed attributes
class DataProcessor:
    """Process research data with validation."""

    def __init__(
        self,
        config: Dict[str, Any],
        logger: Logger,
    ) -> None:
        self.config = config
        self.logger = logger
        self._processed_count: int = 0

    def process(self, data: List[str]) -> Dict[str, int]:
        """Process data and return stats."""
        ...

# ✅ Optional for nullable values
def find_user(user_id: str) -> Optional[User]:
    """Find user by ID, return None if not found."""
    ...

# ✅ Union for multiple types
def load_config(source: Union[str, Path, Dict[str, Any]]) -> Config:
    """Load config from file path or dict."""
    ...
```

### 3. Pydantic for Configuration and Validation

**Use Pydantic for**:
- Configuration objects (from YAML/JSON)
- Data validation at boundaries
- API request/response models
- Complex data structures with validation rules

**Pattern**:
```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class ProjectConfig(BaseModel):
    """Project configuration with validation."""

    # Required fields (no defaults)
    project_name: str
    data_dir: Path
    api_key: str

    # Optional fields (with defaults)
    max_retries: int = 3
    timeout: float = 30.0

    # Validated fields
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

    @field_validator('data_dir')
    @classmethod
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists."""
        if not v.exists():
            raise ValueError(f"data_dir does not exist: {v}")
        return v

    @field_validator('max_retries')
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Ensure retries is positive."""
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v

# Usage
config = ProjectConfig(
    project_name="research-project",
    data_dir=Path("/data"),
    api_key=os.environ["API_KEY"],  # Fails if not set
)
```

**Validation at Boundaries**:
```python
# ✅ Validate external data immediately
def process_api_response(raw_data: Dict[str, Any]) -> ProcessedData:
    """Process API response with validation."""
    # Validate at boundary
    validated = ResponseModel(**raw_data)  # Pydantic validates

    # Work with validated data
    return process_validated(validated)

# ❌ Don't validate internal data repeatedly
def internal_function(data: ProcessedData) -> Result:
    # data already validated at boundary, don't re-validate
    ...
```

### 4. Modern Python: pathlib, f-strings, comprehensions

**Use pathlib, not os.path**:
```python
from pathlib import Path

# ✅ Modern pathlib
data_dir = Path("/data")
input_file = data_dir / "input.json"
output_file = data_dir / "output.json"

if input_file.exists():
    content = input_file.read_text()

# ❌ Old os.path
import os
data_dir = "/data"
input_file = os.path.join(data_dir, "input.json")

if os.path.exists(input_file):
    with open(input_file) as f:
        content = f.read()
```

**Use f-strings for formatting**:
```python
# ✅ f-strings
name = "Alice"
age = 30
message = f"User {name} is {age} years old"

# ❌ Old % or .format()
message = "User %s is %d years old" % (name, age)
message = "User {} is {} years old".format(name, age)
```

**Use comprehensions for transformations**:
```python
# ✅ List comprehensions
active_users = [u for u in users if u.is_active]
user_names = [u.name for u in users]

# ✅ Dict comprehensions
user_map = {u.id: u.name for u in users}

# ✅ Set comprehensions
unique_ids = {u.id for u in users}

# ❌ Manual loops for simple transformations
active_users = []
for u in users:
    if u.is_active:
        active_users.append(u)
```

### 5. No Bare Excepts, Specific Error Handling

**FORBIDDEN**:
```python
# ❌ Bare except (catches EVERYTHING)
try:
    risky_operation()
except:
    pass

# ❌ Too broad
try:
    result = api_call()
except Exception:
    result = None  # Hides all errors!
```

**REQUIRED**:
```python
# ✅ Specific exceptions
try:
    result = api_call()
except httpx.TimeoutError:
    logger.error("API timeout")
    raise  # Re-raise, don't hide
except httpx.HTTPError as e:
    logger.error(f"API error: {e}")
    raise

# ✅ Let it fail (fail-fast)
result = api_call()  # If it fails, it fails - FIX THE ROOT CAUSE
```

**When to catch exceptions**:
- At system boundaries (logging, then re-raising)
- When you can meaningfully recover
- For cleanup (use `finally` or context managers)

**When NOT to catch**:
- To hide errors
- To provide default values
- To "make it work" when it should fail

## Python Development Workflow

### Step 1: Design Before Code

**Before writing any code**:

1. **Define the interface**:
   - Function signatures with type hints
   - Input/output contracts
   - Error conditions

2. **Write docstring**:
   - What does it do?
   - Args (with types)
   - Returns (with type)
   - Raises (what exceptions, when)

3. **Consider edge cases**:
   - Empty inputs
   - None values
   - Invalid data
   - Boundary conditions

**Example**:
```python
def calculate_statistics(
    data: List[float],
    percentiles: List[int] = [25, 50, 75],
) -> Dict[str, float]:
    """Calculate statistical measures for numeric data.

    Args:
        data: List of numeric values to analyze
        percentiles: Which percentiles to calculate (0-100)

    Returns:
        Dictionary with keys: mean, median, std, and p{N} for each percentile

    Raises:
        ValueError: If data is empty or percentiles invalid

    Example:
        >>> stats = calculate_statistics([1, 2, 3, 4, 5])
        >>> stats['mean']
        3.0
        >>> stats['p50']  # median
        3.0
    """
    # Implementation follows design
    if not data:
        raise ValueError("data cannot be empty")

    if any(p < 0 or p > 100 for p in percentiles):
        raise ValueError("percentiles must be between 0 and 100")

    # Calculate stats...
```

### Step 2: Write Test First (TDD)

**Use test-writing skill for detailed TDD workflow**.

**Quick reference**:
```python
def test_calculate_statistics_basic(real_conf):
    """Test basic statistical calculations."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]

    stats = calculate_statistics(data)

    assert stats['mean'] == 3.0
    assert stats['median'] == 3.0
    assert 'p25' in stats
    assert 'p75' in stats

def test_calculate_statistics_empty_raises():
    """Test that empty data raises ValueError."""
    with pytest.raises(ValueError, match="data cannot be empty"):
        calculate_statistics([])

def test_calculate_statistics_invalid_percentiles():
    """Test that invalid percentiles raise ValueError."""
    with pytest.raises(ValueError, match="percentiles must be"):
        calculate_statistics([1, 2, 3], percentiles=[-1, 50])
```

### Step 3: Implement with Quality

**Code quality checklist**:

- [ ] Type hints on all parameters and returns
- [ ] Docstring with Args/Returns/Raises
- [ ] No `.get()` with defaults for required config
- [ ] No bare `except:` clauses
- [ ] Uses pathlib for file operations
- [ ] Uses f-strings for formatting
- [ ] Pydantic for configuration/validation
- [ ] No magic numbers (use constants)
- [ ] Clear variable names (no `x`, `temp`, `data`)
- [ ] Single responsibility (function does one thing)

**Example**:
```python
from pathlib import Path
from typing import List, Dict
import json
from pydantic import BaseModel

class ProcessingConfig(BaseModel):
    """Configuration for data processing."""
    input_dir: Path
    output_dir: Path
    batch_size: int

def load_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON data from file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of records from file

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file isn't valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    content = file_path.read_text()
    return json.loads(content)

def process_batch(
    records: List[Dict[str, Any]],
    config: ProcessingConfig,
) -> List[Dict[str, Any]]:
    """Process a batch of records.

    Args:
        records: Records to process
        config: Processing configuration

    Returns:
        Processed records

    Raises:
        ValueError: If records is empty
    """
    if not records:
        raise ValueError("Cannot process empty batch")

    # Process records
    processed = [transform_record(r) for r in records]

    return processed
```

### Step 4: Run and Debug

**Debugging workflow**:

1. **Run tests**:
   ```bash
   uv run pytest tests/test_module.py -xvs
   ```

2. **If test fails**:
   - Read error message carefully
   - Check assumptions
   - Add debug logging (use logger, not print)
   - Use pytest's `-xvs` for detailed output

3. **DO NOT**:
   - Create `test.py`, `debug.py`, `verify.py` scripts
   - Use `python -c "..."` to check things
   - Add try/except to hide the error
   - Guess at fixes

4. **DO**:
   - Fix the root cause
   - Add test for the bug
   - Verify fix with pytest

**Logging (not print)**:
```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: List[str]) -> List[str]:
    """Process data with logging."""
    logger.info(f"Processing {len(data)} records")

    try:
        result = [transform(d) for d in data]
        logger.info(f"Successfully processed {len(result)} records")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise  # Re-raise, don't hide
```

## Common Patterns

### Pattern 1: Configuration Loading

```python
from pydantic import BaseModel
from pathlib import Path
import yaml

class AppConfig(BaseModel):
    """Application configuration."""
    database_url: str
    api_key: str
    data_dir: Path
    batch_size: int = 100  # Only simple defaults

def load_config(config_path: Path) -> AppConfig:
    """Load and validate configuration.

    Args:
        config_path: Path to YAML config file

    Returns:
        Validated configuration

    Raises:
        FileNotFoundError: If config file missing
        ValidationError: If config invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    content = yaml.safe_load(config_path.read_text())
    return AppConfig(**content)  # Pydantic validates

# Usage
config = load_config(Path("config.yaml"))
# If config missing/invalid, fails immediately - GOOD
```

### Pattern 2: Data Processing Pipeline

```python
from typing import List, Dict, Any, Callable
from pathlib import Path

def load_data(source: Path) -> List[Dict[str, Any]]:
    """Load data from source."""
    ...

def validate_data(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate records, raise on invalid data."""
    for record in records:
        if "id" not in record:
            raise ValueError(f"Record missing id: {record}")
    return records

def transform_data(
    records: List[Dict[str, Any]],
    transformer: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply transformation to each record."""
    return [transformer(r) for r in records]

def save_data(records: List[Dict[str, Any]], destination: Path) -> None:
    """Save records to destination."""
    ...

# Pipeline
data = load_data(input_path)
validated = validate_data(data)
transformed = transform_data(validated, my_transformer)
save_data(transformed, output_path)
```

### Pattern 3: Error Handling at Boundaries

```python
import httpx
from typing import Dict, Any

def fetch_api_data(url: str, api_key: str) -> Dict[str, Any]:
    """Fetch data from API with error handling at boundary.

    Args:
        url: API endpoint
        api_key: Authentication key

    Returns:
        API response data

    Raises:
        httpx.HTTPError: On API errors
        ValueError: On invalid response format
    """
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.TimeoutError:
        logger.error(f"API timeout: {url}")
        raise  # Let it fail
    except httpx.HTTPError as e:
        logger.error(f"API error: {e}")
        raise  # Let it fail

    data = response.json()

    # Validate at boundary
    if "results" not in data:
        raise ValueError("API response missing 'results' field")

    return data
```

### Pattern 4: File Operations with pathlib

```python
from pathlib import Path
from typing import List
import json

def process_directory(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.json",
) -> int:
    """Process all files in directory.

    Args:
        input_dir: Input directory
        output_dir: Output directory
        pattern: File pattern to match

    Returns:
        Number of files processed

    Raises:
        FileNotFoundError: If input_dir doesn't exist
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for input_file in input_dir.glob(pattern):
        # Process file
        data = json.loads(input_file.read_text())
        result = process_data(data)

        # Write output
        output_file = output_dir / input_file.name
        output_file.write_text(json.dumps(result, indent=2))

        processed += 1

    return processed
```

## Code Review Checklist

When reviewing Python code, check:

**Fail-Fast**:
- [ ] No `.get(key, default)` for required config
- [ ] No `try/except` returning defaults
- [ ] No `if x is None: x = fallback`
- [ ] Uses `config["key"]` (raises KeyError)
- [ ] Pydantic fields have no defaults (required)

**Type Safety**:
- [ ] All function parameters have type hints
- [ ] All return types specified
- [ ] Optional used for nullable values
- [ ] Complex types properly hinted (List, Dict, etc.)

**Modern Python**:
- [ ] Uses pathlib for file operations
- [ ] Uses f-strings for formatting
- [ ] Uses comprehensions for transformations
- [ ] No bare `except:` clauses

**Quality**:
- [ ] Docstrings with Args/Returns/Raises
- [ ] Clear variable names
- [ ] Single responsibility per function
- [ ] No magic numbers
- [ ] Logging instead of print

**Testing**:
- [ ] Tests exist for functionality
- [ ] Tests use real_bm/real_conf fixtures
- [ ] Tests cover edge cases
- [ ] No standalone test scripts

## Critical Rules

**NEVER**:
- Use `.get()` with defaults for required configuration
- Use bare `except:` or overly broad exception handling
- Create standalone test/debug/verify scripts
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
    param3: Path,
) -> Dict[str, Any]:
    """Short description of what it does.

    Args:
        param1: Description
        param2: Description
        param3: Description

    Returns:
        Description of return value

    Raises:
        ValueError: When and why
        FileNotFoundError: When and why
    """
    # Validate inputs
    if not param1:
        raise ValueError("param1 cannot be empty")

    # Implementation
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

    @field_validator('required_path')
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v
```

**Command reference**:
```bash
# Run specific test
uv run pytest tests/test_module.py::test_function -xvs

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```
