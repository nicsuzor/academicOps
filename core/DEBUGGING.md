# Debugging Methodology

Generic debugging principles and systematic troubleshooting. Project-specific debug tools in project-tier DEBUGGING.md files.

## Systematic Troubleshooting

**The Scientific Method for Debugging**:

1. **Reproduce**: Can you reliably trigger the problem?
2. **Isolate**: What's the minimum code path that fails?
3. **Hypothesize**: What do you think is causing it?
4. **Test**: How can you verify your hypothesis?
5. **Fix**: Address root cause, not symptoms
6. **Verify**: Confirm fix works AND doesn't break other things

**Evidence-Based Debugging**:
- ✅ Check logs/traces for actual behavior
- ✅ Use profilers/debuggers to observe state
- ✅ Write failing tests that reproduce issue
- ✅ Verify assumptions with data
- ❌ Speculate about what "should" happen
- ❌ Guess without checking evidence
- ❌ Add print statements and hope

## Profiling

**Import Time Profiling** (Python):
```bash
# Identify slow imports
python -X importtime -c "import mymodule" 2> /tmp/import_profile.txt

# Analyze output
cat /tmp/import_profile.txt | grep "import time" | sort -k2 -rn | head -20
```

**Runtime Profiling** (Python):
```python
import cProfile
import pstats

# Profile function
cProfile.run('my_function()', '/tmp/profile.stats')

# Analyze
stats = pstats.Stats('/tmp/profile.stats')
stats.sort_stats('cumulative').print_stats(20)
```

**Memory Profiling** (Python):
```bash
# Install memory_profiler
pip install memory-profiler

# Profile with decorator
from memory_profiler import profile

@profile
def my_function():
    # Function code
    pass
```

## Logging

**Structured Logging Best Practices**:

```python
import structlog

logger = structlog.get_logger()

# ✅ Good - structured data
logger.info("user_authenticated",
            user_id=user.id,
            method="oauth",
            duration_ms=elapsed)

# ❌ Bad - unstructured string
logger.info(f"User {user.id} authenticated via oauth in {elapsed}ms")
```

**Log Levels**:
- `ERROR`: Something failed, needs immediate attention
- `WARNING`: Unexpected but handled, may need investigation
- `INFO`: Normal operation, significant events
- `DEBUG`: Detailed diagnostic information

**Filtering Logs**:
```bash
# Show only errors and warnings
grep -E "(ERROR|WARNING)" /path/to/log.jsonl

# Show logs for specific component
grep "component_name" /path/to/log.jsonl | jq .

# Show recent entries
tail -f /path/to/log.jsonl
```

## Common Anti-Patterns

**Speculation Without Evidence**:
- ❌ "The hook should have caught it"
- ❌ "This will probably work"
- ❌ "I think the issue is..."
- ✅ "The logs show..." (check evidence)
- ✅ "Let me test this hypothesis..." (verify)
- ✅ "Profiling reveals..." (measure)

**Adding Workarounds Instead of Fixing Root Cause**:
- ❌ Adding try/except to silence errors
- ❌ Adding defaults to mask configuration problems
- ❌ Adding timeouts to hide race conditions
- ✅ Fix the configuration issue
- ✅ Fix the race condition properly
- ✅ Make errors explicit and actionable

**Print-Driven Debugging**:
- ❌ Adding print statements throughout code
- ❌ Leaving debug prints in committed code
- ❌ Using print instead of proper logging
- ✅ Use proper logging with levels
- ✅ Use debugger breakpoints
- ✅ Write tests that expose the issue

## Debugging Workflow

**For failing tests**:
1. Read test output carefully - what exactly failed?
2. Reproduce failure reliably
3. Add more specific assertions if needed
4. Use debugger to step through failing code
5. Fix root cause
6. Verify all tests pass
7. Commit fix

**For production issues**:
1. Check structured logs for errors/warnings
2. Identify error message and stack trace
3. Reproduce in development environment
4. Write failing test that reproduces issue
5. Fix code to make test pass
6. Verify fix in development
7. Deploy fix

**For performance issues**:
1. Profile to identify bottleneck (don't guess)
2. Measure baseline performance
3. Make targeted optimization
4. Measure again - verify improvement
5. Ensure tests still pass
6. Document performance gain

See project-tier DEBUGGING.md for project-specific debugging tools and workflows.
