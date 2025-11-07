# Development Workflow

## 🚨 CRITICAL: Systematic Development Process

The #1 rule: **STOP → ANALYZE → PLAN → TEST → IMPLEMENT → DOCUMENT → COMMIT**

## Development Phases

### Phase 1: STOP - Don't Rush

Before writing ANY code:

- Understand the full problem scope.
- Check GitHub issues for related work.
- Identify all stakeholders and impacts.
- Question assumptions.

### Phase 2: ANALYZE - Map the Territory

```bash
# Check existing issues
gh issue list --search "relevant keywords"

# If no issue exists, create one
gh issue create --title "Clear problem description" --body "Detailed analysis"
```

Key Analysis Steps:

1. **Trace Data Flow**: Understand the data lifecycle.
2. **Map Dependencies**: What touches what?
3. **Identify Root Cause**: Not symptoms, but actual problems.
4. **Check Error Propagation**: Are exceptions being handled and logged properly?
5. **Verify Configuration Chain**: Check for proper inheritance and paths.
6. **Check Schema Contracts**: Ensure data structures match across all components.
7. **Document Findings**: Update the GitHub issue.

### Phase 3: PLAN - Design Before Code

Create a clear plan in a GitHub issue with:

- Phases and milestones
- Success criteria
- Test cases
- Rollback strategy

### Phase 4: TEST - Failing Tests First

**CRITICAL: Tests MUST be in the `tests/` directory using pytest conventions.**

```python
# File: tests/module/test_feature.py (NEVER create test files elsewhere)
import pytest

@pytest.mark.anyio
async def test_expected_behavior():
    """Test that demonstrates the problem."""
    # This should pass when fixed
    assert 1 == 1 # Replace with real test
```

**Run tests with:** `uv run pytest tests/`

### Phase 5: IMPLEMENT - Minimal Changes

- Make the smallest change that fixes the root cause.
- Don't add "nice to have" features.
- Keep existing interfaces stable.
- Follow existing patterns.

### Phase 6: DOCUMENT - Keep It Current

- Update docstrings.
- Add inline comments for complex logic.
- Update relevant `.md` files.
- Ensure examples still work.

### Phase 7: COMMIT - Track Progress

```bash
# Commit with clear message referencing the issue
git add -A
git commit -m "fix: Clear description of what and why

Fixes #123"

# Update GitHub issue
gh issue comment 123 --body "Fixed in commit abc123."
```

## GitHub Workflow

- **ALWAYS** check for existing issues before starting work.
- **ALWAYS** create or update an issue to document your plan and progress.
- **ALWAYS** link commits to issues.

## INTERACTIVE DEVELOPMENT

When working directly with the user in a back-and-forth exchange, you must follow their directions PRECISELY.

- **DO NOT** jump ahead or anticipate steps.
- Acknowledge and wait at each step if the user indicates a pause.
- Your role is to be a tool that the user is guiding, not an autonomous agent.

## Anti-Patterns to Avoid

### 🚫 Red Flags - Stop Immediately If You're:

1. About to create ANY test file outside the `tests/` directory.
2. Saying "let me test this" or "validate my implementation" without using pytest.
3. Proposing config changes without understanding the data flow.
4. Making multiple small fixes instead of one root cause fix.
5. Suggesting "try this" without a systematic plan.
6. Modifying code without tests demonstrating the problem.
7. Making "quick fixes" to suppress errors.

### 🚫 Never Do These:

- **Standalone Test Scripts**: All tests must be in the `tests/` directory and use `pytest`.
- **Superficial Fixes**: Do not change validation rules (e.g. Pydantic's `extra="forbid"`) to hide errors.
- **Type Suppression**: Do not use `type: ignore`.
- **Defensive Overload**: Do not add excessive checks for valid data. Let it fail.
- **Schema Violations**: Do not support multiple locations for the same data or provide "safe" defaults. Trust the schema.
- **Manual Configuration**: Do not create configurations in code; use YAML or designated config files.
- **Silent Configuration Defaults**: NEVER use `.get(key, default)` for configuration parameters (see below).

## Configuration Anti-Patterns

### ❌ PROHIBITED: `.get()` with Defaults on Configuration

**DO NOT use `.get()` with default values for configuration parameters:**

```python
# ❌ PROHIBITED - Silent misconfiguration corrupts research data
timeout = kwargs.get("timeout", 30)
error_threshold = config.get("error_threshold", 0.5)
max_retries = params.get("max_retries", 3)
```

**WHY THIS IS CRITICAL:**

- Silent defaults hide misconfiguration for **months**
- Research data can be corrupted without any errors
- Violates fail-fast philosophy essential for academic integrity
- Pre-commit hook will **BLOCK** commits with this pattern

### ✅ REQUIRED: Explicit Configuration Validation

**Option 1: Pydantic (PREFERRED for all new code)**

```python
from pydantic import BaseModel, Field

class HostConfig(BaseModel):
    """Configuration with REQUIRED parameters."""
    timeout: int = Field(description="Max seconds to wait")
    error_threshold: float = Field(ge=0.0, le=1.0)
    max_retries: int = Field(gt=0)

    # NO defaults - raises ValidationError if missing

# Usage
config = HostConfig(**kwargs)  # Fails immediately if timeout not provided
```

**Option 2: Explicit KeyError**

```python
# Fails immediately with clear error
if "timeout" not in kwargs:
    raise ValueError("timeout must be explicitly configured")
timeout = kwargs["timeout"]
```

**Option 3: Property with Validation**

```python
@property
def timeout(self) -> int:
    """Get timeout from parameters. Must be explicitly set."""
    if "timeout" not in self.parameters:
        raise ValueError(
            f"{self.agent_name}: 'timeout' must be explicitly set in parameters"
        )
    return self.parameters["timeout"]
```

**See:** Issue #100 for full analysis and enforcement strategy.

## Remember

1. **Systematic Approach**: Don't guess, investigate.
2. **One Change at a Time**: Isolate variables.
3. **Document Everything**: Your future self will thank you.
4. **Ask for Help**: Check issues, ask the team.
5. **Take Breaks**: Fresh eyes see more.
