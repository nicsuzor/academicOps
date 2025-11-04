# Experiment: Add Interchangeable Components Pattern to Test Instructions

## Metadata
- Date: 2025-11-04
- Issue: #163
- Commit: ca413e1
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Adding explicit guidance about **preferring parameterized tests for interchangeable components** will prevent agents from creating redundant standalone test functions when they should extend existing parameterized test infrastructure.

## Problem

Dev agent created redundant `test_flux11pro_generation()` standalone test function instead of adding `FLUX11Pro` to existing `ImageClients` enum and letting existing `@pytest.mark.parametrize("client", ImageClients)` test cover it.

**Pattern**: Agent failed to recognize:
1. New component is interchangeable with existing ones (same interface)
2. Existing parameterized test already handles this pattern
3. Creating standalone test violates DRY principle

## Changes Made

### 1. test-writing skill (`~/.claude/skills/test-writing/SKILL.md`)

Added new **Pattern 4: Interchangeable Components** section (lines 414-458):
- Definition of interchangeable components
- WRONG example (creating standalone test)
- RIGHT example (extending parameterized test)
- When to create standalone tests (unique behavior, error conditions)
- 3-question checklist before creating new test functions

Added to **Test Quality Checklist** (line 486):
- "Extends parameterized tests for interchangeable components"

### 2. DEVELOPER.md (`agents/DEVELOPER.md`)

Added bullet point to TDD section (line 146):
- "Use fixtures and extend parameterized tests for interchangeable components"

## Success Criteria

**Behavioral metrics** (measure over 5+ test-writing sessions):
1. Agent **asks questions** before creating new test functions ("Could I extend existing parameterized test?")
2. Agent **searches for existing parameterized tests** when adding new interchangeable component
3. **Reduction in redundant standalone tests** for components that share interfaces

**Code quality metrics**:
- No new standalone test functions for interchangeable components
- New components added to existing fixtures/enums/lists
- Parameterized tests cover all component variations

## Results

[To be filled after testing across multiple sessions]

**Test scenarios to monitor**:
- Adding new LLM clients (OpenAI, Anthropic, Gemini, etc.)
- Adding new image generation models
- Adding new data formatters/parsers
- Adding new storage backends

## Outcome

[Success/Failure/Partial - to be determined]

## Notes

**Token cost**: ~54 lines added across 2 files
- test-writing skill: +52 lines
- DEVELOPER.md: +1 line

**Anti-bloat justification**:
- Q1-Q3 (Scripts/Hooks/Config): Cannot reliably detect pattern without context
- Q4 (Instructions): Requires pattern recognition and architectural judgment
- Condensed to concrete examples (WRONG vs RIGHT) following Anthropic best practices
- Added to checklist for quick reference
- No FAQ content or excessive background

**Related improvements needed**:
- Consider adding similar guidance for "load production config, don't duplicate SQL/queries" pattern from original issue #163
