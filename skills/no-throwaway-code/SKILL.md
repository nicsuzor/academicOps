---
name: no-throwaway-code
description: Intervention skill that triggers when agents attempt temporary/throwaway
  Python code (python -c, temp scripts, one-off investigations). Enforces Axiom 15
  - WRITE FOR THE LONG TERM. Nudges toward reusable solutions using dev agent or test-writing
  skill instead.
permalink: aops/skills/no-throwaway-code/skill
---

# No Throwaway Code

## Purpose

**Enforce Axiom #15: WRITE FOR THE LONG TERM for replication.**

This is a lightweight intervention skill that activates when an agent attempts to write temporary, throwaway Python code. Instead of allowing one-off scripts or inline Python commands, redirect to proper development practices that ensure replicability.

## Recognize Throwaway Code Patterns

Activate this skill when an agent is about to:

1. **Write inline Python with `python -c "..."`**
   - Investigating data: `python -c "import json; print(json.load(open('x.json')))"`
   - Checking values: `python -c "from foo import bar; print(bar.value)"`
   - Testing logic: `python -c "result = func(x); assert result == expected"`

2. **Create temporary scripts for investigation**
   - `/tmp/check_something.py`
   - `quick_test.py`
   - `debug_issue.py`
   - Any script intended for single use then deletion

3. **Write one-off code to "just check" or "investigate" something**
   - "Let me quickly write a script to see what's in this file"
   - "I'll create a temp script to verify this behavior"
   - "Let me check this with a quick Python command"

## Execute Intervention Workflow

When detecting throwaway code intent, **STOP immediately** and present this decision tree:

```
Agent wants to write temporary Python code to investigate/check/verify something
│
├─ IS THIS TESTING A BEHAVIOR?
│  └─ YES → Use test-writing skill
│     "This investigation validates behavior. Create a durable test instead."
│     → Invoke test-writing skill to create proper test in tests/
│
├─ IS THIS DEVELOPMENT/IMPLEMENTATION WORK?
│  └─ YES → Use dev agent
│     "This code should be reusable infrastructure. Create proper module instead."
│     → Invoke dev agent to create maintainable code
│
├─ IS THIS DATA EXPLORATION/ANALYSIS?
│  └─ YES → Use analyst skill or create reusable analysis
│     "This analysis should be reproducible. Use Jupyter notebook or Streamlit dashboard."
│     → Guide toward durable analytical artifacts
│
└─ IS THIS TRULY ONE-TIME ONLY?
   └─ Challenge this assumption
      "Even one-time issues can recur. Creating durable code costs barely more
      and ensures we can detect regression. What test or tool should we build?"
```

## Core Message

**REPLICABILITY is the key.**

Even if we only notice an issue once and fix it right away, we want to create durable infrastructure that:
- Ensures the issue never re-emerges down the line
- Documents what we learned
- Can be run again to verify behavior
- Lives in version control as institutional knowledge

## Intervention Template

When catching throwaway code, say:

```
🚫 STOP - Axiom #15: No single-use scripts or throwaway code

I see you're about to write temporary Python code to [investigate/check/verify] [X].

Instead of throwaway code, let's build something durable:

[Choose appropriate path:]

✅ If validating behavior:
   → Create a test in tests/ using the test-writing skill
   → This ensures [X] stays correct over time

✅ If building functionality:
   → Create proper module using dev agent
   → This makes [X] reusable infrastructure

✅ If analyzing data:
   → Create Jupyter notebook or Streamlit dashboard
   → This makes [X] analysis reproducible

Even if this issue occurs only once, durable code:
- Prevents regression (we catch it if it returns)
- Documents our understanding
- Costs barely more than throwaway code
- Builds institutional knowledge

What durable solution should we create instead?
```

## Examples

### Example 1: Inline Python to Check Data

**Agent intends:**
```bash
python -c "import json; data = json.load(open('config.json')); print(data.keys())"
```

**Intervention:**
```
🚫 STOP - Axiom #15: No single-use scripts

You're about to check JSON keys with inline Python.

Instead, let's create a durable test:
→ Use test-writing skill to create tests/test_config_schema.py
→ This test validates config structure permanently
→ Any future config changes will be verified automatically

What should the test verify about config.json?
```

### Example 2: Temp Script to Investigate Bug

**Agent intends:**
```python
# /tmp/debug_parser.py
from myapp.parser import parse_input

result = parse_input("edge case")
print(f"Result: {result}")
print(f"Type: {type(result)}")
```

**Intervention:**
```
🚫 STOP - Axiom #15: No single-use scripts

You're about to write a temp script to investigate parser behavior.

Instead, let's create a durable test:
→ Use test-writing skill to create tests/test_parser_edge_cases.py
→ This test documents the edge case behavior
→ Future parser changes won't break this case silently

What edge case behavior should we test?
```

### Example 3: Quick Check Before Implementation

**Agent intends:**
```bash
python -c "from datetime import datetime; print(datetime.now().isoformat())"
```

**Intervention:**
```
🚫 STOP - Axiom #15: No single-use scripts

You're about to check datetime formatting with inline Python.

Instead, let's create a durable test:
→ Use test-writing skill to create tests/test_datetime_formatting.py
→ This test documents expected format
→ We ensure format stays correct across Python versions

OR if this is for implementation:
→ Use dev agent to create utility function
→ datetime_utils.py with get_iso_timestamp()
→ Reusable across the codebase

Which approach fits the need?
```

### Example 4: "Just Checking" Something

**Agent intends:**
```bash
python -c "import sys; print(sys.version)"
```

**Acceptable exception:**
This is checking environment/system state, not testing behavior or building functionality.

**But if recurring:**
```
If we need to verify Python version frequently:
→ Create tests/test_environment.py
→ Documents required Python version
→ CI/CD can verify environment setup
```

## When NOT to Intervene

**Acceptable temporary Python (rare):**

1. **Environment/system queries** that are truly one-time:
   - `python -c "import sys; print(sys.version)"` (checking installed version)
   - `python -c "import pkg; print(pkg.__version__)"` (checking installed package)

2. **Standard tool usage** (not throwaway code):
   - `python -m pytest tests/` (running tests)
   - `python -m http.server` (dev server)
   - `uv run python script.py` (running existing script)

**Key distinction:**
- ❌ Creating new throwaway code → INTERVENE
- ✅ Using existing tools/scripts → ALLOW
- ✅ Checking system state once → ALLOW (but if recurring, suggest test)

## Integration with Other Skills

This skill is a **pre-check** before development work:

```
Throwaway code attempt
    ↓
no-throwaway-code (intervention)
    ↓
├─ Behavior validation → test-writing skill
├─ Implementation work → dev agent
└─ Data analysis → analyst skill or Jupyter/Streamlit
```

## Success Criteria

This skill succeeds when:

1. **Agent catches themselves** before writing throwaway code
2. **Durable artifact created** instead (test, module, notebook)
3. **Replicability achieved** - future developers can run/verify the work
4. **Institutional knowledge captured** - what we learned is codified

## Tone

Keep interventions:
- **Brief** - This is a lightweight nudge, not a lecture
- **Constructive** - Offer the better path immediately
- **Practical** - "Let's create X instead" not "You shouldn't do Y"
- **Enforcement-focused** - This is Axiom #15, non-negotiable

## Summary

**Axiom #15: WRITE FOR THE LONG TERM**

No single-use scripts. No throwaway code. No "just checking" with temporary Python.

Every investigation, check, or verification is an opportunity to build durable infrastructure that ensures replicability and prevents regression.

When in doubt: **If it's worth running once, it's worth testing forever.**
