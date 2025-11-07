# End-of-Session Agent: Add Mandatory Skill-First Pattern

## Metadata

- Date: 2025-11-03
- Issue: #184
- Commit: [pending]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Adding the mandatory skill-first invocation pattern to end-of-session.md will prevent the agent from attempting to read reference files and evaluate accomplishment criteria manually. Instead, it will immediately delegate to scribe skill Mode 4 as designed.

## Changes Made

1. Added mandatory skill-first pattern at top of end-of-session.md (after frontmatter, before "Purpose" section):
   - **MANDATORY FIRST STEP** instruction to invoke scribe immediately
   - **DO NOT** list preventing improvisation (reading files, manual evaluation)
   - Brief description of what scribe Mode 4 provides

2. Removed confusing reference (line 75):
   - Before: "See scribe skill SKILL.md lines 251-349 for full criteria"
   - After: "Scribe skill Mode 4 applies these criteria automatically"
   - Rationale: Reference to line numbers may have suggested agent should READ the skill

## Success Criteria

When end-of-session agent is invoked:

1. **Immediate delegation**: Agent invokes `Skill(command='scribe', mode='end-of-session', ...)` as first action after git operations
2. **No file reads**: Agent does not attempt Read operations on reference files
3. **No searches**: Agent does not search for documentation (VALID, CODE, COMMIT patterns)
4. **Successful capture**: Accomplishment written to accomplishments.md via scribe delegation (for qualified work)
5. **Silent completion**: Agent completes without user-visible output

## Test Plan

**Manual test**:

1. Complete substantial work (e.g., implement feature, fix bug)
2. Trigger end-of-session agent via Stop hook
3. Review execution log for:
   - Skill(command='scribe') invocation present
   - No Read(file_path="/home/nic/src/writing/...") errors
   - No Search(pattern="**/_VALID_.md") attempts
   - Accomplishment entry in accomplishments.md (if qualified)

**Expected execution sequence**:

```
1. Bash(git status --short)
2. Skill(command='git-commit')  # If changes present
3. Skill(command='scribe', mode='end-of-session', work_description='...', state='completed')
4. Complete silently
```

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial]

## Next Steps

- If SUCCESS: Close as working, monitor for regressions
- If FAILURE: Escalate to hook-based enforcement (PreToolUse hook blocking Read in end-of-session context)
- If PARTIAL: Iterate on instruction clarity or add additional constraints
