---
title: "Code Style and Conventions"
type: conventions
description: "Generic code formatting and documentation standards for agents. Project-specific style requirements in project-tier STYLE.md files."
tags:
  - style
  - conventions
  - formatting
  - code-quality
relations:
  - "[[chunks/AXIOMS]]"
  - "[[core/DEVELOPMENT]]"
---

# Code Style and Conventions

Generic code formatting and documentation standards. Project-specific style requirements in project-tier STYLE.md files.

## General Principles

**Clarity over cleverness**:

- Code should be self-explanatory
- Prefer explicit over implicit
- Use descriptive names
- Comment "why", not "what"

**Consistency**:

- Follow existing patterns in the codebase
- Don't introduce new patterns without good reason
- When in doubt, match surrounding code style

## Naming Conventions

**Files and Modules** (Python):

- `lowercase_with_underscores.py`
- Test files: `test_module_name.py`
- Avoid abbreviations unless widely known

**Functions and Methods**:

- `lowercase_with_underscores()`
- Verb phrases: `get_user()`, `process_data()`, `validate_input()`
- Boolean functions: `is_valid()`, `has_permission()`, `can_process()`

**Classes**:

- `PascalCase`
- Noun phrases: `UserManager`, `DataProcessor`, `AuthenticationService`

**Constants**:

- `UPPERCASE_WITH_UNDERSCORES`
- Module-level only: `MAX_RETRIES = 3`, `DEFAULT_TIMEOUT = 30`

**Variables**:

- `lowercase_with_underscores`
- Descriptive: `user_count`, not `uc`
- Avoid single letters except in loops: `for i in range(10)`

## Code Organization

**Import Order** (Python):

```python
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. Third-party packages
import numpy as np
import pytest
from pydantic import BaseModel

# 3. Local/project imports
from myproject.auth import authenticate
from myproject.data import Database
```

**Function Length**:

- Keep functions focused (one responsibility)
- Aim for < 50 lines
- If longer, consider extracting helper functions
- Long functions should have clear sections with comments

**File Length**:

- Aim for < 500 lines per file
- If longer, consider splitting into multiple modules
- Group related functionality together

## Documentation

**Docstrings** (Python):

```python
def process_user_data(user_id: str, options: dict) -> Result:
    """Process user data with specified options.

    Args:
        user_id: Unique identifier for the user
        options: Configuration options for processing
                 Expected keys: 'validate', 'transform', 'save'

    Returns:
        Result object with status and processed data

    Raises:
        ValueError: If user_id is empty
        ProcessingError: If data processing fails

    Example:
        result = process_user_data("user123", {"validate": True})
        if result.success:
            print(result.data)
    """
    # Implementation
```

**Comments**:

```python
# ✅ Good - explains WHY
# Use exponential backoff to avoid overwhelming the API
retry_delay = base_delay * (2**attempt)

# ❌ Bad - explains WHAT (code already shows this)
# Multiply base_delay by 2 to the power of attempt
retry_delay = base_delay * (2**attempt)
```

**TODOs**:

```python
# TODO(username): Brief description of what needs to be done
# TODO: Optimize this query for large datasets
# FIXME: Handle edge case where user_id is None
```

## Error Handling

**Be specific**:

```python
# ✅ Good - specific exception
raise ValueError(f"User ID cannot be empty, got: {user_id}")

# ❌ Bad - generic exception
raise Exception("Error")
```

**Fail fast**:

```python
# ✅ Good - validate early
def process_data(data: dict):
    if not data:
        raise ValueError("Data cannot be empty")
    if "required_field" not in data:
        raise ValueError("Missing required_field in data")

    # Process data...


# ❌ Bad - fail late
def process_data(data: dict):
    # Process data...
    if not data.get("required_field"):  # Fails deep in processing
        raise ValueError("Missing field")
```

## Type Hints (Python)

**Use type hints consistently**:

```python
from typing import List, Dict, Optional, Union


def get_users(user_ids: List[str], include_deleted: bool = False) -> Dict[str, User]:
    """Retrieve users by IDs."""
    # Implementation


def find_user(user_id: str) -> Optional[User]:
    """Find user by ID, returns None if not found."""
    # Implementation
```

## Code Formatting

**Follow language-specific formatters**:

- Python: `black` or `ruff format`
- JavaScript/TypeScript: `prettier`
- Use project's configured formatter settings
- Run formatter before committing

**Line Length**:

- Aim for 88-100 characters (Python default for black)
- Break long lines logically
- Indent continuation lines clearly

**Whitespace**:

- One blank line between functions
- Two blank lines between classes
- No trailing whitespace
- Consistent indentation (spaces, not tabs for Python)

See project-tier STYLE.md for project-specific conventions and domain-specific formatting requirements.
