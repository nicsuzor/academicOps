# Developer Agent Tool Capabilities Reference

This reference documents what tools the dev agent has access to and how the supervisor should instruct their use.

## Core Development Tools

### Read

**What it does**: Reads file contents from disk.

**When dev agent uses it**:
- Understanding existing code before modification
- Reading test files to understand patterns
- Reviewing configuration files
- Reading error logs or output files

**Supervisor instructions**:
```
"Read the current implementation in src/auth/oauth.py to understand the token validation logic"
"Read tests/test_auth.py to see existing test patterns"
```

**Constraints**:
- Can read ANY file on system
- Returns content with line numbers
- Can specify line ranges for large files
- Cannot read directories (use Bash ls for that)

---

### Edit

**What it does**: Performs exact string replacements in files.

**When dev agent uses it**:
- Modifying existing code
- Fixing specific bugs
- Updating configuration
- Refactoring code

**Supervisor instructions**:
```
"Edit src/auth/oauth.py:
- Find the validate_token() function
- Replace the expiry check logic to handle None values
- Make minimal change only"

"Edit tests/test_auth.py to use real_bm fixture instead of initialize_config_dir()"
```

**Constraints**:
- MUST read file first before editing
- String replacement must be EXACT (including whitespace)
- If match not unique, edit fails
- STRONGLY PREFER editing existing files over creating new ones
- Can use replace_all for renaming variables

---

### Write

**What it does**: Creates new files or overwrites existing ones.

**When dev agent uses it**:
- Creating new test files
- Creating new modules
- Creating JSON fixture files
- Creating configuration files

**Supervisor instructions**:
```
"Write a new test file tests/test_oauth.py using test-writing skill patterns"
"Create tests/fixtures/auth/valid_token.json with sample OAuth token data"
```

**Constraints**:
- MUST read file first if it exists (to avoid accidental overwrites)
- AVOID creating new files when editing existing would work
- Prefer Edit over Write for existing files
- Never create temporary/throwaway files

---

### Bash

**What it does**: Executes shell commands.

**When dev agent uses it**:
- Running tests: `uv run pytest tests/test_auth.py -xvs`
- Checking git status: `git status`, `git diff`
- Running builds: `uv run dbt build`
- Installing dependencies: `uv add package`
- Checking file structure: `ls`, `tree`

**Supervisor instructions**:
```
"Run the test using Bash: uv run pytest tests/test_auth.py::test_user_login -xvs"
"Check git status to see what files were modified"
"Run all tests to check for regressions: uv run pytest"
```

**Constraints**:
- For file operations, prefer specialized tools (Read, Edit, Write, Grep, Glob)
- For terminal operations (git, pytest, build tools), use Bash
- Can chain commands with && for sequential execution
- Use parallel Bash calls for independent commands

---

### Grep

**What it does**: Searches file contents for patterns (regex).

**When dev agent uses it**:
- Finding where a function is defined
- Searching for specific error patterns
- Finding usages of a variable or import
- Locating test patterns

**Supervisor instructions**:
```
"Use Grep to find all usages of validate_token function"
"Search for any .get() calls with defaults in src/ directory"
"Find tests that use initialize_config_dir() pattern"
```

**Constraints**:
- Returns file paths or content based on output_mode
- Supports full regex syntax
- Can filter by file type (--type python)
- Use for content search, not file name search

---

### Glob

**What it does**: Finds files matching patterns.

**When dev agent uses it**:
- Finding test files: `tests/test_*.py`
- Finding all Python files: `**/*.py`
- Finding configuration files: `conf/**/*.yaml`
- Listing files in directory: `src/auth/*.py`

**Supervisor instructions**:
```
"Use Glob to find all test files in tests/ directory"
"List all Python files in src/auth/ module"
```

**Constraints**:
- Use for file name patterns, not content search
- Fast and efficient for file discovery
- Returns sorted list of matching paths

---

### Task (Subagent Invocation)

**What it does**: Launches specialized subagents for complex work.

**When dev agent uses it**:
- RARELY - dev agent should do atomic work, not delegate further
- Only when supervisor explicitly tells dev to use a subagent

**Supervisor should NOT typically tell dev agent to use Task tool** - supervisor handles orchestration.

---

## Skill Invocation

### Skill

**What it does**: Invokes specialized skills (test-writing, git-commit, etc.).

**When dev agent uses it**:
- When supervisor EXPLICITLY requires skill usage
- "Use test-writing skill to..."
- "Use git-commit skill to..."

**Supervisor instructions**:
```
"Use test-writing skill to create failing test for OAuth login"
"Use git-commit skill to validate and commit these changes"
```

**Constraints**:
- Dev MUST use skill when supervisor requires it
- Cannot skip or work around required skills
- Reports back after skill completes

---

## Tool Usage Patterns for Common Tasks

### Pattern: Create Test (TDD Cycle)

**Supervisor instructions**:
```
Use test-writing skill to create ONE failing test:

Behavior: [specific behavior to test]
File: tests/test_[name].py
Function: test_[behavior]

Steps:
1. Use test-writing skill (it will guide test creation)
2. Use real_bm or real_conf fixture
3. Load data from JSON fixtures
4. Mock only external APIs (use respx)
5. Test behavior, not implementation

After test created:
- Run using Bash: uv run pytest tests/test_[name].py::test_[function] -xvs
- Verify it fails with expected error
- Report test location, run command, failure message
```

**Tools dev agent will use**:
- Skill (test-writing)
- Write (create test file) or Edit (modify existing test file)
- Write (create JSON fixtures if needed)
- Bash (run pytest to verify test fails)

---

### Pattern: Implement Minimal Code

**Supervisor instructions**:
```
Implement MINIMAL code to make this ONE test pass:

Test: tests/test_auth.py::test_user_login
File to modify: src/auth/oauth.py
Requirement: [specific functionality needed]

Steps:
1. Read current implementation in src/auth/oauth.py
2. Make minimal change to pass the test
3. Follow fail-fast principles (no .get(), no defaults, no fallbacks)
4. NO 'while I'm here' fixes

After implementation:
- Run test: uv run pytest tests/test_auth.py::test_user_login -xvs
- Run all tests: uv run pytest
- Report what changed, which files modified, test results
```

**Tools dev agent will use**:
- Read (understand current code)
- Edit (make minimal changes)
- Bash (run tests)

---

### Pattern: Fix Test Failure

**Supervisor instructions**:
```
Fix this test failure:

Test: tests/test_auth.py::test_user_login
Error: AttributeError: 'NoneType' object has no attribute 'expiry'
File: src/auth/oauth.py:45

Analysis: Token expiry check doesn't handle None values

Fix required:
- Add explicit check for None before accessing expiry attribute
- Raise AuthenticationError if token is None
- Minimal change only

After fix:
- Run test: uv run pytest tests/test_auth.py::test_user_login -xvs
- Report test result
```

**Tools dev agent will use**:
- Read (examine code at error location)
- Edit (fix the specific issue)
- Bash (re-run test)

---

### Pattern: Commit with Validation

**Supervisor instructions**:
```
Use git-commit skill to validate and commit:

Changes: Implemented OAuth token validation with expiry checks
Test: tests/test_auth.py::test_user_login (now passing)

The git-commit skill will validate:
- Code quality standards
- Fail-fast compliance
- Test patterns
- Documentation

If validation FAILS:
- Report all violations with file:line
- STOP and wait for fix instructions

If validation PASSES:
- Commit will be created
- Report commit hash
```

**Tools dev agent will use**:
- Skill (git-commit) - this skill internally uses Bash for git operations

---

### Pattern: Search and Understand

**Supervisor instructions**:
```
Find all usages of initialize_config_dir() in test files:

1. Use Grep to search tests/ directory for "initialize_config_dir"
2. Report all files and line numbers where it appears
3. Read one example test file to understand the pattern
4. Report how many tests use this anti-pattern
```

**Tools dev agent will use**:
- Grep (find usages)
- Read (understand example)

---

## Tools Dev Agent Does NOT Have

❌ **No WebFetch** - Dev agent cannot fetch URLs
❌ **No WebSearch** - Dev agent cannot search the web
❌ **No TodoWrite** - Dev agent does not manage its own todos (supervisor does)
❌ **No BashOutput/KillShell** - Dev agent doesn't manage background shells
❌ **No NotebookEdit** - Dev agent doesn't edit Jupyter notebooks directly

## Supervisor's Instruction Guidelines

### ✅ DO: Be Explicit and Specific

```
"Read src/auth/oauth.py to understand current token validation logic.
Then Edit src/auth/oauth.py to add expiry check at line 45.
Make minimal change only - add explicit None check before accessing token.expiry.
After editing, run test: uv run pytest tests/test_auth.py::test_user_login -xvs"
```

### ❌ DON'T: Be Vague

```
"Fix the token validation"
```

### ✅ DO: Specify Tools and Sequence

```
"Use Grep to find all .get() calls in src/ directory.
Read each file that has violations.
For each violation, Edit to replace .get(key, default) with [key] to enforce fail-fast.
After all edits, run tests: uv run pytest"
```

### ❌ DON'T: Assume Dev Knows What to Do

```
"Make the code fail-fast compliant"
```

### ✅ DO: Require Skills When Needed

```
"Use test-writing skill to create ONE failing test for OAuth login"
```

### ❌ DON'T: Let Dev Skip Required Skills

```
"Write a test for OAuth login"
```

## Tool Availability Summary

| Tool | Purpose | Dev Agent Has? | When Supervisor Mentions |
|------|---------|----------------|--------------------------|
| Read | Read files | ✅ YES | "Read [file] to understand..." |
| Edit | Modify files | ✅ YES | "Edit [file] to fix..." |
| Write | Create files | ✅ YES | "Create [file] with..." |
| Bash | Run commands | ✅ YES | "Run test: uv run pytest..." |
| Grep | Search content | ✅ YES | "Search for [pattern] in..." |
| Glob | Find files | ✅ YES | "Find all files matching..." |
| Skill | Use skills | ✅ YES | "Use [skill-name] skill to..." |
| Task | Launch subagents | ✅ YES (but rarely used) | Usually supervisor orchestrates |
| TodoWrite | Manage todos | ❌ NO | Supervisor manages todos |
| WebFetch | Fetch URLs | ❌ NO | N/A |
| WebSearch | Search web | ❌ NO | N/A |

## Anti-Patterns to Avoid

### ❌ Letting Dev Agent Self-Orchestrate

**BAD**:
```
"Implement OAuth authentication feature"
```

This is too broad. Dev agent might:
- Write tests and code together (not TDD)
- Skip using required skills
- Do multiple steps without reporting back

**GOOD**:
```
Step 1: "Use test-writing skill to create ONE failing test for OAuth login"
[Wait for report]
Step 2: "Implement minimal code in src/auth/oauth.py to make test pass"
[Wait for report]
Step 3: "Use git-commit skill to validate and commit"
```

### ❌ Not Specifying Which Tool

**BAD**:
```
"Check if there are any defensive programming patterns in the code"
```

Dev agent might use wrong approach or miss patterns.

**GOOD**:
```
"Use Grep to search src/ for .get(key, default) patterns.
Report all files and line numbers with defensive .get() usage."
```

### ❌ Allowing Tool Misuse

**BAD** (if you notice):
```
Dev agent creates temp.py file for one-time analysis
```

**CORRECT** (enforce):
```
"Do NOT create temporary files. If you need to analyze data, write it as a proper test or utility in the appropriate location."
```

## Summary

The supervisor controls the dev agent by:

1. **Specifying exactly which tools to use** - "Use Grep to find...", "Edit src/file.py to fix..."
2. **Providing complete parameters** - File paths, patterns, specific changes needed
3. **Sequencing operations** - Step 1: Read, Step 2: Edit, Step 3: Run test
4. **Requiring skills explicitly** - "Use test-writing skill to..."
5. **Enforcing single-task atomicity** - One operation, report back, wait

Dev agent has powerful tools. Supervisor must wield them with precision.
