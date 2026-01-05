---
title: Modern Python Patterns
type: reference
permalink: python-dev-modern-python
description: Contemporary Python best practices and idioms
---

# Modern Python Patterns

## Use pathlib, Not os.path

### File Operations

```python
from pathlib import Path

# ✅ Modern pathlib
data_dir = Path("/data")
input_file = data_dir / "input.json"
output_file = data_dir / "output.json"

# Check existence
if input_file.exists():
    content = input_file.read_text()

# Write file
output_file.write_text(content)

# Get file info
size = input_file.stat().st_size
modified = input_file.stat().st_mtime

# ❌ Old os.path
import os

data_dir = "/data"
input_file = os.path.join(data_dir, "input.json")

if os.path.exists(input_file):
    with open(input_file) as f:
        content = f.read()
```

### Directory Operations

```python
from pathlib import Path

# ✅ pathlib directory operations
data_dir = Path("/data")

# Create directory
data_dir.mkdir(parents=True, exist_ok=True)

# List files
json_files = list(data_dir.glob("*.json"))
all_files = list(data_dir.rglob("*"))  # Recursive

# Iterate over directory
for file_path in data_dir.iterdir():
    if file_path.is_file():
        process_file(file_path)

# ❌ Old os.path
import os

data_dir = "/data"
os.makedirs(data_dir, exist_ok=True)

json_files = [
    os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".json")
]
```

### Path Manipulation

```python
from pathlib import Path

file_path = Path("/data/research/results.json")

# ✅ pathlib properties
file_path.name  # "results.json"
file_path.stem  # "results"
file_path.suffix  # ".json"
file_path.parent  # Path("/data/research")
file_path.parts  # ('/', 'data', 'research', 'results.json')

# Change extension
new_path = file_path.with_suffix(".csv")  # "/data/research/results.csv"

# Resolve relative paths
abs_path = file_path.resolve()

# ❌ Old os.path
import os

filename = os.path.basename(file_path)
dirname = os.path.dirname(file_path)
name, ext = os.path.splitext(filename)
```

## Use f-strings for Formatting

### Basic Formatting

```python
# ✅ f-strings (Python 3.6+)
name = "Alice"
age = 30
message = f"User {name} is {age} years old"

# Format numbers
price = 123.456
formatted = f"Price: ${price:.2f}"  # "Price: $123.46"

# ❌ Old % formatting
message = "User %s is %d years old" % (name, age)

# ❌ Old .format()
message = "User {} is {} years old".format(name, age)
```

### Advanced f-string Features

```python
from datetime import datetime

# Expressions in f-strings
users = ["Alice", "Bob", "Charlie"]
message = f"Found {len(users)} users"

# Date formatting
now = datetime.now()
formatted = f"Today is {now:%Y-%m-%d %H:%M:%S}"

# Debugging (Python 3.8+)
x = 42
print(f"{x=}")  # Prints: x=42

# Multiline f-strings
user = {"name": "Alice", "age": 30}
message = f"""
User Information:
  Name: {user["name"]}
  Age: {user["age"]}
"""
```

## Use Comprehensions

### List Comprehensions

```python
# ✅ List comprehension
active_users = [u for u in users if u.is_active]
user_names = [u.name for u in users]
squared = [x**2 for x in range(10)]

# ❌ Manual loop for simple transformation
active_users = []
for u in users:
    if u.is_active:
        active_users.append(u)
```

### Dict Comprehensions

```python
# ✅ Dict comprehension
user_map = {u.id: u.name for u in users}
counts = {word: len(word) for word in words}

# Filter while building dict
active_map = {u.id: u.name for u in users if u.is_active}

# ❌ Manual loop
user_map = {}
for u in users:
    user_map[u.id] = u.name
```

### Set Comprehensions

```python
# ✅ Set comprehension
unique_ids = {u.id for u in users}
even_numbers = {x for x in range(100) if x % 2 == 0}

# ❌ Manual loop
unique_ids = set()
for u in users:
    unique_ids.add(u.id)
```

### When NOT to Use Comprehensions

```python
# ❌ Too complex - use regular loop
result = [
    process_complex_data(x, y, z)
    for x in data1
    for y in data2
    if condition(x, y)
    for z in data3
    if another_condition(y, z)
]

# ✅ Clear regular loop instead
result = []
for x in data1:
    for y in data2:
        if condition(x, y):
            for z in data3:
                if another_condition(y, z):
                    result.append(process_complex_data(x, y, z))
```

## Context Managers

### Using `with` for Resources

```python
from pathlib import Path
import tempfile

# ✅ Context manager for files
input_path = Path("data.txt")
with input_path.open() as f:
    data = f.read()

# Or simpler:
data = input_path.read_text()  # Built-in context manager

# ✅ Temporary directories
with tempfile.TemporaryDirectory() as tmpdir:
    temp_path = Path(tmpdir) / "temp.txt"
    temp_path.write_text("temporary data")
    # tmpdir automatically cleaned up

# ❌ Manual resource management
f = open("data.txt")
data = f.read()
f.close()  # Easy to forget!
```

### Custom Context Managers

```python
from contextlib import contextmanager


@contextmanager
def database_transaction(db):
    """Context manager for database transactions."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


# Usage
with database_transaction(db) as session:
    session.execute("INSERT ...")
    session.execute("UPDATE ...")
# Automatically commits or rolls back
```

## Iterators and Generators

### Generators for Memory Efficiency

```python
from typing import Iterator


# ✅ Generator - memory efficient
def read_large_file(file_path: Path) -> Iterator[str]:
    """Read large file line by line."""
    with file_path.open() as f:
        for line in f:
            yield line.strip()


# Process without loading entire file
for line in read_large_file(Path("huge_file.txt")):
    process_line(line)


# ❌ Loading entire file
def read_large_file_bad(file_path: Path) -> list[str]:
    with file_path.open() as f:
        return [line.strip() for line in f]  # All in memory!
```

### Generator Expressions

```python
# ✅ Generator expression (lazy evaluation)
total = sum(x**2 for x in range(1000000))  # Memory efficient

# ❌ List comprehension (eager, uses memory)
total = sum([x**2 for x in range(1000000)])  # List in memory
```

## Modern String Methods

### String Methods

```python
text = "  Hello, World!  "

# ✅ Modern string methods
text.strip()  # "Hello, World!"
text.lower()  # "  hello, world!  "
text.upper()  # "  HELLO, WORLD!  "
text.replace("World", "Python")  # "  Hello, Python!  "
text.split(",")  # ['  Hello', ' World!  ']

# Check string properties
text.startswith("  Hello")  # True
text.endswith("!")  # True
"123".isdigit()  # True
"abc".isalpha()  # True
```

### String Joining

```python
words = ["Hello", "Python", "World"]

# ✅ Join with separator
" ".join(words)  # "Hello Python World"
", ".join(words)  # "Hello, Python, World"

# ❌ Manual concatenation
result = ""
for word in words:
    result += word + " "
```

## Dataclasses

### Define Data Classes

```python
from dataclasses import dataclass, field
from typing import List


# ✅ Dataclass (Python 3.7+)
@dataclass
class User:
    """User data class."""

    id: int
    username: str
    email: str
    is_active: bool = True
    tags: List[str] = field(default_factory=list)


# Automatic __init__, __repr__, __eq__
user = User(id=1, username="alice", email="alice@example.com")
print(user)  # User(id=1, username='alice', ...)


# ❌ Manual class
class User:
    def __init__(self, id, username, email, is_active=True, tags=None):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active
        self.tags = tags or []

    def __repr__(self):
        return f"User({self.id}, {self.username}, ...)"

    def __eq__(self, other):
        return (
            self.id == other.id and self.username == other.username
            # ... many more fields
        )
```

### Frozen Dataclasses (Immutable)

```python
@dataclass(frozen=True)
class Point:
    """Immutable point."""

    x: float
    y: float


point = Point(1.0, 2.0)
# point.x = 3.0  # Raises FrozenInstanceError
```

## Enums

```python
from enum import Enum, auto


class Status(Enum):
    """Status enumeration."""

    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()


# Usage
current_status = Status.PROCESSING

if current_status == Status.COMPLETED:
    print("Done!")

# String representation
print(current_status.name)  # "PROCESSING"
print(current_status.value)  # 2
```
