# Error Handling Quick Reference

## FAIL FAST PHILOSOPHY

When you encounter ANY error:

1. **STOP** - Do not continue
2. **REPORT** - State exact error message
3. **WAIT** - Get user instruction

**NEVER**:

- Try to fix the error yourself
- Work around the problem
- Debug or investigate
- Continue with partial success

## When You Hit an Error

```
1. STOP - Halt all execution
2. REPORT - "Step [N] failed: [exact error]"
3. WAIT - "Waiting for your instruction."
```

## Error Reporting Format

```
Step 3 failed: [exact error message]
Waiting for your instruction on how to proceed.
```

## Commit Discipline

When stopping due to error:

1. Check `git status` for uncommitted changes
2. If changes exist, commit them before reporting error
3. Then report error and wait

## Remember

- **NEVER** claim success if anything failed
- **ALWAYS** be specific about what failed
- **ALWAYS** provide next steps for user
- **ALWAYS** commit changes before stopping on errors
