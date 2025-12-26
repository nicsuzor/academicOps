---
title: FastAPI
type: reference
permalink: python-dev-fastapi
description: Modern web framework reference for building REST APIs with Python
---

# FastAPI

## Overview

FastAPI is a modern, high-performance web framework for building APIs with Python using standard Python type hints. It provides automatic API documentation, data validation via Pydantic, and async support.

## When to Use

- Building REST APIs
- Creating web services with automatic documentation
- High-performance async API endpoints
- APIs requiring strong type validation
- Rapid API prototyping with OpenAPI/Swagger

## Installation

```bash
uv add "fastapi[standard]"  # Includes uvicorn server
# Or minimal:
uv add fastapi uvicorn
```

## Basic Application

```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    description="API description",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    """Get item by ID with optional query parameter."""
    return {"item_id": item_id, "q": q}
```

**Run**:

```bash
uvicorn main:app --reload  # Development
uvicorn main:app --host 0.0.0.0 --port 8000  # Production
```

## Request/Response Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional

class Item(BaseModel):
    """Item model with validation."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    tax: Optional[float] = None

@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    """Create new item."""
    return item
```

## Path Parameters

```python
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    """Get model by name (enum validation)."""
    return {"model_name": model_name, "message": "Model found"}

@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    """Path parameter that accepts slashes."""
    return {"file_path": file_path}
```

## Query Parameters

```python
from typing import List

@app.get("/items/")
async def read_items(
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None,
    tags: List[str] = Query(default=[])
):
    """List items with pagination and filtering."""
    return {
        "skip": skip,
        "limit": limit,
        "q": q,
        "tags": tags
    }
```

## Request Body

```python
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: Item,
    q: Optional[str] = None
):
    """Update item (combines path, query, and body)."""
    result = {"item_id": item_id, **item.dict()}
    if q:
        result["q"] = q
    return result
```

## Dependency Injection

```python
from fastapi import Depends, HTTPException, status
from typing import Annotated

# Simple dependency
async def common_parameters(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return commons

# Database session dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
async def read_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)]
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
):
    """Verify JWT token."""
    token = credentials.credentials
    # Verify token logic here
    if not is_valid_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return token

@app.get("/protected")
async def protected_route(token: Annotated[str, Depends(verify_token)]):
    """Protected endpoint."""
    return {"message": "Access granted"}
```

## Error Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Raise HTTP exceptions
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in database:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "Custom header"}
        )
    return database[item_id]

# Custom exception handler
class ItemNotFoundException(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFoundException)
async def item_not_found_handler(request, exc: ItemNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"message": f"Item {exc.item_id} not found"}
    )
```

## Background Tasks

```python
from fastapi import BackgroundTasks

def write_log(message: str):
    """Background task to write log."""
    with open("log.txt", "a") as f:
        f.write(message + "\n")

@app.post("/send-notification/{email}")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    """Send notification in background."""
    background_tasks.add_task(write_log, f"Notification sent to {email}")
    return {"message": "Notification sent in background"}
```

## Testing

```python
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

client = TestClient(app)

def test_read_main():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}

def test_create_item():
    """Test item creation."""
    response = client.post(
        "/items/",
        json={"name": "Test", "price": 10.5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test"
    assert data["price"] == 10.5
```

## Async/Await Patterns

```python
import httpx

@app.get("/external")
async def call_external_api():
    """Call external API asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()

# Use sync def for CPU-bound or sync operations
@app.get("/sync")
def cpu_bound_operation():
    """Synchronous endpoint for CPU-bound work."""
    result = heavy_computation()
    return {"result": result}
```

## CORS (Cross-Origin Resource Sharing)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## File Upload

```python
from fastapi import File, UploadFile

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    """Upload file."""
    contents = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents)
    }

@app.post("/files/")
async def create_files(files: List[UploadFile]):
    """Upload multiple files."""
    return {"filenames": [file.filename for file in files]}
```

## Best Practices

### 1. Use Pydantic for Validation

```python
# ✅ Pydantic models
class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr  # Validates email format
    age: int = Field(..., ge=0, le=150)

# ❌ Dict without validation
@app.post("/user")
async def create_user(user: dict):  # No validation!
    ...
```

### 2. Use Dependency Injection

```python
# ✅ Reusable dependencies
async def get_current_user(token: str = Depends(oauth2_scheme)):
    ...

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    ...

# ❌ Repeated logic
@app.get("/me")
async def read_users_me(token: str):
    # Duplicate auth logic in every endpoint
    ...
```

### 3. Use Response Models

```python
# ✅ Explicit response model
@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    ...

# ❌ Untyped response
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return some_dict  # No validation or filtering
```

### 4. Async for I/O, Sync for CPU

```python
# ✅ Async for I/O operations
@app.get("/data")
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(...)
    return response.json()

# ✅ Sync for CPU-bound
@app.get("/compute")
def compute():
    return heavy_computation()
```

## Common Patterns

### API Versioning

```python
from fastapi import APIRouter

# Version 1
v1_router = APIRouter(prefix="/v1")

@v1_router.get("/items")
async def read_items_v1():
    return {"version": "1.0"}

# Version 2
v2_router = APIRouter(prefix="/v2")

@v2_router.get("/items")
async def read_items_v2():
    return {"version": "2.0", "items": []}

app.include_router(v1_router)
app.include_router(v2_router)
```

### Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment."""
    app_name: str = "My API"
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()

@app.get("/info")
async def info():
    return {"app_name": settings.app_name}
```

## Documentation

Auto-generated docs available at:

- `/docs` - Swagger UI (interactive)
- `/redoc` - ReDoc (alternative)
- `/openapi.json` - OpenAPI schema

## Key Principles

1. **Type hints drive validation** - Use Python type hints for automatic validation
2. **Pydantic for data models** - Leverage Pydantic's validation capabilities
3. **Dependency injection** - Reuse logic through dependencies
4. **Async for I/O** - Use `async def` for I/O-bound operations
5. **Response models** - Define explicit response schemas
6. **Test with TestClient** - Use built-in test client for integration tests

## Resources

- Docs: https://fastapi.tiangolo.com/
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Advanced: https://fastapi.tiangolo.com/advanced/
