# CRITICAL WORKFLOW MODE INSTRUCTIONS FOR GEMINI

## ABSOLUTE RULES - NO EXCEPTIONS

When you encounter ANY error during workflow execution:

1. **STOP IMMEDIATELY** - Do not proceed to the next step
2. **DO NOT FIX ERRORS** - Even if you know exactly what's wrong
3. **DO NOT MODIFY CODE** - No edits, replacements, or fixes
4. **REPORT EXACTLY**: "Step [N] failed: [exact error message]"
5. **WAIT FOR USER** - Only continue when explicitly told

## WHAT CONSTITUTES AN ERROR

- Any non-zero exit code
- Any PowerShell error message
- Any Python exception
- Any file not found
- Any operation that doesn't complete successfully
- Any unexpected output format

## FORBIDDEN ACTIONS WHEN ERRORS OCCUR

❌ **NEVER** say "I'll fix this"
❌ **NEVER** say "I'll correct this"  
❌ **NEVER** say "Let me investigate and fix"
❌ **NEVER** modify scripts or code
❌ **NEVER** create workarounds
❌ **NEVER** skip to the next step
❌ **NEVER** improvise solutions

## REQUIRED RESPONSE TO ERRORS

✅ Say: "Step [N] failed: [error]"
✅ Say: "Waiting for your instruction on how to proceed."
✅ Stop all execution
✅ Wait for user response

## EXAMPLE OF WRONG BEHAVIOR (DO NOT DO THIS)

```
Error: PowerShell script has inverted exit codes
Gemini: "I'll correct this by modifying the script..." [WRONG!]
```

## EXAMPLE OF CORRECT BEHAVIOR

```
Error: PowerShell script has inverted exit codes
Gemini: "Step 4 failed: PowerShell script returned unexpected exit code. Waiting for your instruction on how to proceed."
```

## VERIFICATION CHECKLIST

Before taking ANY action after an error:
- [ ] Did I stop immediately?
- [ ] Did I report the exact error?
- [ ] Am I waiting for user instruction?
- [ ] Did I avoid trying to fix anything?

Remember: The user explicitly said "we told him not to fix errors" - this means DO NOT FIX ERRORS under any circumstances.