# Impact Analysis & Shared Infrastructure

## 🚨 CRITICAL: Tunnel Vision Prevention

**A DOCUMENTED PATTERN OF BREAKING SHARED INFRASTRUCTURE WHEN FOCUSED ON SPECIFIC PROBLEMS MUST BE AVOIDED.**

## The Shared Infrastructure Trap

### ❌ Common Failure Pattern:
1. **Focus on a specific failure**: "These tests are failing."
2. **Tunnel vision on an immediate fix**: "I need to change X to make them pass."
3. **Modify shared infrastructure**: Edit a file that affects ALL tests or modules (e.g., `conftest.py`, a base class, a core utility).
4. **Break other functionality**: Other tests or modules that relied on the original behavior now fail.

### ✅ Correct Approach:
1. **Identify shared vs. specific scope**: "This file serves multiple modules."
2. **Analyze true requirements**: "Do these tests *really* need this global change?"
3. **Create targeted solutions**: "I will create a specific fixture/helper for this test module instead of changing the global one."
4. **Preserve existing functionality**: "I will ensure other tests continue to work by not modifying their shared setup."

## Mandatory Impact Analysis Protocol

### 🛑 BEFORE Modifying ANY Shared File:

**STOP and ask these questions:**

1. **Scope Analysis**: What else depends on this file?
   - `conftest.py` files: Affect ALL tests in that directory and subdirectories.
   - Base classes: Used by multiple implementations.
   - Shared utilities: Imported by multiple modules.
   - Configuration files: Loaded by multiple components.

2. **Impact Assessment**: What would break if I make this change?
   - Search for imports: `grep -r "from path.to.this.module import"`
   - Search for usage: `grep -r "filename"`
   - Check test dependencies: Files that import from this module.

3. **Alternative Solutions**: Can I solve this without touching shared infrastructure?
   - Override in specific tests only.
   - Make the shared code more resilient.
   - Use conditional logic based on environment.
   - Create test-specific fixtures.

### 🚨 High-Risk Shared Files:

**These files require EXTRA caution and impact analysis. Examples include:**

- `tests/conftest.py`
- `tests/*/conftest.py`
- Core utility modules (e.g., in `utils/` or `_core/` directories)
- Shared API definitions.
- Any `__init__.py` file.
- Base configuration files.

## No workarounds!

If you hit a problem related to some other part of the project, STOP.
- DO NOT build a workaround that addresses only your current objective.
- STEP BACK and IMMEDIATELY activate your error handling protocol.
- Do not proceed. Raise an issue and seek help.
- We expect EVERYTHING to work. No workarounds, no shortcuts.

## Specific Test Infrastructure Guidelines

### conftest.py Files - High Impact Zone

**NEVER modify `conftest.py` without understanding ALL affected tests:**

1. **Before editing**: Run `pytest --collect-only` to see all tests that would be affected.
2. **Check dependencies**: Search for fixtures used across multiple test files.
3. **Test your changes**: Run the FULL test suite, not just the tests you're fixing.
4. **Consider alternatives**: Can you create test-specific fixtures instead?

## Red Flag Detection System

### 🚨 STOP Immediately When You Think:

- "I'll just remove this from conftest.py to make my tests pass."
- "These other tests probably don't need this anyway."
- "I can fix the other failures later."
- "This shared file is causing problems, I'll simplify it."
- "Let me modify this base class to handle my use case."

### ✅ CORRECT Responses:

- "How can I solve this WITHOUT modifying shared infrastructure?"
- "What would break if I change this shared file?"
- "Can I create a test-specific solution instead?"
- "How can I make this shared code more resilient?"
- "Let me search for all usages of this file first."

## Enforcement Checklist

**Before modifying ANY file, ask:**

1. **Is this file imported by multiple modules?** 
   - If YES: Requires impact analysis.

2. **Does this file contain fixtures used by multiple tests?**
   - If YES: Changes affect ALL dependent tests.

3. **Is this a base class or core utility?**
   - If YES: Changes ripple through the entire system.

4. **Does the filename suggest shared infrastructure?** (e.g., `conftest.py`, `base_*.py`, `__init__.py`)
   - If YES: High-risk modification requiring extra care.

5. **Can I solve my problem with a targeted solution instead?**
   - If YES: Always prefer targeted over shared modifications.

**If ANY red flags appear: STOP and develop a targeted solution instead.**

## Recovery Protocol

**When you catch yourself about to break shared infrastructure:**

1. **STOP immediately** - Don't make the modification.
2. **List all dependencies** - What uses this file?
3. **Search for alternatives** - Can you solve this differently?
4. **Create a targeted solution** - Test-specific or conditional logic.
5. **Validate approach** - Run affected tests to ensure no regressions.
6. **Document the decision** - Explain why this approach is safer.

Remember: **Fixing one specific problem by breaking shared infrastructure is never the right solution.**
