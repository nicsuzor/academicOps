# FastMCP

## Overview

FastMCP is a Python framework for building Model Context Protocol (MCP) servers. It provides a FastAPI-like interface for creating MCP servers that can expose tools, resources, and prompts to LLM applications.

## When to Use

- Building MCP servers to extend Claude or other LLM capabilities
- Exposing Python functions as LLM-callable tools
- Providing structured resources for LLM context
- Creating reusable prompt templates
- Integrating external systems with LLM workflows

## Installation

```bash
uv add fastmcp
```

## Basic Server

```python
from fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("My Server")

@mcp.tool()
async def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b

@mcp.tool()
async def search_web(query: str, limit: int = 10) -> list[dict]:
    """Search the web for information.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of search results
    """
    # Implementation
    return results
```

**Run**:

```bash
# Development
fastmcp dev server.py

# Production (as stdio server)
uv run python server.py
```

## Tools

Tools are Python functions exposed to LLMs:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool()
async def process_data(
    data: Annotated[str, Field(description="Data to process")],
    format: Annotated[str, Field(description="Output format")] = "json"
) -> dict:
    """Process data and return in specified format."""
    # Process data
    return {"result": processed_data, "format": format}

# Sync tools also supported
@mcp.tool()
def get_timestamp() -> str:
    """Get current timestamp."""
    import datetime
    return datetime.datetime.now().isoformat()
```

## Resources

Resources provide structured data for LLM context:

```python
@mcp.resource("config://app")
async def get_config() -> str:
    """Provide application configuration."""
    config = load_config()
    return json.dumps(config, indent=2)

@mcp.resource("file://{path}")
async def read_file(path: str) -> str:
    """Read file contents.

    Args:
        path: File path to read
    """
    with open(path) as f:
        return f.read()

# List available resources
@mcp.list_resources()
async def list_all_resources() -> list[dict]:
    """List all available resources."""
    return [
        {"uri": "config://app", "name": "App Config"},
        {"uri": "file://README.md", "name": "README"}
    ]
```

## Prompts

Prompts are reusable templates:

````python
@mcp.prompt()
async def code_review_prompt(
    code: str,
    language: str = "python"
) -> str:
    """Generate code review prompt.

    Args:
        code: Code to review
        language: Programming language
    """
    return f"""Review this {language} code:

```{language}
{code}
````

Provide:

1. Code quality assessment
2. Potential bugs or issues
3. Suggestions for improvement """

@mcp.prompt("summarize") async def summarize_prompt(text: str, max_words: int = 100) -> list[dict]: """Generate summarization prompt with context.

    Args:
        text: Text to summarize
        max_words: Maximum words in summary
    """
    return [
        {
            "role": "user",
            "content": f"Summarize in {max_words} words or less:\n\n{text}"
        }
    ]

````
## Context Management

```python
from fastmcp import Context

@mcp.tool()
async def process_with_context(
    data: str,
    ctx: Context
) -> dict:
    """Process data with access to MCP context.

    Args:
        data: Data to process
        ctx: MCP context (injected automatically)
    """
    # Access context
    session_id = ctx.session_id
    client_info = ctx.client_info

    # Use context for logging, tracking, etc.
    logger.info(f"Processing for session {session_id}")

    return {"result": processed, "session": session_id}
````

## Error Handling

```python
from fastmcp import McpError

@mcp.tool()
async def risky_operation(value: int) -> str:
    """Operation that might fail.

    Args:
        value: Input value

    Raises:
        McpError: If value is invalid
    """
    if value < 0:
        raise McpError("Value must be non-negative", code="INVALID_VALUE")

    if value > 100:
        raise McpError("Value too large", code="VALUE_TOO_LARGE")

    return f"Processed: {value}"
```

## Dependency Injection

```python
from typing import Annotated
from fastmcp import Depends

# Dependency
async def get_database():
    """Database connection dependency."""
    db = Database()
    try:
        yield db
    finally:
        db.close()

# Tool with dependency
@mcp.tool()
async def fetch_user(
    user_id: int,
    db: Annotated[Database, Depends(get_database)]
) -> dict:
    """Fetch user from database.

    Args:
        user_id: User ID
        db: Database connection (injected)
    """
    user = await db.get_user(user_id)
    return user.to_dict()
```

## Configuration

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class ServerSettings(BaseSettings):
    """Server configuration."""
    name: str = "My MCP Server"
    version: str = "1.0.0"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = ServerSettings()

mcp = FastMCP(
    name=settings.name,
    version=settings.version
)
```

## Testing

```python
from fastmcp.testing import MCPTestClient

def test_add_numbers():
    """Test add_numbers tool."""
    client = MCPTestClient(mcp)

    result = client.call_tool("add_numbers", a=5, b=3)
    assert result == 8

def test_read_file_resource():
    """Test file resource."""
    client = MCPTestClient(mcp)

    content = client.get_resource("file://test.txt")
    assert "expected content" in content

async def test_async_tool():
    """Test async tool."""
    client = MCPTestClient(mcp)

    result = await client.call_tool_async("async_operation", data="test")
    assert result["status"] == "success"
```

## Best Practices

### 1. Clear Tool Descriptions

```python
# ✅ Comprehensive docstring
@mcp.tool()
async def search(
    query: str,
    limit: int = 10,
    filters: dict | None = None
) -> list[dict]:
    """Search for items matching query.

    Args:
        query: Search query string
        limit: Maximum results to return (default: 10)
        filters: Optional filters to apply

    Returns:
        List of matching items with metadata
    """
    ...

# ❌ Missing context
@mcp.tool()
async def search(query: str) -> list:
    """Search."""  # Too vague!
    ...
```

### 2. Use Pydantic for Complex Types

```python
from pydantic import BaseModel, Field

class SearchFilters(BaseModel):
    """Search filter options."""
    category: str | None = None
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)

@mcp.tool()
async def search(
    query: str,
    filters: SearchFilters | None = None
) -> list[dict]:
    """Search with structured filters."""
    ...
```

### 3. Handle Errors Explicitly

```python
# ✅ Clear error messages
@mcp.tool()
async def delete_file(path: str) -> dict:
    """Delete file at path."""
    if not os.path.exists(path):
        raise McpError(
            f"File not found: {path}",
            code="FILE_NOT_FOUND"
        )

    try:
        os.remove(path)
        return {"status": "deleted", "path": path}
    except PermissionError:
        raise McpError(
            f"Permission denied: {path}",
            code="PERMISSION_DENIED"
        )

# ❌ Silent failures
@mcp.tool()
async def delete_file(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except:
        return False  # What went wrong?
```

### 4. Use Async for I/O

```python
# ✅ Async for I/O operations
@mcp.tool()
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ✅ Sync for CPU-bound
@mcp.tool()
def compute_hash(data: str) -> str:
    """Compute hash of data."""
    return hashlib.sha256(data.encode()).hexdigest()
```

## Common Patterns

### Database Tools

```python
@mcp.tool()
async def query_database(
    sql: str,
    params: dict | None = None,
    db: Annotated[Database, Depends(get_database)]
) -> list[dict]:
    """Execute SQL query.

    Args:
        sql: SQL query to execute
        params: Query parameters
        db: Database connection
    """
    results = await db.execute(sql, params or {})
    return [dict(row) for row in results]
```

### File Operations

```python
@mcp.resource("file://{path}")
async def read_file(path: str) -> str:
    """Read file contents."""
    async with aiofiles.open(path) as f:
        return await f.read()

@mcp.tool()
async def write_file(path: str, content: str) -> dict:
    """Write content to file."""
    async with aiofiles.open(path, 'w') as f:
        await f.write(content)
    return {"status": "written", "path": path, "bytes": len(content)}
```

### External API Integration

```python
@mcp.tool()
async def call_external_api(
    endpoint: str,
    method: str = "GET",
    data: dict | None = None
) -> dict:
    """Call external API.

    Args:
        endpoint: API endpoint
        method: HTTP method
        data: Request data
    """
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(endpoint)
        elif method == "POST":
            response = await client.post(endpoint, json=data)

        return response.json()
```

## Key Principles

1. **Clear documentation** - Comprehensive docstrings help LLMs use tools correctly
2. **Type hints** - Use Pydantic models for complex types
3. **Error handling** - Explicit errors with codes and messages
4. **Async for I/O** - Use async/await for I/O-bound operations
5. **Dependency injection** - Reuse resources through dependencies
6. **Testing** - Use MCPTestClient for integration tests

## Resources

- GitHub: https://github.com/jlowin/fastmcp
- MCP Specification: https://spec.modelcontextprotocol.io/
- Examples: https://github.com/jlowin/fastmcp/tree/main/examples
