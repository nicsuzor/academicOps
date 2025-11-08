# Fail-Fast: Detailed Examples

## Axiom #5: Fail-Fast (Code)

No defaults, no fallbacks, no workarounds, **no `.get(key, default)`**

### What It Means

Fail immediately when configuration is missing or incorrect. Silent misconfiguration corrupts research data.

### Prohibited Patterns

❌ **PROHIBITED**: `config.get("param", default_value)` - Silent misconfiguration ❌ **PROHIBITED**: `try/except` returning fallback values - Hides errors ❌ **PROHIBITED**: Defensive programming (`if x is None: use_fallback`) - Masks problems

### Required Patterns

✅ **REQUIRED**: `config["param"]` - Raises KeyError immediately if missing ✅ **REQUIRED**: Pydantic Field() with no default - Raises ValidationError ✅ **REQUIRED**: Explicit check: `if key not in dict: raise ValueError(...)`

### What It Does NOT Mean

Fail-fast does NOT mean avoid using industry-standard tools as dependencies.

✅ **CORRECT**: Require `pre-commit`, `uv`, `pytest` and fail if missing ✅ **CORRECT**: Use best standard tool for the job (see Axiom #9)

## Axiom #6: Fail-Fast (Agents)

When YOUR instructions or tools fail, STOP immediately.

### Prohibited Behaviors

❌ **PROHIBITED**: Attempting recovery when slash commands fail ❌ **PROHIBITED**: Working around broken paths or missing environment variables ❌ **PROHIBITED**: "Figuring it out" when infrastructure is broken ❌ **PROHIBITED**: Continuing with workarounds instead of reporting errors

### Required Behaviors

✅ **REQUIRED**: Report error immediately and stop ✅ **REQUIRED**: Demand infrastructure be fixed, don't bypass it

### Rationale

Just like code shouldn't silently fail with defaults, agents shouldn't silently work around broken infrastructure. Fail-fast exposes problems so they get fixed, not hidden.

## Tool Failure Protocol

When a tool/script fails with an error:

### Steps

1. **Read the error message** - What exactly is it saying?
2. **ONE retry maximum** - If you think you misunderstood the input format, try ONCE more with corrected input
3. **STOP after 2nd failure** - Report the problem, don't continue exploring

### After 2nd Failure

STOP and report:

- What you tried (both attempts)
- The exact error message
- Your hypothesis about the bug (if clear)
- Ask user how to proceed

### NEVER

- Try 3+ variations to "figure it out"
- Explore filesystem/code to understand tool internals
- Invent workarounds for broken tools
- Keep trying different formats/approaches

### Example - CORRECT Fail-Fast Response

```
Attempt 1: task_process.py modify 20250929-004918-nicwin-7ce2c06b --archive
Error: "Invalid task ID format: expected YYYYMMDD-XXXXXXXX"

Attempt 2: task_process.py modify 20250929-004918 --archive
Error: "Invalid task ID format: expected YYYYMMDD-XXXXXXXX"

The script expects format YYYYMMDD-XXXXXXXX but task_add.py creates
IDs as YYYYMMDD-HHMMSS-hostname-uuid. This appears to be a regex
validation bug in task_process.py line 87.

Should I investigate the script bug or handle this differently?
```

**See also**: Behavioral Rule #12 (NO WORKAROUNDS), Axiom #6 (Fail-Fast for Agents)
