# Testing With Live Data

Production-quality integration testing using real data from existing systems.

## Principle

Integration tests MUST use REAL, EXISTING data from production systems, not fake/mock data.

## Rationale

- **Tests verify actual system behavior** - Not theoretical behavior with fake data
- **Catches real-world edge cases** - Data quality issues, format variations, scale problems
- **No data synchronization needed** - Test data automatically stays current with production
- **Tests what users actually experience** - Real workflows, real data, real edge cases
- **Prevents test/production drift** - Tests fail when production data structure changes

## Core Rules

### ✅ ALWAYS

1. **Use existing test infrastructure** - Check `conftest.py` for fixtures
2. **Connect to existing live data** - Use project configs to find data locations
3. **Test against real production data** - Query real databases, read real files
4. **Mock only external APIs** - HTTP requests, email sending, external services

### ❌ NEVER

1. **Create new databases/collections for testing** - Wastes time, creates confusion
2. **Create new configs** - Use existing project configs
3. **Run vectorization/indexing to create test data** - Use existing indexed data
4. **Create fake fixtures when live data exists** - Defeats purpose of integration testing
5. **Mock internal code** - Tests should verify real internal behavior

## Pattern: Correct Testing Approach

### Step 1: Find Existing Test Infrastructure

**Check `conftest.py`:**

```python
# Example: /home/nic/src/zotmcp/src/tests/conftest.py
@pytest.fixture
async def mcp_server():
    """MCP server connected to EXISTING ChromaDB."""
    # Uses existing config to find data location
    server = await initialize_server()  # Connects to .zotmcp_data/chromadb/
    yield server
    await server.cleanup()
```

### Step 2: Use Fixtures to Access Live Data

```python
# Test file: src/tests/test_search.py
async def test_metadata_search(mcp_server):  # Uses existing fixture
    """Test metadata search finds known authors in REAL Zotero library."""

    # Connects to EXISTING ChromaDB via fixture
    result = await mcp_server.search("suzor", search_mode="metadata")

    # Verify against REAL data
    assert len(result) > 0, "Should find Suzor in existing library"
    assert any("suzor" in r.citation.lower() for r in result)
```

### Step 3: Locate Live Data From Project Config

**Check project README or config files:**

```bash
# Example: Where is the data?
cat /home/nic/src/zotmcp/README.md  # Look for data location
cat /home/nic/src/zotmcp/conf/config.yaml  # Check Hydra configs
```

**Common patterns:**
- Buttermilk projects: `~/.cache/buttermilk/chromadb/`
- Project-specific: `.zotmcp_data/chromadb/`
- Shared data: `/data/` or `~/data/`

## Anti-Patterns (DO NOT DO THIS)

### ❌ Creating New Test Database

```python
# WRONG - Creates new database
def test_search():
    client = chromadb.Client()  # New database instance
    collection = client.create_collection("test_data")  # New collection

    # Creates fake data
    collection.add(
        documents=["fake paper about moderation"],
        metadatas=[{"author": "suzor", "title": "fake"}],
        ids=["fake-id"]
    )

    # Tests fake data - not real system!
    result = search(collection, "suzor")
```

**Problems:**
- Fake data doesn't match production reality
- Misses real edge cases (malformed metadata, CID corruption, etc.)
- Test passes but real system might fail
- Wasted time creating fake data

### ❌ Running Vectorization for Tests

```python
# WRONG - Runs expensive indexing pipeline
def test_search():
    # Runs vectorization on small test corpus
    vectorize_data(source="test_data/", output="test_chromadb/")

    collection = load_collection("test_chromadb/")
    result = search(collection, "moderation")
```

**Problems:**
- Wastes time running vectorization
- Creates confusion about which data is canonical
- Test data quickly becomes stale
- Duplicates production pipeline unnecessarily

## When Mocking IS Appropriate

Mock ONLY at system boundaries (external APIs you don't control):

### ✅ Mock External HTTP APIs

```python
async def test_fetch_external_data(respx_mock):
    """Mock external API call."""
    respx_mock.get("https://api.external.com/data").mock(
        return_value=httpx.Response(200, json={"result": "success"})
    )

    # Test uses real internal code, mocks external API
    result = await fetch_from_api()
    assert result["result"] == "success"
```

### ✅ Mock Email Sending

```python
def test_send_notification(mocker):
    """Mock email sending (don't actually send)."""
    mock_smtp = mocker.patch("smtplib.SMTP")

    # Test uses real notification logic, mocks SMTP
    send_notification("user@example.com", "message")
    mock_smtp.assert_called_once()
```

## Diagnostic Checklist

Before writing any test, verify:

- [ ] Checked `conftest.py` for existing fixtures?
- [ ] Identified live data location from project config?
- [ ] Confirmed test uses real data, not mocks?
- [ ] Verified NOT creating new databases/configs?
- [ ] Verified NOT running indexing/vectorization?
- [ ] Confirmed mocking ONLY external APIs (if any)?

## Example Projects

### zotmcp (Zotero Search)

**Live data:** `/home/nic/.cache/buttermilk/chromadb/`
**Test fixture:** `mcp_server` in `conftest.py`
**Pattern:** Tests connect to real Zotero library via ChromaDB

```python
async def test_author_search(mcp_server):
    """Find known author in real library."""
    result = await mcp_server.search("klonick", search_mode="metadata")
    assert len(result) > 0
```

### buttermilk (MLOps Library)

**Live data:** Test projects in `tests/fixtures/projects/`
**Test fixture:** `sample_project` in `conftest.py`
**Pattern:** Tests use real dbt projects, real BigQuery schemas

```python
def test_dbt_manifest_parsing(sample_project):
    """Parse real dbt manifest."""
    manifest = load_manifest(sample_project / "target/manifest.json")
    assert len(manifest.nodes) > 0
```

## Related

- [[../AXIOMS.md#13]] - Verify first
- [[../../../bots/commands/ttd.md]] - TDD workflow
- [[../../python-dev/SKILL.md]] - Python development standards
- [[../../python-dev/references/testing.md]] - Testing philosophy
