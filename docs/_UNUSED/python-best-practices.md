# Python Development Best Practices

**Quick reference for Python development. See `bot/agents/developer.md` for full workflow.**

## Core Philosophy

**

## Type Hints

Always use type hints:

```python
from typing import Optional, List


def process_users(users: List[dict[str, str]], active_only: bool = False) -> List[str]:
    """Process user data and return names."""
    return [u["name"] for u in users if not active_only or u.get("active")]
```

5. BEWARE: 🛑 SCOPE ESCALATION CHECKPOINT

**BEFORE starting any investigation that goes beyond the immediate problem:**

1. **Recognize scope creep**: Am I about to read multiple files/search extensively beyond what the user explicitly asked for?
2. **Check with user**: "This is expanding beyond [original request]. Should I [describe expanded scope] or focus only on [immediate issue]?"
3. **Follow GitHub workflow**: If it's becoming substantial work, create an issue first (as already required)

**Trigger for escalation check**:

- About to read more than 2-3 files not directly mentioned by user
- Investigation expanding to multiple components/systems
- What started as "help with X" becoming "understand how Y architecture works"
- **Workspace dependency conflicts detected** (different projects using incompatible versions)
- Changes that could impact other projects in the workspace

### Interactive Debugging Workflow

When debugging an issue through active conversation with the user (user provides reproduction, you investigate and fix):

**🛑 CRITICAL**: STOP when user interrupts. User interruption takes precedence over completing any workflow step.

1. **FIX**: Make the necessary code changes to address the root cause
2. **BUILD**: Rebuild affected artifacts (Docker images, packages, compiled assets, etc.)
3. **TEST (ONLY IF USER REQUESTS)**: Verify the fix works using proper test infrastructure

   **🛑 ALWAYS USE TESTS FOR VERIFICATION**:
   - Verification MUST use pytest tests, not ad-hoc commands
   - ✅ `pytest tests/test_specific_functionality.py`
   - ❌ Complex bash pipelines with jq/grep/sed
   - ❌ One-off verification scripts
   - ❌ Manual Docker commands to recreate test scenarios

   **When No Tests Exist**:
   1. **STOP** and report: "Changes complete. No tests exist for this functionality."
   2. **ASK**: "Would you like me to write pytest tests, or would you prefer to verify manually?"
   3. **WAIT** for user decision
   4. **DO NOT** create ad hoc test scripts or run verification commands

   **When Tests Exist**:
   1. Check if tests already exist for this functionality
   2. Run them: `pytest tests/test_specific_functionality.py`
   3. If tests fail: Debug the failure, don't work around it

   **If you find yourself writing complex verification commands**: You're doing it wrong. STOP and ask the user instead.

4. **COMMIT**: Commit ALL changes, including any modifications to dependency repositories
5. **VERIFY**: Confirm end-to-end functionality works as expected

**PROHIBITED**: Stopping after step 1 (making code changes) without building, testing, committing, and verifying.

**Example failure pattern**: Fixing a Docker stdio issue by editing source code, but stopping without rebuilding the Docker image or testing that it now works.

## 🛑 CRITICAL FAILURE MODES TO AVOID 🛑

### 1. RUSH-TO-CODE

- **Symptom**: Immediately writing implementation code.
- **Prevention**: Follow the **EXPLORE (MANDATORY)** step above. Search before you code. Justify every new line of code.

### 2. STANDALONE VALIDATION

- **Symptom**: Creating `test.py`, `debug_*.py`, `verify_*.py`, or any validation scripts outside `tests/`, or using `python -c "..."` to "check if something works".
- **Prevention**: **ALL** testing, validation, debugging verification, and "checking" MUST happen within the `pytest` framework in the `tests/` directory. If you feel the urge to write a one-off test, debug script, or verification file, create a proper `pytest` test case instead. Use existing test fixtures (like `real_bm`, `real_logger`) for debugging.
- **See**: Pre-Action Checkpoint below for mandatory halt check before creating any .py file.

### 3. SHARED INFRASTRUCTURE TUNNEL VISION

- **Symptom**: Modifying shared files (e.g., `conftest.py`, base classes, core utilities) to fix a specific, narrow problem, thereby breaking other parts of the system.
- **Prevention**: Before editing a shared file, perform an **Impact Analysis**. Search the codebase to find all dependencies of that file. Prefer targeted, local solutions over modifying shared code.

### 4. DEFENSIVE CODING AROUND BROKEN INFRASTRUCTURE

- **Symptom**: Writing `try...except` blocks or `if x is not None:` checks around core services like logging or tracing.
- **Prevention**: The project's philosophy is **FAIL FAST**. If a core service is broken, the system should fail loudly. Do not write code to hide these failures. Your job is to fix the root cause or report it, not to build workarounds.

### 5. PREMATURE VICTORY DECLARATION

- **Symptom**: Declaring success when tests are failing, making excuses like "environmental issues" or "test setup problems" without evidence.
- **Prevention**: A failing test means broken code, period. You must debug thoroughly until tests pass or you have clear evidence of infrastructure failure. If genuinely blocked by infrastructure, provide reproduction steps and request help.

### 6. LOCALIZED FIX WITHOUT IMPACT ANALYSIS

- **Symptom**: Changing code to match error messages without verifying codebase-wide impact, leading to cascading breakage.
- **Prevention**:
  - Run INTERFACE MISMATCH CHECKPOINT for all naming conflicts
  - Use grep with count to determine majority convention
  - Fix at root (protocol/interface definition) not call sites
  - Trust codebase evidence over error messages
- **Example**: Changing `processor_stage` to `pipeline_stage` would break 38 references. The correct fix was updating the protocol definition to use `processor_stage`.
- **See**: Issue #88

## 🛑 CRITICAL: Configuration File Modifications

**Before modifying ANY configuration file** (YAML, JSON, TOML, env files, etc.), you MUST:

1. **Read Working Examples FIRST**: Find and examine 2-3 working examples of the same configuration type in the codebase
2. **Verify Pattern Match**: Confirm your proposed change follows the established pattern from those examples
3. **Check System Reminders**: Review any system reminders about recent user changes - they are intentional
4. **Understand Before Changing**: If uncertain how the config works, ASK - never guess based on superficial code reading
5. **Cite Your Sources**: When proposing changes, reference specific examples that support your approach

**Example Process**:

```
Task: Modify flows/myflow.yaml host configuration

Steps taken:
1. Read flows/osb.yaml and flows/transllm.yaml
2. Confirmed both use top-level `host:` field (not in observers: or agents:)
3. Verified system reminder shows user intentionally structured config this way
4. My change follows pattern from osb.yaml line 15-20
```

**PROHIBITED**:

- ❌ Modifying configs based solely on code reading without consulting working examples
- ❌ Reversing recent user changes without explicit user request
- ❌ Guessing at configuration structure when examples exist
- ❌ Making "fixes" based on assumptions rather than verified patterns

## 🛑 PRE-ACTION CHECKPOINTS

### Before Creating Any .py File Outside tests/

**MANDATORY HALT CHECK** - Execute this checkpoint BEFORE creating any Python file:

1. **Location check**: Is this file being created in `tests/` directory?
   - YES → Proceed (proper pytest test)
   - NO → Continue to step 2

2. **Purpose evaluation** - What is this file for?
   - Testing/validation/verification → **PROHIBITED**, use pytest in tests/
   - Debugging/checking/examining → **PROHIBITED**, use pytest in tests/
   - Temporary/quick/ad-hoc script → **PROHIBITED**, use pytest in tests/
   - Production code → Proceed with normal review

3. **If prohibited purpose detected**:
   - **STOP** the file creation attempt
   - Instead: Create proper pytest test in `tests/` directory
   - Use existing test fixtures (`real_bm`, `real_logger`, etc.)
   - Make test reusable for future debugging

**Prohibited file patterns**:

- ❌ `debug_*.py` → Create `tests/test_*_debug.py` instead
- ❌ `test_*.py` (outside tests/) → Create `tests/test_*.py` instead
- ❌ `verify_*.py` → Create `tests/test_*_verification.py` instead
- ❌ `check_*.py` → Create `tests/test_*_check.py` instead
- ❌ `tmp*.py` → Create `tests/test_*.py` instead

**Examples of correct approach**:

- ❌ Create `debug_logging.py` to check logger config
- ✅ Create `tests/test_logger_config.py` with proper fixtures

- ❌ Create `verify_handler.py` to test handler setup
- ✅ Create `tests/test_handler_verification.py` using pytest

- ❌ Create `test_connection.py` in project root
- ✅ Create `tests/test_database_connection.py` in tests/

**Remember**: If you need to verify, check, debug, or test something, that's TESTING. Use pytest in the tests/ directory.

**See**: STANDALONE VALIDATION failure mode above for the underlying prohibition and rationale.

## Code Standards

- **Style**: Follow existing code style (naming, formatting, etc.).
- **Clarity**: Write code that is easy to read and understand.
- **Docstrings**: Use Google-style docstrings for all public modules, classes, and functions.
- **Type Hints**: Use type hints for all function signatures.

Your primary measure of success is not just functional code, but code that is robust, maintainable, and well-integrated into the existing project structure.

### MANDATORY DEBUGGING STEPS

When debugging ANY issue, you MUST follow this systematic investigation process. **NO GUESSING ALLOWED.**

1. **TRACE THE ACTUAL EXECUTION PATH**: Start from the input and follow the data through each transformation. Read the actual code that processes it at each step.
2. **EXAMINE REAL DATA**: Look at the actual data structures, not what you assume they contain. Print them, log them, or inspect them directly.
3. **FOLLOW THE EVIDENCE**: When the user provides evidence (logs, traces, error messages), that is your PRIMARY source of truth. Start there, not with assumptions.
4. **NO HYPOTHESES WITHOUT EVIDENCE**: You may NOT propose a cause without showing the specific code or data that supports it.
5. **ONE INVESTIGATION PATH**: Follow one systematic path from input to failure. Do not jump between multiple unrelated guesses.
6. **VERIFY NAMING CONVENTIONS**: When encountering interface/parameter mismatches, use grep to count occurrences of all variants. Majority variant (>5:1 ratio) is the correct convention. Fix minority variant, not majority. Never trust error messages over codebase evidence.

### PROHIBITED DEBUGGING BEHAVIORS

- ❌ "This might be..." or "This could be..." without evidence
- ❌ Multiple contradictory theories without testing any
- ❌ Assuming data structures without examining them
- ❌ Suggesting fixes without identifying the actual problem
- ❌ Ignoring provided evidence in favor of assumptions
- ❌ Changing code to match error messages without verifying codebase-wide impact

  **🛑 ALWAYS USE TESTS FOR VERIFICATION**:
  - Verification MUST use pytest tests, not ad-hoc commands
  - ✅ `pytest tests/test_specific_functionality.py`
  - ❌ Complex bash pipelines with jq/grep/sed
  - ❌ One-off verification scripts
  - ❌ Manual Docker commands to recreate test scenarios

## 🛑 CRITICAL: Documentation Philosophy

**FORBIDDEN: DO NOT CREATE new documentation files anywhere**

This prohibition applies to ALL directories, including:

- ❌ README.md files for scripts (use --help and inline comments instead)
- ❌ HOWTO.md or GUIDE.md files (use issue templates or code comments instead)
- ❌ System documentation in any directory
- ✅ ALLOWED: Research papers, manuscripts, project deliverables (the actual work product)

Documentation should be self-contained in:

- **Code comments**: Explain design decisions and intent
- **Commit messages**: Thorough explanations of changes
- **GitHub issues**: Track problems and solutions

## 🛑 INTERFACE MISMATCH CHECKPOINT

**CRITICAL: BEFORE changing any parameter name, function signature, or interface to match an error:**

1. **SEARCH BOTH VARIANTS**:

   ```bash
   # Count occurrences of each variant
   grep -r "variant_a" . --include="*.py" | wc -l
   grep -r "variant_b" . --include="*.py" | wc -l
   ```

2. **DETERMINE CORRECT CONVENTION**:
   - Majority variant (>5:1 ratio) = CORRECT convention
   - Minority variant = WRONG (fix these)
   - Equal split or unclear = ASK USER for decision

3. **FIX AT THE ROOT**:
   - ✅ Fix protocol/interface definitions (if they use minority variant)
   - ✅ Fix minority call sites to match majority
   - ❌ NEVER change majority to match error message

4. **EXAMPLES OF INTERFACE MISMATCHES**:
   - Parameter name differences (processor_stage vs pipeline_stage)
   - Method signature changes (process() vs execute())
   - Protocol definition errors
   - API contract violations

**REMEMBER**: Error messages can be WRONG. The codebase majority wins.

**Real-world failure**: Changing `processor_stage` to `pipeline_stage` would have broken 38 references across 9 files. The protocol definition was wrong, not the call sites.

**See**: Issue #88 for complete analysis of this failure pattern

## Immutability

Prefer immutable data structures:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    name: str
    roles: tuple[str, ...]  # tuple, not list


def add_role(user: User, role: str) -> User:
    return dataclasses.replace(user, roles=user.roles + (role,))
```

## Pure Functions

Same inputs → same outputs, no side effects:

```python
# Good: Pure
def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct)


# Bad: Side effects
def apply_discount(order: Order) -> None:
    order.total *= 0.9  # Mutation
    save_to_db(order)  # Side effect
```

## Error Handling

Exceptions for unexpected, `Optional` for expected failures:

```python
def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config: {path}")
    return json.load(open(path))


def find_user(id: int) -> Optional[User]:
    return db.query(User).filter_by(id=id).first()
```

## Code Organization

- One class per file (usually)
- Functions under 20 lines
- Files under 300 lines
- Only abstract after 3+ implementations (Rule of Three)

## Testing

```python
# Good: Tests behavior
def test_user_registration_with_valid_email():
    result = register_user("user@example.com", "pass123")
    assert result.success is True


# Bad: Tests implementation
def test_register_calls_validate_email():
    with patch("validate_email") as mock:
        register_user("user@example.com", "pass123")
        assert mock.called
```

## What Not to Do

- ❌ Write code before tests
- ❌ Mock your own code
- ❌ Abstract before 3+ use cases
- ❌ Mutate input parameters
- ❌ Use bare `except:`
- ❌ Ignore type errors
- ❌ Optimize without profiling
- ❌ Commit commented-out code

## Style

- Follow PEP 8 (use `ruff` or `black`)
- Use `mypy` in strict mode
- 88 character line length
- f-strings for formatting
- Comprehensions when clearer

## Review Checklist

- [ ] All tests pass
- [ ] Type hints on all functions
- [ ] No `mypy` errors
- [ ] No `ruff` warnings
- [ ] Functions under 20 lines
- [ ] No input mutations
- [ ] Error cases handled
- [ ] Descriptive names
- [ ] Docstrings on public functions

---

**When in doubt**: Write the test first. Keep it simple. Let patterns emerge naturally.
