---
name: test-writing
description: This skill should be proactively used for all test creation and editing
  tasks. It enforces integration test patterns using real configurations and data,
  follows TDD methodology, and eliminates brittle unit tests. The skill ensures tests
  use real_bm or real_conf fixtures, never mock internal code, and test business behaviors
  rather than implementation details. Use this skill whenever writing new tests or
  refactoring existing test suites.
permalink: aops/skills/test-writing/skill
---

# Test Writing

## Overview

Write robust integration tests that validate real business workflows using actual configurations and data. This skill enforces test-driven development (TDD) principles, real fixture usage, and eliminates brittle patterns like mocking internal code or using fake data.

## When to Use This Skill

Use test-writing when:

1. **Writing new tests** (TDD) - Create failing test before implementation
2. **Editing existing tests** - Fix broken tests or improve test quality
3. **Refactoring test suites** - Consolidate unit tests into integration tests
4. **Test file review** - Ensure tests meet standards

**Concrete trigger examples**:
- "Write a test for user authentication"
- "Fix the failing tests in test_llm.py"
- "Refactor test_orchestrator.py to use real fixtures"
- "Create integration tests for the evaluation workflow"

**Critical**: This skill has authority over test quality. Tests MUST use real configurations (real_bm/real_conf), real data (JSON fixtures), and never mock internal code.

## Core Test Philosophy

### 1. Integration Tests Over Unit Tests

**Delete brittle unit tests**:
- Tests of `__init__` parameters
- Tests of individual method signatures
- Tests that mock our internal code
- Tests with fake/simulated data
- Tests of implementation details

**Write robust integration tests**:
- Tests that exercise complete workflows
- Tests that verify business outcomes
- Tests using real configurations
- Tests with real input/output data
- Tests that would catch production regressions

### 2. NEVER Mock Internal Code

**FORBIDDEN** (delete immediately):
```python
# ❌ WRONG - Mocking OUR code
@patch("buttermilk.core.llm")
@patch("bot.orchestrator")
mock_obj = MagicMock(spec=OurClass)
```

**REQUIRED** (mock only at system boundaries):
```python
# ✅ CORRECT - Mock external APIs only
@respx.mock
async def test_llm_call(real_bm):
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [...]}))

    # Use REAL internal objects
    result = await real_bm.cfg.llm.generate("test prompt")
    assert result.content
```

### 3. Use REAL Configurations via Fixtures

**CRITICAL CONFIG RULE**: NEVER load Hydra configs in test files!

**FORBIDDEN PATTERNS** (block commits with these):
```python
# ❌ NEVER do this in test files:
initialize_config_dir(...)
compose(...)
GlobalHydra
@pytest.fixture that loads configs
```

**REQUIRED PATTERN**:
```python
# ✅ ALWAYS use real_bm or real_conf from conftest.py
def test_with_configured_objects(real_bm):
    # Access fully configured objects
    orchestrator = real_bm.cfg.orchestrator
    llm = real_bm.cfg.llm
    # Test with real objects

def test_with_config_dict(real_conf):
    # Access raw Hydra DictConfig
    orchestrator = instantiate(real_conf.orchestrator)
    # Test with instantiated object
```

### 4. Use REAL Data from JSON Fixtures

**WRONG** (inline fake data):
```python
# ❌ Simulated data in code
records = [{"id": "fake1", "text": "test"}]
```

**RIGHT** (real data from JSON):
```python
# ✅ Load real data from fixtures
records = json.loads(Path("tests/fixtures/input_records.json").read_text())
expected = json.loads(Path("tests/fixtures/expected_output.json").read_text())

results = process(records)
assert results == expected
```

## Follow Follow Test Writing Workflow

Follow this TDD workflow for all test tasks.

### Step 1: Understand What to Test

**For new features (TDD)**:
1. **Identify the business behavior** - What should this feature DO?
2. **Define success criteria** - How do you know it works?
3. **Plan the test** - What inputs, what expected outputs?

**For existing tests (refactoring)**:
1. **Read the test** - Can you understand it in 30 seconds?
2. **Identify anti-patterns**:
   - Mocks of internal code?
   - Fake data?
   - Config loading in test file?
   - Testing implementation details?
3. **Decide**: DELETE or REFACTOR?

### Step 2: Use Existing Fixtures (DON'T Create Config Fixtures!)

**ALWAYS use these existing fixtures from conftest.py**:

- `real_bm` - Provides `real_bm.cfg` with fully configured objects
- `real_conf` - Provides raw Hydra DictConfig from testing.yaml

**Example usage**:
```python
def test_orchestrator_workflow(real_bm):
    \"\"\"Test complete orchestrator workflow with real config.\"\"\"
    orchestrator = real_bm.cfg.orchestrator

    # Load real test data
    records = load_json_fixture("tests/fixtures/input_records.json")

    # Run real workflow
    results = orchestrator.evaluate(records)

    # Validate against expected output
    expected = load_json_fixture("tests/fixtures/expected_results.json")
    assert results == expected
```

**DO NOT create new config-loading fixtures!**:
```python
# ❌ PROHIBITED - This will be caught in code review
@pytest.fixture
def configured_orchestrator():
    with initialize_config_dir(...):  # ❌ FORBIDDEN!
        cfg = compose(...)
        return instantiate(cfg.orchestrator)
```

### Step 3: Create JSON Fixture Files

**Organize test data as JSON files**:

```
tests/fixtures/
  llm_evaluation/
    input_records.json          # Real input data
    expected_evaluation.json    # Expected outputs
  orchestrator/
    simple_workflow_input.json
    simple_workflow_output.json
```

**Pattern**:
```python
def load_json_fixture(filepath: str):
    \"\"\"Load JSON fixture file.\"\"\"
    return json.loads(Path(filepath).read_text())

def test_evaluation_workflow():
    inputs = load_json_fixture("tests/fixtures/llm_evaluation/input_records.json")
    expected = load_json_fixture("tests/fixtures/llm_evaluation/expected_evaluation.json")

    results = evaluate(inputs)
    assert results == expected
```

### Step 4: Write the Test (TDD: Test-First!)

**TDD Process**:
1. **Write FAILING test first** - Test should fail because feature doesn't exist yet
2. **Run test to verify it fails** - `uv run pytest tests/test_file.py::test_name -xvs`
3. **Implement minimum code** to make test pass
4. **Run test to verify it passes** - Same pytest command
5. **Refactor if needed** - Keep test passing

**Test structure** (Arrange-Act-Assert):
```python
@pytest.mark.anyio  # For async tests
async def test_llm_generates_valid_response(real_bm):
    \"\"\"Verify LLM processes prompt and returns valid response.\"\"\"

    # ARRANGE - Set up test data and dependencies
    llm = real_bm.cfg.llm
    prompt = "What is 2+2?"

    # Mock external API boundary only
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "4"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1}
        })
    )

    # ACT - Execute the behavior being tested
    result = await llm.generate(prompt)

    # ASSERT - Verify expected outcomes
    assert result.content == "4"
    assert result.usage.total_tokens == 6
    assert real_bm.trace_id  # Real tracing logic executed
```

**Test naming convention**:
```python
# ✅ Descriptive behavior-based names
def test_user_can_login_with_valid_credentials(real_bm):
def test_evaluation_persists_results_to_bigquery(real_conf):
def test_invalid_api_key_raises_authentication_error(real_bm):

# ❌ Implementation-based names
def test_init_params():
def test_call_method():
def test_validate_config():
```

### Step 5: Mock Only at System Boundaries

**System Boundaries (OK to mock)**:
- HTTP calls: Use `respx` or `httpx`
- File system: Use `tmp_path` fixture
- Time: Use `freezegun`
- Environment variables: Use `monkeypatch`
- External processes: Mock `subprocess`
- Cloud services: Mock GCP/AWS SDK clients

**Our Code (NEVER mock)**:
- Anything in `buttermilk.*`
- Anything in `bot.*`
- Any project-specific code
- Business logic
- Data transformations

**Example - External API mocking**:
```python
@respx.mock
async def test_llm_api_call(real_bm):
    \"\"\"Test LLM handles API response correctly.\"\"\"

    # Mock ONLY the external HTTP boundary
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={...})
    )

    # Use REAL internal LLM object
    llm = real_bm.cfg.llm
    result = await llm.generate("test")

    # Verify real internal logic executed
    assert result.content
    assert llm.trace_id  # Real tracing happened
```

### Step 6: Run and Verify Tests

**Commands**:
```bash
# Run specific test
uv run pytest tests/test_file.py::test_name -xvs

# Run all tests in file
uv run pytest tests/test_file.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

**TDD verification**:
1. **Test fails initially** (feature not implemented)
2. **Implement minimum code**
3. **Test passes** (feature works)
4. **All other tests still pass** (no regressions)

### Step 7: Refactor Ruthlessly

**Delete these immediately**:
```python
# ❌ Mocking internal code
@patch("buttermilk.llm")
@patch("bot.orchestrator")

# ❌ Fake data
record = BaseRecord(record_id="fake", ...)

# ❌ Config loading in tests
with initialize_config_dir(...):
@pytest.fixture that uses compose()

# ❌ Testing implementation
def test_init_params():
def test_internal_helper():

# ❌ Complex mock setups
mock.method.return_value.attribute.side_effect = [...]
```

**Consolidate 10 unit tests → 1 integration test**:
```python
# BEFORE: 10 tests, 300 lines
def test_init_valid():
def test_init_invalid():
def test_setup_storage():
def test_setup_llm():
def test_load_records():
def test_process_record():
def test_save_results():
def test_error_handling():
def test_cleanup():
def test_trace_logging():

# AFTER: 1 test, 25 lines
@pytest.mark.anyio
async def test_complete_evaluation_workflow(real_bm, load_json_fixture):
    \"\"\"End-to-end workflow test with real config and data.\"\"\"
    orchestrator = real_bm.cfg.orchestrator

    inputs = load_json_fixture("tests/fixtures/evaluation_input.json")
    expected = load_json_fixture("tests/fixtures/evaluation_output.json")

    results = await orchestrator.run(inputs)

    assert results == expected
    assert orchestrator.trace.is_persisted()
```

## Common Test Patterns

### Pattern 1: Simple Synchronous Test

```python
def test_data_processing(real_conf):
    \"\"\"Test data processor with real configuration.\"\"\"
    processor = instantiate(real_conf.processor)

    input_data = load_json_fixture("tests/fixtures/processor_input.json")
    expected = load_json_fixture("tests/fixtures/processor_output.json")

    result = processor.process(input_data)
    assert result == expected
```

### Pattern 2: Async Test with External API Mock

```python
@pytest.mark.anyio
@respx.mock
async def test_llm_evaluation(real_bm):
    \"\"\"Test LLM evaluation with mocked API.\"\"\"
    # Mock external API
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "Good response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        })
    )

    # Use real configured LLM
    llm = real_bm.cfg.llm
    result = await llm.generate("Test prompt")

    assert result.content == "Good response"
    assert result.usage.total_tokens == 15
```

### Pattern 3: Parametrized Test with Real Data

```python
@pytest.mark.parametrize("fixture_file,expected_file", [
    ("input_case1.json", "expected_case1.json"),
    ("input_case2.json", "expected_case2.json"),
    ("input_case3.json", "expected_case3.json"),
])
def test_multiple_scenarios(real_conf, fixture_file, expected_file):
    \"\"\"Test multiple scenarios with different input/output pairs.\"\"\"
    processor = instantiate(real_conf.processor)

    inputs = load_json_fixture(f"tests/fixtures/{fixture_file}")
    expected = load_json_fixture(f"tests/fixtures/{expected_file}")

    results = processor.process(inputs)
    assert results == expected
```

### Pattern 4: Interchangeable Components (Fixtures + Parameterization)

**CRITICAL PRINCIPLE**: When testing interchangeable components (clients, models, formatters, handlers), **ALWAYS prefer extending existing parameterized tests** over creating new standalone test functions.

**Interchangeable components** share:
- Same interface/base class
- Same test scenarios
- Different implementations (providers, models, formats)

**WRONG - Creating redundant standalone test**:
```python
# ❌ Existing parameterized test
@pytest.mark.parametrize("client", [OpenAIClient, AnthropicClient])
async def test_client(client):
    result = await client().generate("test")
    assert result.content

# ❌ WRONG - New standalone test for new client
async def test_gemini_client():
    """Test Gemini client."""
    result = await GeminiClient().generate("test")
    assert result.content
```

**RIGHT - Extending parameterized test**:
```python
# ✅ Add to existing list/enum
LLMClients = [OpenAIClient, AnthropicClient, GeminiClient]

# ✅ Existing parameterized test now covers all clients
@pytest.mark.parametrize("client", LLMClients)
async def test_client(client):
    result = await client().generate("test")
    assert result.content
```

**When to create standalone tests**:
- Component has **unique behavior** not shared with others
- Testing **integration between** multiple components
- **Error conditions** specific to one implementation

**Before creating new test function, ask**:
1. Does a parameterized test already cover this pattern?
2. Is this component interchangeable with existing ones?
3. Could I add this to an existing fixture/enum/list instead?

### Pattern 5: File System Operations

```python
def test_file_output(real_bm, tmp_path):
    \"\"\"Test file writing with temporary directory.\"\"\"
    writer = real_bm.cfg.file_writer

    output_file = tmp_path / "output.json"
    test_data = {"key": "value"}

    writer.write(output_file, test_data)

    # Verify file was written correctly
    assert output_file.exists()
    assert json.loads(output_file.read_text()) == test_data
```

## Test Quality Checklist

Before committing tests, verify:

✅ **Uses real_bm or real_conf** from conftest.py
✅ **No config loading** in test files (no initialize_config_dir, compose, GlobalHydra)
✅ **No mocking internal code** (only external boundaries)
✅ **Uses real data** from JSON fixtures
✅ **Tests behavior**, not implementation
✅ **Extends parameterized tests** for interchangeable components (don't create redundant standalone tests)
✅ **Descriptive test names** (test_user_can_login_with_valid_credentials)
✅ **Clear arrange-act-assert** structure
✅ **Async tests use @pytest.mark.anyio**
✅ **Tests are independent** (can run in any order)
✅ **Tests clean up** after themselves

## Forbidden Patterns (Auto-Reject in Code Review)

These patterns will BLOCK commits:

```python
# ❌ Config loading in test files
initialize_config_dir(config_path="conf")
cfg = compose(config_name="config")
GlobalHydra.instance().clear()

# ❌ Creating config-loading fixtures
@pytest.fixture
def hydra_config():
    with initialize_config_dir(...):
        return compose(...)

# ❌ Mocking internal code
@patch("buttermilk.core.llm")
@patch("bot.orchestrator.Orchestrator")
mock_bm = MagicMock()

# ❌ Fake data in tests
record = BaseRecord(record_id="fake_id", dataset="fake")
config = {"model": "gpt-4", "temp": 0.7}  # Inline config dict

# ❌ Testing implementation details
def test_init_valid_params():
def test_internal_helper_method():
def test_validate_config():
```

## Reference Files

See `references/` for detailed guides:

- `test-patterns.md` - Common test patterns and examples
- `fixture-guide.md` - How to use real_bm and real_conf properly
- `tdd-workflow.md` - Complete TDD cycle guidance

## Success Criteria

A test suite meets standards when:

1. **Zero config loading** in test files (ONLY in conftest.py)
2. **Zero internal mocks** (buttermilk.*, bot.* never mocked)
3. **All data from JSON** fixtures (no inline fake data)
4. **Tests real behaviors** (not implementation details)
5. **Uses existing fixtures** (real_bm, real_conf from conftest.py)
6. **All tests pass** when run with `uv run pytest`
7. **70%+ fewer tests** (consolidated unit → integration)
8. **< 30 seconds** to understand any test

## Quick Reference

**Test creation workflow**:
```bash
# 1. Write failing test (TDD)
def test_new_feature(real_bm):
    result = real_bm.cfg.feature.do_thing()
    assert result == expected

# 2. Run test - verify it fails
uv run pytest tests/test_file.py::test_new_feature -xvs

# 3. Implement feature

# 4. Run test - verify it passes
uv run pytest tests/test_file.py::test_new_feature -xvs

# 5. Run full suite - verify no regressions
uv run pytest tests/
```

**Required imports**:
```python
import pytest
from pathlib import Path
import json
from hydra.utils import instantiate  # If using real_conf
import respx  # For HTTP mocking
import httpx  # For HTTP responses
```

**Test file template**:
```python
\"\"\"Tests for [feature name].

All tests use real_bm or real_conf fixtures from conftest.py.
No config loading in this file.
\"\"\"
import pytest
from pathlib import Path
import json

def load_json_fixture(filepath: str):
    return json.loads(Path(filepath).read_text())

def test_feature_behavior(real_bm):
    \"\"\"Test [specific behavior] with real configuration.\"\"\"
    # Arrange
    feature = real_bm.cfg.feature
    inputs = load_json_fixture("tests/fixtures/feature_input.json")

    # Act
    results = feature.process(inputs)

    # Assert
    expected = load_json_fixture("tests/fixtures/feature_output.json")
    assert results == expected
```
