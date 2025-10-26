# Fail-Fast Philosophy

**Core Principle:** Agents fail immediately on errors. Fix infrastructure, not add error handling.

## For Agents

- **STOP** immediately when anything goes wrong
- **REPORT** the exact error message
- **WAIT** for user instruction
- **NEVER** attempt to fix, debug, or work around errors

## For Agent-Trainer

- **FIX** root causes when agents fail
- **ENSURE** scripts are executable in repository
- **ADD** missing tools to system
- **DESIGN** workflows that cannot fail

## What We DON'T Do

### No Defensive Programming
❌ Check if script exists before running
❌ Verify script is executable
❌ Test if tool is available
❌ Handle errors gracefully

### No Error Recovery
❌ Retry on failure
❌ Try alternative approaches
❌ Debug problems
❌ Implement workarounds

## What We DO Instead

### Build Reliable Infrastructure
✅ All scripts executable in git
✅ All tools exist and work
✅ All paths resolve correctly
✅ All workflows execute perfectly

### Fix Root Causes
- Script not executable → Make it executable in repository
- Tool missing → Add the tool to system
- Path not found → Fix path resolution
- Workflow breaks → Redesign the workflow

## Why?

1. **Simplicity** - Agents have clear instructions
2. **Reliability** - Problems fixed once, permanently
3. **Maintainability** - No complex error handling
4. **Debuggability** - Failures point to infrastructure issues
5. **Token Efficiency** - Less defensive code

## Example

### ❌ Wrong (Defensive)
```bash
if [ -f "$SCRIPT" ] && [ -x "$SCRIPT" ]; then
    $SCRIPT
else
    chmod +x $SCRIPT; $SCRIPT
fi
```

### ✅ Correct (Fail-Fast)
```bash
$ACADEMIC_OPS_SCRIPTS/script.sh
```

If it fails, agent reports error and waits. Trainer fixes infrastructure.

**Remember:** Every error improves infrastructure, not error handling.
