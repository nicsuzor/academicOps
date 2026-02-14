---
title: aOps Test Plan
type: spec
description: Comprehensive test plan for the academicOps framework
tags:
  - testing
  - quality
  - roadmap
created: 2026-02-01
---

# aOps Test Plan

Test strategy and roadmap for improving test coverage across the academicOps framework.

## Current State

### Infrastructure

| Component       | Status                                           |
| --------------- | ------------------------------------------------ |
| Framework       | pytest 8.0+ with pytest-xdist                    |
| Parallelization | 4 workers (configurable)                         |
| Markers         | slow, integration, metrics, demo, endtoend, tool |
| Fixtures        | Comprehensive (conftest.py ~1000 LOC)            |
| Documentation   | tests/README.md                                  |

### Test Counts

| Category                 | Count    | Status               |
| ------------------------ | -------- | -------------------- |
| Unit tests               | 680+     | Active               |
| Integration tests        | 21       | Partial pass         |
| Slow tests (Claude exec) | 11       | 73% pass             |
| E2E tests                | Variable | Credential-dependent |

### Coverage by Component

| Component                  | Coverage | Notes                                          |
| -------------------------- | -------- | ---------------------------------------------- |
| aops-core/lib              | High     | task_model, task_storage, session_paths tested |
| aops-core/hooks            | Medium   | gate_registry good, others variable            |
| aops-core/skills/framework | Medium   | 3 test files                                   |
| aops-core/skills/* (other) | None     | 12 skills untested                             |
| aops-tools/skills          | None     | 4 skills, 0 tests                              |
| MCP tools                  | Low      | Basic tool invocation only                     |

## Priority Gaps

### P0 - Critical (Blockers to reliability)

1. **aops-tools skills have zero tests**
   - `pdf`: PDF generation from markdown
   - `excalidraw`: Diagram creation
   - `convert-to-md`: Document format conversion
   - `flowchart`: Mermaid flowchart generation

2. **Hook system edge cases**
   - `router.py`: Prompt routing decisions
   - `user_prompt_submit.py`: User input handling
   - `policy_enforcer.py`: Policy validation

### P1 - High (Impact user experience)

3. **MCP tool integration**
   - Task manager tools (create, update, complete)
   - Memory tools (store, retrieve, recall)
   - Outlook integration

4. **Skill invocation flow**
   - `/skill` command parsing
   - Skill loading and execution
   - Error handling during skill execution

### P2 - Medium (Technical debt)

5. **Session management**
   - `session_state.py`: State transitions
   - `session_reader.py`: Transcript parsing
   - `transcript_parser.py`: Complex parsing logic

6. **Large script coverage**
   - `analyst/scripts/assumption_checks.py` (16K LOC)
   - `garden/scripts/lint_frontmatter.py` (12K LOC)
   - `hypervisor/scripts/batch_worker.py` (12K LOC)

### P3 - Low (Nice to have)

7. **Documentation validation**
   - All README files reference valid paths
   - Skill documentation matches implementation
   - API documentation accuracy

## Test Plan by Phase

### Phase 1: aops-tools Skills (P0)

**Goal**: Basic test coverage for all aops-tools skills

**Deliverables**:

```
aops-tools/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_pdf_skill.py        # PDF generation tests
│   ├── test_excalidraw_skill.py # Diagram tests
│   ├── test_convert_skill.py    # Conversion tests
│   └── test_flowchart_skill.py  # Flowchart tests
```

**Test Cases per Skill**:

#### PDF Skill

- [ ] Valid markdown → PDF conversion
- [ ] Invalid markdown handling
- [ ] Font availability check
- [ ] Output path creation
- [ ] Overwrite behavior

#### Excalidraw Skill

- [ ] Valid input → diagram JSON
- [ ] Element placement validation
- [ ] Color/style application
- [ ] Invalid input handling

#### Convert-to-MD Skill

- [ ] DOCX → markdown
- [ ] PDF → markdown
- [ ] XLSX → markdown
- [ ] Tracked changes preservation
- [ ] Comment extraction

#### Flowchart Skill

- [ ] Valid mermaid syntax generation
- [ ] Node/edge validation
- [ ] Layout compliance
- [ ] Accessibility (labels present)

**Estimated Effort**: 20-30 tests, ~2-3 hours

### Phase 2: Hook System (P0-P1)

**Goal**: Comprehensive hook testing

**Deliverables**:

```
tests/hooks/
├── test_router.py
├── test_user_prompt_submit.py
├── test_policy_enforcer.py
├── test_command_intercept.py
└── test_task_binding.py
```

**Test Cases**:

#### Router

- [ ] Skill routing detection
- [ ] Task context extraction
- [ ] Default routing behavior
- [ ] Error recovery

#### Policy Enforcer

- [ ] Valid policy enforcement
- [ ] Policy bypass conditions
- [ ] Policy conflict resolution

**Estimated Effort**: 15-20 tests, ~2 hours

### Phase 3: MCP Tool Integration (P1)

**Goal**: Verify MCP tool reliability

**Deliverables**:

```
tests/tools/
├── test_task_manager_tools.py
├── test_memory_tools.py
└── test_outlook_tools.py
```

**Test Cases**:

#### Task Manager

- [ ] create_task validation
- [ ] update_task field handling
- [ ] complete_task state transition
- [ ] decompose_task parent/child
- [ ] list_tasks filtering
- [ ] search_tasks query matching

#### Memory

- [ ] store_memory persistence
- [ ] retrieve_memory semantic search
- [ ] recall_memory time expressions
- [ ] search_by_tag operations

**Estimated Effort**: 25-35 tests, ~3-4 hours

### Phase 4: Session Management (P2)

**Goal**: Validate session state handling

**Test Areas**:

- State transitions
- Transcript parsing edge cases
- Session summary generation
- Multi-session context

**Estimated Effort**: 30-40 tests, ~4-5 hours

## Test Patterns

### Unit Test Template

```python
"""Tests for <component>."""

import pytest
from pathlib import Path


class Test<ComponentName>:
    """<Component> functionality tests."""

    def test_<action>_with_valid_input(self) -> None:
        """<Action> succeeds with valid input."""
        # Arrange
        input_data = ...

        # Act
        result = component.action(input_data)

        # Assert
        assert result.success
        assert result.output == expected

    def test_<action>_with_invalid_input_raises(self) -> None:
        """<Action> raises on invalid input."""
        with pytest.raises(ValueError, match="specific message"):
            component.action(invalid_data)
```

### Integration Test Template

```python
"""Integration tests for <feature>."""

import pytest


@pytest.mark.integration
class Test<Feature>Integration:
    """<Feature> integration tests."""

    def test_end_to_end_workflow(self, fixture) -> None:
        """Complete workflow from input to output."""
        # Full workflow test
        pass

    @pytest.mark.slow
    def test_with_claude_execution(self, claude_headless) -> None:
        """Test requiring Claude Code execution."""
        result = claude_headless(prompt="...", timeout_seconds=120)
        assert result["success"]
```

## Success Metrics

| Metric                | Current  | Target (Phase 1) | Target (Full) |
| --------------------- | -------- | ---------------- | ------------- |
| Total tests           | 680+     | 700+             | 800+          |
| aops-tools coverage   | 0%       | 80%              | 95%           |
| Hook coverage         | 40%      | 70%              | 90%           |
| Integration pass rate | 73%      | 90%              | 95%           |
| CI pipeline pass      | Variable | Stable           | Green         |

## Running Tests

```bash
# Default fast tests
uv run pytest tests/

# Include integration
uv run pytest tests/ -m integration

# Include slow tests
uv run pytest tests/ -m slow

# All tests
uv run pytest tests/ -m "not endtoend"

# Specific component
uv run pytest tests/tools/test_task_manager_tools.py -v

# With coverage
uv run pytest tests/ --cov=aops-core --cov-report=html
```

## Implementation Notes

### Fixture Reuse

Leverage existing fixtures from `tests/conftest.py`:

- `writing_root`: Framework root path
- `test_data_dir`: Temporary task directory
- `claude_headless`: Claude Code execution

### Test Isolation

- Use `tmp_path` for file operations
- Mock external services (Outlook, memory server)
- Reset state between tests

### CI Integration

Tests should work with:

- GitHub Actions (`framework-health.yml`)
- Pre-commit hooks
- Local development

## Next Steps

1. **Immediate**: Create `aops-tools/tests/` directory structure
2. **Week 1**: Implement Phase 1 (aops-tools skills)
3. **Week 2**: Implement Phase 2 (hooks)
4. **Week 3-4**: Implement Phases 3-4 (MCP, session)

## References

- [[tests/README.md]] - Existing test documentation
- [[pyproject.toml]] - Test configuration
- [[AXIOMS.md]] - Testing philosophy
