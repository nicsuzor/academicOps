---
title: Fail-Fast Philosophy
type: reference
permalink: python-dev-fail-fast
description: Error handling philosophy and patterns for Python applications
---

# Fail-Fast Philosophy

## Core Principle

**Silent failures corrupt research data.** Fail immediately so problems are fixed, not hidden.

## No Defaults, No Fallbacks

### FORBIDDEN Patterns

```python
# ❌ Silent defaults
value = config.get("api_key", "default_key")
value = os.getenv("API_KEY", "fallback")
value = kwargs.get("timeout", 30)

# ❌ Silent fallbacks
try:
    result = risky_operation()
except Exception:
    result = default_value  # Hides errors!

# ❌ Defensive checks
if value is None:
    value = fallback  # Should fail instead


# ❌ Optional parameters with defaults for config
def process(data, timeout=30):  # Config should be required!
    ...
```

### REQUIRED Patterns

```python
# ✅ Explicit, fails immediately
value = config["api_key"]  # KeyError if missing - GOOD
value = os.environ["API_KEY"]  # Fails if not set - GOOD

# ✅ No try/except for expected values
api_key = config["api_key"]  # Let it fail if missing

# ✅ Explicit checks with errors
if "api_key" not in config:
    raise ValueError("api_key is required in configuration")
```

## Why This Matters

**Example: Silent failure corrupts research**

```python
# ❌ BAD: Silent default
error_threshold = config.get("error_threshold", 0.5)

# Problem: Config file has typo: "error_threshhold: 0.1"
# Code silently uses 0.5 instead of 0.1
# Research results are WRONG for months
# No error was raised!
```

```python
# ✅ GOOD: Explicit required field
error_threshold = config["error_threshold"]  # Raises KeyError immediately


# OR with Pydantic
class Config(BaseModel):
    error_threshold: float  # No default - required


# Typo in config file → ValidationError immediately
# Research stops, problem gets fixed
```

## Pydantic for Configuration

### REQUIRED: No Defaults for Config

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class ProcessingConfig(BaseModel):
    """Configuration with validation."""

    # Required fields (no defaults)
    api_key: str
    data_dir: Path
    max_retries: int
    timeout: float

    # Only simple types can have defaults if truly optional
    log_level: str = "INFO"  # Genuinely optional
    batch_size: int = 100  # Has sensible default

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists."""
        if not v.exists():
            raise ValueError(f"data_dir does not exist: {v}")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Ensure retries is positive."""
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v


# Usage
config = ProcessingConfig(
    api_key=os.environ["API_KEY"],  # Fails if not set
    data_dir=Path("/data"),
    max_retries=3,
    timeout=30.0,
)
```

### Validation at Boundaries

```python
from typing import Dict, Any
from pydantic import BaseModel


class APIResponse(BaseModel):
    """API response model."""

    status: str
    data: Dict[str, Any]
    timestamp: str


def process_api_response(raw_data: Dict[str, Any]) -> ProcessedData:
    """Process API response with validation at boundary."""

    # ✅ Validate at boundary
    validated = APIResponse(**raw_data)  # Pydantic validates

    # Work with validated data
    return process_validated(validated)


# ❌ Don't validate internal data repeatedly
def internal_function(data: APIResponse) -> Result:
    # data already validated at boundary, don't re-validate
    return transform(data.data)
```

## Error Handling

### No Bare Excepts

```python
# ❌ FORBIDDEN: Bare except (catches EVERYTHING)
try:
    risky_operation()
except:
    pass

# ❌ Too broad
try:
    result = api_call()
except Exception:
    result = None  # Hides all errors!

# ❌ Silent default on exception
try:
    timeout = int(config["timeout"])
except (KeyError, ValueError):
    timeout = 30  # Hides configuration problems!
```

### Specific Exceptions

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

# ✅ Specific validation with clear errors
if not config_path.exists():
    raise FileNotFoundError(f"Config file not found: {config_path}")

content = config_path.read_text()
config_data = json.loads(content)  # Let JSONDecodeError raise
```

### When to Catch Exceptions

**DO catch when**:

- At system boundaries (logging, then re-raising)
- When you can meaningfully recover
- For cleanup (use `finally` or context managers)

**DON'T catch when**:

- To hide errors
- To provide default values
- To "make it work" when it should fail

## Configuration Loading Patterns

### Pattern 1: Pydantic (PREFERRED)

```python
from pydantic import BaseModel
from pathlib import Path
import yaml


class AppConfig(BaseModel):
    """Application configuration."""

    database_url: str  # Required, no default
    api_key: str  # Required, no default
    data_dir: Path  # Required, no default
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

### Pattern 2: Explicit KeyError

```python
def load_config_dict(config: Dict[str, Any]) -> Config:
    """Load config with explicit validation."""

    # ✅ Let KeyError raise
    database_url = config["database_url"]
    api_key = config["api_key"]

    # ✅ Or explicit check
    if "data_dir" not in config:
        raise ValueError("data_dir must be explicitly configured")

    return Config(
        database_url=database_url,
        api_key=api_key,
        data_dir=Path(config["data_dir"]),
    )
```

### Pattern 3: Environment Variables

```python
import os
from pathlib import Path


def load_from_env() -> Config:
    """Load config from environment variables."""

    # ✅ Explicit, raises if not set
    api_key = os.environ["API_KEY"]
    database_url = os.environ["DATABASE_URL"]

    # ❌ NEVER use .get() with defaults for config
    # timeout = os.getenv("TIMEOUT", "30")  # NO!

    # ✅ Fail if optional env var malformed
    timeout_str = os.getenv("TIMEOUT")
    timeout = int(timeout_str) if timeout_str else 30

    return Config(
        api_key=api_key,
        database_url=database_url,
        timeout=timeout,
    )
```

## Common Failure Patterns to Avoid

### Pattern 1: Defensive Programming

```python
# ❌ BAD: Defensive checks everywhere
def process_data(data):
    if data is None:
        return []  # Hiding the problem

    if not isinstance(data, list):
        data = [data]  # Guessing at intent

    # More defensive code...
```

```python
# ✅ GOOD: Explicit requirements
def process_data(data: List[Dict[str, Any]]) -> List[str]:
    """Process data with explicit requirements.

    Args:
        data: List of data dictionaries (REQUIRED)

    Raises:
        ValueError: If data is empty
    """
    if not data:
        raise ValueError("data cannot be empty")

    return [transform(item) for item in data]
```

### Pattern 2: Try/Except as Default

```python
# ❌ BAD: Using exceptions for defaults
try:
    port = int(config["port"])
except (KeyError, ValueError):
    port = 8080  # Hiding configuration errors
```

```python
# ✅ GOOD: Explicit validation
if "port" not in config:
    raise ValueError("port must be specified in config")

try:
    port = int(config["port"])
except ValueError as e:
    raise ValueError(f"port must be an integer, got: {config['port']}") from e
```

### Pattern 3: Silent None Handling

```python
# ❌ BAD: Silent None defaults
def fetch_user(user_id: Optional[str]) -> User:
    if user_id is None:
        return AnonymousUser()  # Hiding missing user_id
```

```python
# ✅ GOOD: Explicit None handling
def fetch_user(user_id: str) -> User:
    """Fetch user by ID.

    Args:
        user_id: User identifier (REQUIRED)

    Raises:
        ValueError: If user_id is empty
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Fetch user...


# Separate function for optional case
def fetch_user_or_anonymous(user_id: Optional[str]) -> User:
    """Fetch user or return anonymous if None."""
    if user_id is None:
        return AnonymousUser()
    return fetch_user(user_id)
```

