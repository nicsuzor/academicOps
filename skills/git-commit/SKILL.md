---
name: git-commit
description: This skill should be used when committing code changes to git repositories.
  It validates code quality against defined standards, enforces conventional commit
  format, handles submodule patterns, and executes commits only when all validation
  passes. The skill reports problems without fixing them, maintaining fail-fast principles.
  Use this skill any time code needs to be committed to ensure quality gates are enforced.
permalink: aops/skills/git-commit/skill
---

# Git Commit

## Overview

Validate code quality and execute git commits with enforced standards. This skill acts as the quality gate for all repository commits, ensuring code meets defined standards before allowing changes to enter the repository.

## When to Use This Skill

Use git-commit when:

1. **Code changes are complete** - Ready to commit implementation
2. **Tests are passing** - Validation step after TDD cycle
3. **Documentation updated** - Committing doc changes
4. **Any repository change** - This is the ONLY way to commit code

**Concrete trigger examples**:
- "Commit these changes with message 'Add user authentication'"
- "I've finished the feature, ready to commit"
- "Commit the test file I just created"
- "Save this work to git"

**Critical**: This skill has absolute authority over commits. If validation fails, it BLOCKS the commit and reports specific issues. It does NOT fix problems - agents must address issues and retry.

## Follow Commit Workflow

Follow this 6-step validation and commit workflow.

### Step 1: Identify Changed Files

**Objective**: Determine what files have been modified, added, or deleted.

**Process**:

1. **Run git status**:
   ```bash
   git status
   ```
   - Lists untracked files
   - Shows staged and unstaged changes
   - Indicates current branch

2. **Run git diff** for detailed changes:
   ```bash
   git diff        # Unstaged changes
   git diff --staged   # Staged changes
   git diff HEAD   # All changes since last commit
   ```

3. **Collect file list**:
   - Note all modified files
   - Note all new files
   - Note any deleted files

**Output**: Complete list of changed files for validation.

### Step 2: Load Validation Rules

**Objective**: Load applicable code quality standards from validation files.

**File Hierarchy** (3-tier fallback):

1. **Core standards** (ALWAYS load if they exist):
   - `references/TESTS.md` - Test file standards
   - `references/FAIL-FAST.md` - Fail-fast philosophy
   - `references/GIT-WORKFLOW.md` - Git workflow patterns

2. **Project-specific rules** (if exists):
   - `<project>/docs/agents/CODE.md` - Project validation rules
   - `<project>/docs/agents/COMMIT.md` - Project commit standards

3. **User-specific rules** (if exists):
   - `${OUTER}/docs/agents/CODE.md` - Personal standards
   - `${OUTER}/docs/agents/COMMIT.md` - Personal commit preferences

**Process**:

1. **Attempt to read each validation file** using Read tool
2. **Extract rules** from each file:
   - Required patterns (MUST)
   - Forbidden patterns (MUST NOT)
   - File-specific rules
   - Language-specific standards
3. **Aggregate all rules** into comprehensive checklist
4. **If ALL core files missing**: BLOCK commit with error

**Generalization Note**: The exact paths above are examples from one repository structure. In any repository:
- Look for validation rules in `references/`, `docs/agents/`, or similar documentation directories
- Adapt paths to the repository's structure
- Fail-fast if NO validation rules found anywhere

### Step 3: Build Validation Checklist

**Objective**: Create structured checklist from loaded rules organized by category.

**Checklist Structure**:

```markdown
## File-Specific Rules
- [ ] test_*.py files use real_bm or real_conf fixtures
- [ ] test files do not use initialize_config_dir()
- [ ] ...

## Language-Specific Standards
- [ ] Python files follow PEP 8
- [ ] No bare except clauses
- [ ] ...

## Project-Wide Conventions
- [ ] No hardcoded paths
- [ ] No environment variable access in code
- [ ] ...

## Security Requirements
- [ ] No secrets in code (.env files not committed)
- [ ] No API keys in source
- [ ] ...

## Testing Requirements
- [ ] Tests exist for new functionality
- [ ] All tests passing
- [ ] ...

## Documentation Requirements
- [ ] Public functions have docstrings
- [ ] README updated if API changed
- [ ] ...
```

**Process**:

1. **Organize rules by category** (file-specific, language, project, security, testing, docs)
2. **Make rules specific** - include detection patterns, line numbers, evidence requirements
3. **Mark criticality** - which violations BLOCK vs. WARN
4. **Reference source** - track which validation file each rule came from

### Step 4: Execute Validation

**Objective**: Apply checklist to each changed file and collect evidence.

**For each changed file**:

1. **Read the file** using Read tool
2. **Apply relevant rules**:
   - Check forbidden patterns (grep for specific strings)
   - Check required patterns (grep for expected structure)
   - Validate file structure and organization
   - Check security concerns

3. **Mark each checklist item**:
   - ✅ **PASS**: Rule satisfied, provide brief confirmation
   - ❌ **FAIL**: Rule violated, provide:
     - Exact file name and line number
     - Code snippet showing violation
     - Why it violates the rule
     - How to fix it
   - ⚠️ **WARNING**: Non-blocking issue, describe concern
   - **N/A**: Rule doesn't apply to this file

4. **Collect evidence**:
   - Line numbers for violations
   - Code snippets (keep under 10 lines per violation)
   - Specific remediation steps

**Example Validation**:

```markdown
### test_auth.py

File-Specific Rules:
- ❌ FAIL: Uses initialize_config_dir()
  - Line 15: `initialize_config_dir(config_path="conf")`
  - Violation: Test files MUST use real_bm or real_conf fixtures
  - Fix: Replace with `def test_auth(real_bm)` and use real_bm fixture
  - Source: references/TESTS.md line 17

- ✅ PASS: Uses real fixture pattern correctly in test_login()

Testing Requirements:
- ✅ PASS: Test file exists for new auth functionality
```

### Step 5: Generate Validation Report

**Objective**: Produce clear, structured report of validation results.

**Report Format**:

```markdown
## PRE-COMMIT VALIDATION REPORT

### Summary
- Files Reviewed: 3
- Rules Checked: 24
- Status: [APPROVED | BLOCKED]

### Validation Results

#### test_auth.py
- Rules Applied: 8
- Passed: 7
- Failed: 1
- Warnings: 0

**BLOCKING ISSUE**:
❌ File-Specific Rule: real_bm fixture required
  - Line 15: `initialize_config_dir(config_path="conf")`
  - Violation: Test files MUST use real_bm or real_conf fixtures
  - Fix: Replace with `def test_auth(real_bm)` and use real_bm fixture
  - Source: references/TESTS.md line 17

#### auth.py
- Rules Applied: 12
- Passed: 12
- Failed: 0
- Warnings: 0

✅ All rules passed

#### README.md
- Rules Applied: 4
- Passed: 4
- Failed: 0
- Warnings: 0

✅ All rules passed

### Verdict

[BLOCKED] This commit violates critical validation rules and MUST NOT proceed:

**Blocking Issues** (must fix before commit):
1. test_auth.py:15 - Uses initialize_config_dir() instead of real_bm fixture

**Required Actions**:
- Update test_auth.py to use real_bm fixture
- Remove initialize_config_dir() call
- Re-run validation after fixes

---

[APPROVED] This commit meets all required standards and may proceed.
- All 24 validation rules passed
- Ready to commit
```

**Process**:

1. **Summarize results**:
   - Total files, rules, pass/fail counts
   - Overall status (APPROVED or BLOCKED)

2. **Detail each file**:
   - List each rule with status
   - Provide full evidence for failures
   - Include warnings even if not blocking

3. **Render verdict**:
   - **APPROVED**: All critical rules pass → proceed to commit
   - **BLOCKED**: Any critical rule failed → list all blocking issues with remediation steps

4. **Display report** to the invoking agent/user

### Step 6: Commit (If Approved) or Block (If Failed)

**Objective**: Execute commit if validation passed, or block with specific feedback if failed.

**If BLOCKED**:

1. **Do NOT commit** - Validation failed
2. **Return detailed report** with:
   - All blocking issues listed
   - Specific line numbers and violations
   - Concrete remediation steps
3. **Stop execution** - Agent must fix issues and re-invoke skill

**If APPROVED**:

1. **Draft commit message** following conventional commits format:
   ```
   <type>(<scope>): <subject>

   <body>

   Fixes #<issue>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   **Types**: fix, feat, docs, refactor, test, chore
   **Scopes**: Vary by repository (e.g., prompts, infrastructure, docs for bot/ repo)
   **Subject**: 1-line summary (why, not what)
   **Body**: 1-2 sentences of detail

2. **Stage all changed files**:
   ```bash
   git add .
   ```
   OR for specific files:
   ```bash
   git add file1.py file2.md file3.py
   ```

3. **Execute commit** with heredoc format:
   ```bash
   git commit -m "$(cat <<'EOF'
   feat(auth): Add user authentication system

   Implements login, logout, and token refresh endpoints.

   Fixes #42

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

4. **Verify commit**:
   ```bash
   git status
   git log -1
   ```

5. **Report success**:
   ```
   ✅ COMMIT SUCCESSFUL

   Commit: a1b2c3d
   Message: feat(auth): Add user authentication system
   Files: 3 changed
   ```

**Submodule Pattern** (if in submodule like bot/):

For submodule commits, chain commands in ONE bash call:

```bash
cd /path/to/submodule && git add . && git commit -m "$(cat <<'EOF'
fix(prompts): Update validation workflow

Details here.

Fixes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" && git status
```

**Why**: Bash tool resets working directory after each call. Chaining with `&&` keeps directory context.

## Conventional Commits Reference

See `references/conventional-commits.md` for detailed format guide.

**Quick Reference**:

```
<type>(<scope>): <subject line>

<body: 1-2 sentences>

Fixes #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `fix` - Bug fixes
- `feat` - New features
- `docs` - Documentation only
- `refactor` - Code restructuring, no behavior change
- `test` - Adding or updating tests
- `chore` - Maintenance, tooling, configs

**Scopes** (repository-specific examples):
- For bot/ repo: `prompts`, `infrastructure`, `docs`
- For projects: `api`, `models`, `ui`, `tests`
- Adapt to your repository structure

## Validation Rule References

See `references/validation-rules.md` for comprehensive list of common validation patterns.

**Core Principles**:
- **Fail-fast**: No defaults, no fallbacks, no workarounds
- **Explicit configuration**: All config in YAML, not code or env vars
- **Real fixtures**: Tests use real_bm/real_conf, never mock internal code
- **TDD**: Tests exist before implementation
- **No secrets**: Never commit .env, credentials, API keys

## Critical Rules

**NEVER**:
- Allow commit if ANY validation rule violated
- Fix problems automatically (report only, don't fix)
- Make assumptions about rule interpretation (strict and literal)
- Provide workarounds to bypass validation
- Skip staging files before commit
- Use imprecise feedback ("something's wrong" → specific file:line)

**ALWAYS**:
- Stage files with `git add` before committing (MANDATORY)
- Provide specific, actionable feedback with line numbers
- Reference exact file locations for violations
- Block commit if ALL validation files missing
- Use heredoc format for commit messages (proper multiline handling)
- Include Claude Code attribution and Co-Authored-By line

## Edge Cases

**No validation files found**:
- Check all three locations (core, project, user)
- BLOCK commit and report which locations checked
- Error message: "No validation files found in <locations>. Cannot validate commit."

**Empty changes** (git status shows nothing):
- Report: "No changes to commit"
- Log attempt for audit
- Don't create empty commit

**Partial file changes** (only some lines modified):
- Validate ENTIRE file, not just changed lines
- Rationale: Ensures overall file quality
- Exception: If validation rule explicitly scopes to changed lines only

**Generated code** (e.g., from code generators):
- Apply same standards unless validation rules explicitly exempt
- Check for exemption patterns in validation files

**Emergency commits**:
- NO exceptions
- All commits must pass validation
- If truly urgent, fix the blocking issues (they're usually quick)

**Pre-commit hook modifications**:
- If pre-commit hooks modify files after commit
- Check commit authorship: `git log -1 --format='%an %ae'`
- Check not pushed: `git status` shows "Your branch is ahead"
- If both true AND modifications minor: May amend commit
- Otherwise: Create NEW commit with hook changes

## Success Criteria

A successful git-commit skill invocation achieves:

1. **All validation rules checked** against changed files
2. **Clear verdict** (APPROVED or BLOCKED) with evidence
3. **Specific feedback** if blocked (file:line, violation, fix)
4. **Proper commit** if approved (conventional format, staged files, attribution)
5. **No fixes applied** - skill reports only, doesn't modify code

## Quick Reference

**Full commit workflow**:

```bash
# 1. Check what changed
git status
git diff

# 2. [Skill loads validation rules from references/ or similar]

# 3. [Skill validates each file against rules]

# 4. [Skill generates validation report]

# 5a. If BLOCKED - Report issues and stop
# 5b. If APPROVED - Stage and commit:

git add .
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body>

Fixes #<issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git status  # Verify success
```

**Submodule commit** (one chained command):

```bash
cd /path/to/submodule && git add . && git commit -m "$(cat <<'EOF'
fix(prompts): Update validation

Details.

Fixes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" && git status
```
