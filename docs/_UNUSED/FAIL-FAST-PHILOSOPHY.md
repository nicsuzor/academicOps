# FAIL FAST PHILOSOPHY

## Core Principle

Agents should fail immediately on ANY error. We fix infrastructure problems, not add error handling.

## What This Means

### For Agents

- **STOP** immediately when anything goes wrong
- **REPORT** the exact error message
- **WAIT** for user instruction
- **NEVER** attempt to fix, debug, or work around errors

### For Agent-Trainer

- **FIX** the root cause when agents fail
- **ENSURE** scripts are executable in the repository
- **ADD** missing tools to the system
- **DESIGN** workflows that cannot fail

## What We DON'T Do

### No Defensive Programming

❌ Check if script exists before running ❌ Verify script is executable ❌ Test if tool is available ❌ Handle errors gracefully

### No Error Recovery

❌ Retry on failure ❌ Try alternative approaches ❌ Debug problems ❌ Implement workarounds

## What We DO Instead

### Build Reliable Infrastructure

✅ All scripts are executable in git ✅ All tools exist and work ✅ All paths resolve correctly ✅ All workflows execute perfectly

### Fix Root Causes

When an agent fails because:

- Script not executable → Make it executable in repository
- Tool missing → Add the tool to the system
- Path not found → Fix path resolution
- Workflow breaks → Redesign the workflow

## Why This Philosophy?

1. **Simplicity**: Agents have simple, clear instructions
2. **Reliability**: Problems are fixed once, permanently
3. **Maintainability**: No complex error handling to maintain
4. **Debuggability**: Failures point directly to infrastructure issues
5. **Token Efficiency**: Less defensive code means fewer tokens

## Implementation Checklist

### Remove from Agent Instructions

- [ ] Permission checking code
- [ ] Tool verification steps
- [ ] Error recovery logic
- [ ] Debugging instructions
- [ ] Workaround documentation

### Add to Infrastructure

- [ ] Script execute permissions in git
- [ ] All referenced tools
- [ ] Path resolution system
- [ ] Workflow validation tests
- [ ] Infrastructure documentation

## Example Transformation

### Before (Wrong)

```bash
# Check if script exists and is executable
if [ -f "$SCRIPT_PATH" ]; then
    if [ -x "$SCRIPT_PATH" ]; then
        $SCRIPT_PATH
    else
        chmod +x $SCRIPT_PATH
        $SCRIPT_PATH
    fi
else
    echo "Script not found, trying alternative..."
fi
```

### After (Correct)

```bash
$ACADEMIC_OPS_SCRIPTS/script_name.sh
```

If it fails, the agent reports: "Step 3 failed: Permission denied" and waits. The agent-trainer then fixes the script permissions in the repository.

## Remember

Every error is an opportunity to improve infrastructure, not add error handling.
