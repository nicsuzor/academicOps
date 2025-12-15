---
title: Python Code Quality
type: reference
permalink: python-dev-code-quality
description: Python-specific code quality standards and conventions
---

# Python Code Quality

Python-specific code quality standards. See [[AXIOMS|AXIOMS]] for universal principles.

## Docstrings

### Google-Style Docstrings

```python
def calculate_statistics(
    data: List[float],
    percentiles: List[int] = [25, 50, 75],
) -> Dict[str, float]:
    """Calculate statistical measures for numeric data.

    This function computes mean, median, standard deviation, and specified
    percentiles for a list of numeric values.

    Args:
        data: List of numeric values to analyze. Must not be empty.
        percentiles: Which percentiles to calculate (0-100). Defaults to
            quartiles [25, 50, 75].

    Returns:
        Dictionary with keys:
            - mean: Arithmetic mean
            - median: 50th percentile
            - std: Standard deviation
            - p{N}: Nth percentile for each N in percentiles

    Raises:
        ValueError: If data is empty or percentiles contain invalid values.

    Example:
        >>> stats = calculate_statistics([1, 2, 3, 4, 5])
        >>> stats['mean']
        3.0
        >>> stats['p50']  # median
        3.0
    """
    if not data:
        raise ValueError("data cannot be empty")

    # Implementation...
```

### Module Docstrings

```python
"""Data processing utilities for research projects.

This module provides functions for cleaning, transforming, and validating
research data from various sources.

Typical usage example:

    from myproject.data import clean_records, validate_schema

    cleaned = clean_records(raw_data)
    validated = validate_schema(cleaned, schema)
"""

import logging
# ... rest of module
```

### Class Docstrings

```python
class DataProcessor:
    """Process and validate research data.

    This class handles the complete data processing pipeline including
    cleaning, transformation, and validation against schemas.

    Attributes:
        config: Processing configuration from Pydantic model
        logger: Logger instance for this processor
        _processed_count: Number of records processed (private)
    """

    def __init__(self, config: ProcessingConfig, logger: logging.Logger) -> None:
        """Initialize processor with configuration.

        Args:
            config: Validated processing configuration
            logger: Logger instance for this processor
        """
        self.config = config
        self.logger = logger
        self._processed_count = 0
```

## Naming Conventions

### Files and Modules

```python
# ✅ Good module names
data_processor.py
user_authentication.py
api_client.py

# ❌ Bad module names
DataProcessor.py  # Use snake_case, not PascalCase
data - processor.py  # Use underscore, not hyphen
dp.py  # No abbreviations
```

### Functions and Methods

```python
# ✅ Descriptive verb phrases
def load_user_data(user_id: str) -> UserData: ...


def calculate_average(values: List[float]) -> float: ...


def is_valid_email(email: str) -> bool: ...


def has_permission(user: User, resource: Resource) -> bool: ...


# ❌ Unclear names
def process(data):  # What kind of processing?
    ...


def get_data():  # What data?
    ...


def check(value):  # Check what?
    ...
```

### Classes

```python
# ✅ Noun phrases in PascalCase
class UserManager: ...


class DataProcessor: ...


class AuthenticationService: ...


# ❌ Poor class names
class Process:  # Too generic
    ...


class UserMgr:  # No abbreviations
    ...


class user_manager:  # Use PascalCase
    ...
```

### Variables

```python
# ✅ Descriptive names
user_count = len(users)
total_revenue = sum(sales)
is_authenticated = check_auth(token)
config_path = Path("config.yaml")

# ❌ Unclear names
uc = len(users)  # What is uc?
total = sum(sales)  # Total what?
flag = check_auth(token)  # What flag?
path = Path("config.yaml")  # What path?
```

### Constants

```python
# ✅ Module-level constants (UPPER_SNAKE_CASE)
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"
SUPPORTED_FORMATS = ["json", "csv", "parquet"]

# Use in code
for attempt in range(MAX_RETRIES):
    try:
        response = fetch_data(timeout=DEFAULT_TIMEOUT)
    except TimeoutError:
        continue
```

## Code Organization

### Import Order

```python
"""Module docstring."""

# 1. Standard library imports
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 2. Third-party imports
import httpx
import numpy as np
import pytest
from pydantic import BaseModel

# 3. Local/project imports
from myproject.auth import authenticate
from myproject.data import Database
from myproject.utils import logger

# Module-level constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
```

### Function Length

```python
# ✅ Focused function (< 50 lines)
def process_user_record(record: Dict[str, Any]) -> User:
    """Process and validate user record.

    Args:
        record: Raw user record from database

    Returns:
        Validated User object
    """
    # Validate required fields
    required_fields = ["id", "username", "email"]
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    # Create user object
    user = User(
        id=record["id"],
        username=record["username"],
        email=record["email"],
    )

    return user


# ❌ Too long - extract helper functions
def process_user_record_bad(record):
    # 100 lines of validation, transformation, etc.
    # Extract into smaller focused functions
```

### File Length

- Aim for < 500 lines per file
- If longer, consider splitting into multiple modules
- Group related functionality together

```python
# Instead of one large file:
# data_processing.py (1000 lines)

# Split into focused modules:
# data_processing/
#   __init__.py
#   cleaning.py (200 lines)
#   validation.py (150 lines)
#   transformation.py (250 lines)
#   schemas.py (100 lines)
```

## Comments

### When to Comment

```python
# ✅ Explain WHY, not WHAT
# Use exponential backoff to avoid overwhelming the API
retry_delay = base_delay * (2**attempt)

# ✅ Document complex algorithms
# Implementing Smith-Waterman algorithm for sequence alignment
# See: https://en.wikipedia.org/wiki/Smith%E2%80%93Waterman_algorithm
score_matrix = initialize_matrix(len(seq1), len(seq2))

# ✅ Mark intentional decisions
# Using float64 instead of float32 to preserve precision for scientific calculations
data = np.array(values, dtype=np.float64)

# ❌ State the obvious (code already shows this)
# Increment counter by 1
counter += 1

# ❌ Outdated comments
# TODO: Fix this later (from 2 years ago)
```

### TODOs

```python
# ✅ Actionable TODOs
# TODO(alice): Optimize this query for large datasets (Issue #123)
# TODO: Add error handling for network failures
# FIXME: Race condition when multiple processes write simultaneously

# ❌ Vague TODOs
# TODO: Improve this
# TODO: Make better
```

## Error Messages

### Specific and Actionable

```python
# ✅ Specific error messages
if not config_path.exists():
    raise FileNotFoundError(
        f"Configuration file not found: {config_path}\n"
        f"Expected location: {config_path.resolve()}\n"
        f"Create config file or set CONFIG_PATH environment variable."
    )

if "api_key" not in config:
    raise ValueError(
        "api_key is required in configuration.\n"
        "Add 'api_key' to your config file or set API_KEY environment variable."
    )

# ❌ Vague error messages
raise Exception("Error")
raise ValueError("Invalid config")
raise FileNotFoundError("File not found")
```

## Logging

### Use Logging, Not Print

```python
import logging

logger = logging.getLogger(__name__)


def process_data(data: List[str]) -> List[str]:
    """Process data with logging."""

    # ✅ Use logger
    logger.info(f"Processing {len(data)} records")

    try:
        result = [transform(d) for d in data]
        logger.info(f"Successfully processed {len(result)} records")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise  # Re-raise, don't hide


# ❌ Don't use print
def process_data_bad(data):
    print(f"Processing {len(data)} records")  # NO!
    # ...
```

### Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug(f"Connecting to {url} with timeout={timeout}")

# INFO: General informational messages
logger.info(f"Processing started with {len(data)} records")

# WARNING: Warning messages for potentially harmful situations
logger.warning(f"Retry {attempt}/{max_retries} after {delay}s delay")

# ERROR: Error messages for serious problems
logger.error(f"Failed to connect to database: {error}")

# CRITICAL: Critical messages for very serious errors
logger.critical(f"System shutdown due to: {error}")
```

## Magic Numbers

### Use Named Constants

```python
# ✅ Named constants
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
BATCH_SIZE = 100

for attempt in range(MAX_RETRIES):
    response = fetch_data(timeout=TIMEOUT_SECONDS)
    if response.ok:
        break

# ❌ Magic numbers
for attempt in range(3):  # What is 3?
    response = fetch_data(timeout=30)  # What is 30?
    if response.ok:
        break
```

## Single Responsibility

### Functions Should Do One Thing

```python
# ✅ Single responsibility - separate functions
def load_data(file_path: Path) -> str:
    """Load data from file."""
    return file_path.read_text()


def parse_data(content: str) -> List[Dict[str, Any]]:
    """Parse JSON content."""
    return json.loads(content)


def validate_data(records: List[Dict[str, Any]]) -> None:
    """Validate records have required fields."""
    for record in records:
        if "id" not in record:
            raise ValueError(f"Record missing id: {record}")


# Usage
content = load_data(file_path)
records = parse_data(content)
validate_data(records)


# ❌ Multiple responsibilities in one function
def load_and_process_data(file_path):
    # Load from file
    content = file_path.read_text()

    # Parse JSON
    records = json.loads(content)

    # Validate
    for record in records:
        if "id" not in record:
            raise ValueError("Missing id")

    # Transform
    transformed = [transform(r) for r in records]

    # Save results
    output_path.write_text(json.dumps(transformed))

    # Return (what exactly?)
    return transformed
```

## Related References

- [[type-safety|Type Safety in Python]] - Type hints and validation
- [[fail-fast|Fail-Fast Philosophy]] - Error handling and validation
- [[modern-python|Modern Python Patterns]] - Current best practices

## Summary

- **Docstrings** - Document all public functions, classes, modules
- **Naming** - Descriptive names (no abbreviations)
- **Organization** - Logical import order, focused functions
- **Comments** - Explain WHY, not WHAT
- **Error messages** - Specific and actionable
- **Logging** - Use logger, not print
- **Constants** - Named constants for magic numbers
- **Single responsibility** - One function, one purpose
