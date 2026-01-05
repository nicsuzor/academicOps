---
title: Type Safety in Python
type: reference
permalink: python-dev-type-safety
description: Type hints, Pydantic models, and static type checking patterns
---

# Type Safety in Python

## Core Principle

**All function signatures, class attributes, and complex data structures must have type hints.**

Type hints enable:

- Static type checking (mypy, pyright)
- Better IDE autocomplete
- Self-documenting code
- Early error detection
- Easier refactoring

## Required Type Hints

### 1. Function Signatures

```python
from typing import List, Dict, Optional, Any
from pathlib import Path


# ✅ Complete type hints
def process_records(
    records: List[Dict[str, Any]],
    output_path: Path,
    filter_active: bool = False,
) -> int:
    """Process records and write to file.

    Args:
        records: List of record dictionaries
        output_path: Where to save results
        filter_active: Whether to filter for active records only

    Returns:
        Number of records processed
    """
    # Implementation
    return len(records)


# ❌ Missing type hints
def process_records(records, output_path, filter_active=False):
    # What types? What returns? Unclear!
    return len(records)
```

### 2. Class Attributes

```python
from typing import List, Optional
import logging


# ✅ Typed class attributes
class DataProcessor:
    """Process research data with validation."""

    def __init__(
        self,
        config: Dict[str, Any],
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.logger = logger
        self._processed_count: int = 0
        self._errors: List[str] = []

    def process(self, data: List[str]) -> Dict[str, int]:
        """Process data and return stats."""
        self._processed_count += len(data)
        return {"processed": self._processed_count}


# ❌ Untyped class
class DataProcessor:
    def __init__(self, config, logger):
        self.config = config  # What type?
        self.logger = logger  # What type?
        self._processed_count = 0
        self._errors = []
```

### 3. Return Types

```python
from typing import Optional, List, Dict, Any


# ✅ Explicit return types
def find_user(user_id: str) -> Optional[User]:
    """Find user by ID, return None if not found."""
    # Implementation
    return None  # or User instance


def get_users(user_ids: List[str]) -> Dict[str, User]:
    """Get multiple users by IDs."""
    # Implementation
    return {}


# ✅ Explicit None return
def delete_user(user_id: str) -> None:
    """Delete user (no return value)."""
    # Implementation
    pass


# ❌ No return type
def find_user(user_id: str):  # Returns what?
    return None
```

## Common Type Patterns

### Optional for Nullable Values

```python
from typing import Optional


# ✅ Optional indicates None is valid
def find_config(name: str) -> Optional[Dict[str, Any]]:
    """Find config by name, return None if not found."""
    # Implementation
    return None


# ❌ Don't use Optional for required values
def load_config(path: str) -> Optional[Dict[str, Any]]:
    """Load config from path."""
    # If path doesn't exist, should raise, not return None!
    # Bad design - Optional suggests None is expected
```

### Union for Multiple Types

```python
from typing import Union
from pathlib import Path


# ✅ Union for multiple valid types
def load_data(source: Union[str, Path, Dict[str, Any]]) -> Data:
    """Load data from file path or dict."""
    if isinstance(source, dict):
        return Data(**source)
    # Handle Path or str
    path = Path(source) if isinstance(source, str) else source
    return Data.from_file(path)


# Consider: Is Union a code smell?
# Often better to have separate functions
def load_data_from_file(path: Path) -> Data:
    """Load data from file."""
    ...


def load_data_from_dict(data: Dict[str, Any]) -> Data:
    """Load data from dictionary."""
    ...
```

### List, Dict, Set, Tuple

```python
from typing import List, Dict, Set, Tuple, Any


# ✅ Parameterized collections
users: List[User] = []
config: Dict[str, Any] = {}
unique_ids: Set[str] = set()
coordinates: Tuple[float, float] = (0.0, 0.0)


# ✅ In function signatures
def process_users(users: List[User]) -> Dict[str, int]:
    """Process users and return stats."""
    return {"count": len(users)}


# ❌ Unparameterized (less useful)
def process_users(users: list) -> dict:  # What's in the list/dict?
    return {"count": len(users)}
```

### Any for Truly Unknown Types

```python
from typing import Any, Dict


# ✅ Any for JSON-like data
def parse_json(content: str) -> Dict[str, Any]:
    """Parse JSON content."""
    return json.loads(content)


# ⚠️  Use sparingly - prefer specific types
# If you know the structure, define it:
class APIResponse(TypedDict):
    status: str
    data: Dict[str, str]
    count: int


def parse_api_response(content: str) -> APIResponse:
    """Parse API response with known structure."""
    return json.loads(content)
```

## Pydantic for Runtime Validation

### Basic Pydantic Model

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class User(BaseModel):
    """User model with validation."""

    # Required fields
    id: int
    username: str
    email: str

    # Optional fields
    full_name: Optional[str] = None

    # Fields with defaults
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

    # Validated fields
    age: int = Field(gt=0, le=150)  # Must be 1-150


# Usage
user = User(
    id=1,
    username="alice",
    email="alice@example.com",
    age=30,
)

# Type hints work with IDE
reveal_type(user.username)  # Revealed type is 'str'
reveal_type(user.full_name)  # Revealed type is 'Optional[str]'
```

### Field Validators

```python
from pydantic import BaseModel, field_validator
from pathlib import Path
import re


class Config(BaseModel):
    """Configuration with custom validation."""

    project_name: str
    data_dir: Path
    email: str
    max_retries: int

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Ensure project name is valid."""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("project_name must be lowercase alphanumeric")
        return v

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists."""
        if not v.exists():
            raise ValueError(f"data_dir does not exist: {v}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Ensure email is valid format."""
        if "@" not in v:
            raise ValueError("email must contain @")
        return v
```

### Nested Models

```python
from pydantic import BaseModel
from typing import List


class Address(BaseModel):
    """Address model."""

    street: str
    city: str
    postal_code: str


class Person(BaseModel):
    """Person with address."""

    name: str
    age: int
    address: Address  # Nested model


class Team(BaseModel):
    """Team with members."""

    name: str
    members: List[Person]  # List of nested models


# Usage
team = Team(
    name="Research Team",
    members=[
        Person(
            name="Alice",
            age=30,
            address=Address(
                street="123 Main St",
                city="Research City",
                postal_code="12345",
            ),
        ),
    ],
)

# Type hints work through nesting
reveal_type(team.members[0].address.city)  # str
```

## Advanced Type Hints

### TypedDict for Dict Structure

```python
from typing import TypedDict, List


# ✅ Define dict structure
class UserDict(TypedDict):
    """User as dictionary."""

    id: int
    username: str
    email: str
    is_active: bool


def process_user_data(user: UserDict) -> str:
    """Process user data with known structure."""
    return f"User {user['username']} ({user['email']})"


# Type checker knows the keys
users: List[UserDict] = [
    {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "is_active": True,
    }
]
```

### Generic Types

```python
from typing import TypeVar, Generic, List


T = TypeVar("T")


class Repository(Generic[T]):
    """Generic repository for any type."""

    def __init__(self) -> None:
        self._items: List[T] = []

    def add(self, item: T) -> None:
        """Add item to repository."""
        self._items.append(item)

    def get_all(self) -> List[T]:
        """Get all items."""
        return self._items


# Usage with specific types
user_repo: Repository[User] = Repository()
user_repo.add(User(id=1, username="alice", email="alice@example.com"))

users: List[User] = user_repo.get_all()  # Type checker knows it's List[User]
```

### Protocol for Duck Typing

```python
from typing import Protocol


class Processable(Protocol):
    """Protocol for objects that can be processed."""

    def process(self) -> str:
        """Process and return result."""
        ...


def process_all(items: List[Processable]) -> List[str]:
    """Process all items implementing Processable protocol."""
    return [item.process() for item in items]


# Any class with process() method works
class DataRecord:
    def process(self) -> str:
        return "processed data"


class LogEntry:
    def process(self) -> str:
        return "processed log"


# Both work without inheritance
records: List[Processable] = [DataRecord(), LogEntry()]
results = process_all(records)
```

## Type Checking

### Using mypy

```bash
# Install
uv add --dev mypy

# Run type checking
uv run mypy src/

# Strict mode (recommended)
uv run mypy --strict src/
```

### mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true # Require type hints
disallow_any_unimported = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true
```

## Common Pitfalls

### 1. Avoid `type: ignore`

```python
# ❌ Suppressing type errors
result = process_data(data)  # type: ignore

# ✅ Fix the types
result: ProcessedData = process_data(data)
```

### 2. Use Specific Types

```python
# ❌ Too generic
def process(data: Any) -> Any: ...


# ✅ Specific types
def process(data: List[Dict[str, str]]) -> ProcessedResult: ...
```

### 3. Don't Mix Optional and Defaults

```python
# ❌ Confusing
def fetch(user_id: Optional[str] = None) -> User:
    # Is None valid or should it raise?
    ...


# ✅ Clear intent
def fetch(user_id: str) -> User:
    """Fetch user (user_id required)."""
    ...


def fetch_or_default(user_id: Optional[str]) -> User:
    """Fetch user or return default if None."""
    if user_id is None:
        return DefaultUser()
    return fetch(user_id)
```
