# Error Handling Strategy

## Core Principles

1. **Fail Fast**: Detect errors immediately, don't continue with bad state
2. **Fail Informatively**: Provide context about what failed and why
3. **Fail Safely**: Never leave system in inconsistent state
4. **Track Systematically**: Use GitHub issues for recurring problems

## Error Classification

### 1. Tool Errors
**Examples**: File not found, MCP connection failed, API rate limits
**Response**: 
- Log the specific error with context
- Attempt retry with backoff if transient
- Create GitHub issue if recurring pattern
- STOP workflow if critical path blocked

### 2. Validation Errors
**Examples**: API response missing expected fields, malformed data
**Response**:
- Log what was expected vs received
- Check if there's a known issue (search GitHub)
- Create new issue if novel failure mode
- Attempt alternative approach if available

### 3. Logic Errors
**Examples**: Conflicting instructions, impossible requirements
**Response**:
- Document the conflict clearly
- Request clarification from user
- Create issue for instruction improvement
- STOP rather than guess

### 4. Partial Failures
**Examples**: 3 of 5 tasks completed, some emails processed
**Response**:
- NEVER claim full success
- Report exactly what succeeded and failed
- Create recovery plan for failed items
- Continue with successful items if safe

## Standard Error Handling Flow

```
1. DETECT: Check return values, catch exceptions
2. CLASSIFY: Determine error type and severity
3. LOG: Record error with full context
4. DECIDE: Can we recover? Should we continue?
5. ACT: Retry, fallback, or stop
6. REPORT: Update user and create issues if needed
```

## Recovery Strategies

### Immediate Recovery
- **Retry with backoff**: For transient network/API errors
- **Fallback methods**: Alternative tools or approaches
- **Graceful degradation**: Partial functionality vs complete failure

### Deferred Recovery
- **Queue for later**: Save failed items for retry
- **Manual intervention**: Create clear instructions for user
- **Issue tracking**: Document for systematic fix

## Error Reporting

### To User (Immediate)
```
❌ Failed: [Specific operation]
Reason: [Clear explanation]
Impact: [What this means]
Next steps: [What user should do]
Issue: #[number] (if exists)
```

### To GitHub (Systematic)
Create issue when:
- Error occurs multiple times
- No existing issue covers it
- Requires code/infrastructure change

Issue template:
```markdown
## Error: [Brief description]
## Frequency: [How often]
## Impact: [Who/what affected]
## Root Cause: [If known]
## Workaround: [If any]
## Fix: [Proposed solution]
```

## Prevention Strategies

### Pre-flight Checks
- Verify prerequisites before starting
- Check API connectivity
- Validate input data
- Confirm permissions

### Defensive Coding
- Always check return values
- Use type checking where possible
- Validate data at boundaries
- Implement timeouts

### Testing Requirements
- Test error paths not just success
- Verify error messages are helpful
- Ensure partial failures handled
- Check recovery mechanisms work

## Integration with Workflows

Every workflow must:
1. Define expected failure modes
2. Specify recovery strategies
3. Include error handling examples
4. Reference this strategy

## Common Patterns

### API Integration Errors
```python
try:
    response = api_call()
    if not response.success:
        # Check known issues
        if "Task Name" in response.error:
            raise KnownError("See issue #14")
        else:
            # Novel error - needs investigation
            create_issue(response.error)
except NetworkError:
    # Retry with exponential backoff
    retry_with_backoff(api_call)
```

### Multi-step Workflows
```python
completed = []
failed = []

for item in items:
    try:
        process(item)
        completed.append(item)
    except Exception as e:
        failed.append((item, str(e)))

# ALWAYS report both
report_results(completed, failed)
```

## Critical Rules

1. **NEVER** mark task successful if any component failed
2. **NEVER** continue after critical errors
3. **NEVER** swallow errors silently
4. **ALWAYS** provide actionable error messages
5. **ALWAYS** check existing issues before creating new ones

## Quick Reference

| Error Type | Continue? | Create Issue? | User Action |
|------------|-----------|---------------|-------------|
| Network timeout | Retry 3x | If persists | Wait/retry |
| API error | No | Yes | Check issue |
| Missing file | No | If unexpected | Provide file |
| Bad data | No | If systematic | Fix data |
| Logic conflict | No | Yes | Clarify |
| Partial success | Maybe | If pattern | Review |
