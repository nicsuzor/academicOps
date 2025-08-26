# Error Handling Quick Reference

This system is a work-in-progress! We love finding errors and limitations: they are a great opportunity to think carefully about design and future development.

## Pre-execution Verification Checklist

### Before Running Scripts
```
1. CHECK - Does the script exist?
   ls -la /path/to/script.sh
   
2. VERIFY - Is it executable?
   Look for 'x' in permissions (-rwxr-xr-x)
   
3. FIX - Make executable if needed
   chmod +x /path/to/script.sh
   
4. TRACK - Remember verified scripts in session
```

### Before Assigning Projects
```
1. LIST - Check available projects
   ls /home/nic/src/writing/data/projects/
   
2. READ - Understand project purpose
   cat /home/nic/src/writing/data/projects/[project].md
   
3. VERIFY - Does project match task type?
   - Academic conferences → academic-profile projects
   - Industry/government → impact projects
   
4. ASK - If uncertain, show options to user
```

### Before Classifying Tasks
```
1. CONTEXT - Read relevant goal files
   /home/nic/src/writing/data/goals/*.md
   
2. UNDERSTAND - Know the taxonomy
   - What are the project categories?
   - What goes where?
   
3. VERIFY - Project exists and is appropriate
```

## When You Hit an Error

```
1. STOP - Don't continue with bad state
2. CHECK - Is this a known issue? (search GitHub)  
3. DECIDE - Can I recover? Should I retry?
4. REPORT - Tell user what failed and why
5. TRACK - Create issue if new/recurring
```

## Decision Tree

```
Error Occurred
    ↓
Is it in GitHub issues? 
    YES → Reference issue # and apply workaround
    NO ↓
    
Can I retry?
    YES → Retry 3x with backoff
    NO ↓
    
Is there alternative approach?
    YES → Try alternative and note in report
    NO ↓
    
STOP and report:
- What failed
- Why it failed  
- Impact on task
- Create GitHub issue
```

## Tips 

- Use heredocs (`cat << 'EOF'`) when calling **CLI TOOLS WITH FORMATTED OR MULTI-LINE INPUT** to avoid escaping issues.
- **COMMIT BEFORE RECOVERY** - If you've made changes and hit an error, commit them first to prevent data loss

## Critical Recovery Actions

Before stopping due to an error:
1. Check `git status` - are there uncommitted changes?
2. If yes, commit them with a descriptive message including the error
3. Check parent repository status too
4. Only then report the error and wait for guidance

## Remember
- **NEVER** claim success if anything failed
- **ALWAYS** be specific about what failed
- **ALWAYS** provide next steps for user
- **ALWAYS** commit changes before stopping on errors
