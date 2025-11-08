## True End-to-End Testing

**TRUE E2E = Real APIs + Real Storage + Real Data. NO MOCKS.**

### Core Principle

End-to-end tests verify the COMPLETE workflow with REAL components:

- ✅ Real API calls (Vertex AI, Zotero API, external services)
- ✅ Real storage (ChromaDB, BigQuery, file systems)
- ✅ Real processors (SemanticSplitter, EmbeddingGenerator, etc.)
- ✅ Real configuration (via `real_bm` fixture)
- ✅ Real data flowing through the entire pipeline

**NOT end-to-end**:

- ❌ Mocking internal code
- ❌ Mocking our own APIs/services
- ❌ Fake data or simulated responses
- ❌ Partial pipeline execution

### When to Mock

**Mock ONLY at system boundaries you don't control**:

- External third-party APIs you can't call in tests
- Services requiring paid credentials for every test run
- Infrastructure you don't own (but document why)

**Example - What to mock**:

```python
# DON'T mock this (it's OUR code):
# @patch("buttermilk.data.vector.ChromaDBEmbeddings")

# DO mock this (it's Google's API):
# @patch("google.cloud.aiplatform.Endpoint")  # Only if needed
```

**Prefer real calls when possible**: If you have test credentials, use real APIs.

### E2E Test Structure

```python
@pytest.mark.anyio
async def test_complete_zotero_vectorization_pipeline(real_bm):
    \"\"\"TRUE E2E test - uses REAL everything.\"\"\"

    # ARRANGE: Create realistic test data
    test_record = Record(
        record_id="E2E_TEST",
        dataset="zotero",
        content="Real content from realistic source...",
        metadata={"title": "Real Test Document"},
    )

    # ACT: Run REAL pipeline components

    # Step 1: REAL SemanticSplitter
    splitter = SemanticSplitter(chunk_size=100, chunk_overlap=20)
    chunked_records = [rec async for rec in splitter.process(test_record)]

    # Step 2: REAL EmbeddingGenerator (calls Vertex AI!)
    embedding_gen = EmbeddingGenerator(
        embedding_model="text-embedding-004",
        dimensionality=768,
    )
    embedded_records = [rec async for rec in embedding_gen.process(chunked_records[0])]

    # Step 3: REAL ChromaDB storage
    with tempfile.TemporaryDirectory() as tmpdir:
        embeddings = ChromaDBEmbeddings(
            persist_directory=str(Path(tmpdir) / "test_db"),
            collection_name="e2e_test",
            embedding_model="text-embedding-004",
            dimensionality=768,
        )
        await embeddings.ensure_cache_initialized()

        # This calls REAL ChromaDB API
        result = await embeddings.process_record(
            embedded_records[0],
            skip_existing=False,
        )

    # ASSERT: Verify complete pipeline succeeded
    assert result.status == "processed"
    assert result.chunks_created > 0
```

### Test Isolation

**Use temporary resources for test isolation**:

```python
# Temporary directories for file systems
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "test_chromadb"
    # Use real ChromaDB, just in temp location

# Temporary collections with unique names
collection_name = f"test_collection_{uuid.uuid4()}"

# Test-specific credentials/projects (if available)
# Use environment variables for test-specific resources
```

### E2E vs Integration vs Unit

**Unit Test** (isolated component):

- Tests single function/class
- Mocks all dependencies
- Fast, focused

**Integration Test** (components working together):

- Tests 2-3 components interacting
- Real configuration via `real_bm`
- May mock external APIs

**TRUE End-to-End Test** (complete workflow):

- Tests entire pipeline start to finish
- REAL everything (APIs, storage, processors)
- Slower but validates production workflow
- NO mocks except unavoidable external systems

### Success Criteria for E2E Tests

A TRUE E2E test must:

1. ✅ Use `real_bm` fixture for configuration
2. ✅ Call real APIs (document any mocked external systems)
3. ✅ Store data in real databases (temp locations OK)
4. ✅ Exercise complete workflow from input to output
5. ✅ Validate end-to-end behavior, not intermediate steps
6. ✅ Use realistic test data
7. ✅ Clean up resources after test

### Common E2E Test Patterns

**Pattern 1: Pipeline Test**

```python
async def test_full_pipeline(real_bm):
    \"\"\"Test source → process → store workflow.\"\"\"
    # Real source
    records = await real_source.fetch()

    # Real processing
    processed = await real_processor.process(records[0])

    # Real storage
    result = await real_storage.store(processed)

    # Validate end result
    assert result.success
```

**Pattern 2: API Integration Test**

```python
async def test_external_api_integration(real_bm):
    \"\"\"Test integration with external service.\"\"\"
    # Real API client
    client = RealAPIClient(credentials=test_credentials)

    # Real request
    response = await client.query("test query")

    # Validate response structure and content
    assert response.status_code == 200
    assert "expected_field" in response.data
```

**Pattern 3: Storage Round-Trip Test**

```python
async def test_storage_round_trip(real_bm):
    \"\"\"Test data survives storage and retrieval.\"\"\"
    # Real data
    data = create_test_data()

    # Real storage (temp location)
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = RealStorage(path=tmpdir)

        # Store
        await storage.save(data)

        # Retrieve
        retrieved = await storage.load(data.id)

        # Validate round-trip
        assert retrieved == data
```

### Documentation

When writing E2E tests, document:

```python
\"\"\"TRUE end-to-end test for [workflow name].

This test uses REAL components:
- Real [API/service]: [Description, note any credentials needed]
- Real [Processor]: [Description]
- Real [Storage]: [Description, note temp location usage]

NO mocks except: [List any unavoidable mocked external systems with justification]

This validates the complete [workflow] from [start] to [end].
\"\"\"
```

### Anti-Patterns

**❌ WRONG - Not E2E**:

```python
@patch("buttermilk.data.vector.ChromaDBEmbeddings")
@patch("buttermilk.processors.embeddings.EmbeddingGenerator")
async def test_pipeline(mock_embeddings, mock_chromadb):
    # This is NOT E2E - it's all mocks!
    pass
```

**✅ CORRECT - TRUE E2E**:

```python
async def test_pipeline(real_bm):
    # Real components
    splitter = SemanticSplitter(...)  # Real
    embedder = EmbeddingGenerator(...)  # Real, calls Vertex AI
    storage = ChromaDBEmbeddings(...)  # Real, uses temp dir

    # Real pipeline execution
    result = await run_full_pipeline(splitter, embedder, storage)

    # Validate real results
    assert result.success
```
