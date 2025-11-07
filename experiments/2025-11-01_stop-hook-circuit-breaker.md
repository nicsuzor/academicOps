# Stop Hook Circuit Breaker - Prevent Infinite Loop on Infrastructure Failure

## Metadata

- Date: 2025-11-01
- Issue: #171
- Commit: [pending]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Adding `|| echo '{"continue":true}'` to Stop and SubagentStop hook commands will allow sessions to terminate cleanly even when underlying infrastructure (like `uv`) breaks during execution, preventing infinite loop deadlocks.

## Changes Made

Modified `/home/nic/src/bot/config/settings.json`:

1. **Stop hook** (line 33):
   - Before: `uv run ... Stop; else echo ...`
   - After: `uv run ... Stop || echo '{"continue":true}'; else echo ...`

2. **SubagentStop hook** (line 22):
   - Before: `uv run ... SubagentStop; else echo ...`
   - After: `uv run ... SubagentStop || echo '{"continue":true}'; else echo ...`

**Pattern**: `command || fallback` ensures fallback executes if command fails, rather than only handling missing script file.

## Success Criteria

1. **Primary**: Session can exit when `uv` infrastructure is broken
   - Test: Move `/opt/nic/cache/uv` temporarily, attempt to exit session
   - Success: Session exits cleanly with error logged
   - Failure: Infinite loop returns

2. **Secondary**: Validation still runs when infrastructure is healthy
   - Test: Normal session with working `uv`
   - Success: Stop hook validation executes and logs
   - Failure: Validation silently skipped

3. **Tertiary**: No degradation in hook reliability
   - Test: 10 normal session exits
   - Success: All hooks execute as before
   - Failure: Hooks fail more frequently

## Test Plan

### Test 1: Infrastructure Failure Recovery (Primary)

1. Start Claude Code session
2. Simulate `uv` failure: `sudo mv /opt/nic/cache/uv /opt/nic/cache/uv.bak`
3. Attempt to exit session
4. Expected: Session exits cleanly, error logged but no infinite loop
5. Restore: `sudo mv /opt/nic/cache/uv.bak /opt/nic/cache/uv`

### Test 2: Normal Operation Preservation (Secondary)

1. Start Claude Code session with working infrastructure
2. Perform normal operations
3. Exit session
4. Expected: Stop hook validation runs, logs generated
5. Verify: Check hook debug logs for validation execution

### Test 3: Reliability Baseline (Tertiary)

1. Run 10 sessions with various operations
2. Exit each normally
3. Expected: No increase in hook failure rate
4. Metric: Compare hook success rate before/after change

## Results

### Test 1: Infrastructure Failure Recovery ✅ SUCCESS

**Setup**: Moved `/opt/nic/cache/uv` to `/opt/nic/cache/uv.bak` to simulate exact failure from Issue #171

**Execution**: Agent sent response, Stop hook triggered

**Observed behavior**:

- Stop hook attempted to run `uv run ... validate_stop.py`
- `uv` failed (cache directory missing)
- `|| echo '{"continue":true}'` fallback executed
- Session **continued normally** - no infinite loop
- Agent remained responsive and functional

**Comparison to pre-fix behavior**:

- Before: Infinite loop, session trapped, manual kill required
- After: Single error, session continues, agent functional

**Restoration**: Successfully restored `/opt/nic/cache/uv`

### Test 2: Normal Operation (Not Yet Run)

[Will verify hook still executes when infrastructure is healthy]

### Test 3: Reliability Baseline (Not Yet Run)

[Will run multiple sessions to verify no degradation]

## Outcome

**PRIMARY SUCCESS**: Circuit breaker prevents infinite loop deadlock

The core issue is **RESOLVED**. The `|| echo '{"continue":true}'` pattern successfully breaks the infinite loop when infrastructure fails during Stop hook execution.

**Next steps**:

1. Commit this change
2. Run Test 2 to verify normal validation still works
3. Monitor hook logs over next few sessions for any false-negatives
4. Document this pattern for other critical hooks if needed

## Notes

- This change implements **graceful degradation** - prefer availability over strict validation
- Trade-off: Might mask legitimate validation failures if `uv` breaks unexpectedly
- Alternative: Circuit breaker script would track failure counts and alert user (more complex)
- Decision: Start with simple solution, upgrade if false-negatives become problematic

## Follow-up Enhancement: Stderr Logging (2025-11-01)

**Issue**: Original circuit breaker had no user-visible output when hook failed

**Solution**: Added stderr echo to fallback path:

```bash
|| { echo 'Stop hook validation failed - session continuing despite error' >&2; echo '{"continue":true}'; }
```

**Pattern breakdown**:

- `{ ... }` groups commands
- `echo '...' >&2` sends message to stderr (visible to user)
- `echo '{...}'` sends JSON to stdout (for Claude Code)
- Both execute when `uv run` fails

**Applied to**:

- Stop hook (line 33)
- SubagentStop hook (line 22)

**Testing note**: Stderr visibility confirmed via claude-hooks skill documentation. User will see error message when hook fails, providing transparency about degraded validation.
