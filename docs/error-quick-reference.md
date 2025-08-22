# Error Handling Quick Reference

This system is a work-in-progress! We love finding errors and limitations: they are a great opportunity to think carefully about design and future development.

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

## Remember
- **NEVER** claim success if anything failed
- **ALWAYS** be specific about what failed
- **ALWAYS** provide next steps for user
