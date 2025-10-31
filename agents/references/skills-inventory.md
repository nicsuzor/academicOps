# Skills Inventory for Supervisor

This reference documents all available skills that the supervisor can explicitly require the dev agent to use during orchestration.

## Core Development Skills

### test-writing

**Purpose**: Create and maintain integration tests using real fixtures and TDD methodology.

**When supervisor should require**: EVERY time tests need to be written or modified.

**Explicit delegation pattern**:
```
Task(subagent_type="dev", prompt="
Use test-writing skill to create ONE failing test for [specific behavior].

Test requirements:
- File: tests/test_[name].py
- Function: test_[specific_behavior]
- Use real_bm or real_conf fixture (NO config loading in test)
- Load test data from JSON fixtures in tests/fixtures/
- NEVER mock internal code (only external APIs with respx)
- Test behavior, not implementation

Expected: Test should fail with [specific error message]

After creating test, STOP and report:
- Test file and function name
- How to run it: uv run pytest tests/test_[name].py::test_[function] -xvs
- Expected failure message
")
```

**Key constraints to enforce**:
- MUST use real_bm or real_conf fixtures
- FORBIDDEN: initialize_config_dir(), compose(), GlobalHydra in test files
- FORBIDDEN: Mocking internal code (buttermilk.*, bot.*, project code)
- REQUIRED: JSON fixture files for test data
- REQUIRED: Integration test pattern (test complete workflows)

**Success signals**: Dev reports test file created, shows how to run it, describes expected failure.

**Failure signals**: Dev creates unit test, mocks internal code, uses fake data inline, loads config in test file.

---

### git-commit

**Purpose**: Validate code quality and execute commits with enforced standards.

**When supervisor should require**: EVERY time code is ready to commit (after tests pass).

**Explicit delegation pattern**:
```
Task(subagent_type="dev", prompt="
Use git-commit skill to validate and commit these changes:

Changes summary: [what was implemented]
Test that passes: [specific test name]

The git-commit skill will:
1. Run validation checks against code quality standards
2. Check for fail-fast violations (.get() with defaults, fallbacks, etc.)
3. Verify test patterns (real fixtures, no mocks of internal code)
4. Check documentation and code structure
5. Execute commit ONLY if all validation passes

If validation FAILS:
- Report ALL violations with file:line numbers
- STOP and wait for instructions
- Do NOT commit

If validation PASSES:
- Commit will be created automatically
- Report commit hash

After git-commit skill completes, report:
- PASS or FAIL status
- If PASS: commit hash
- If FAIL: list of violations with specific file:line references
")
```

**Key constraints to enforce**:
- Blocks commit if ANY critical rule violated
- Reports specific violations (file:line, what's wrong, how to fix)
- Does NOT fix problems automatically
- Uses conventional commit format
- Includes Claude Code attribution

**Success signals**: Dev reports commit hash OR specific violations that need fixing.

**Failure signals**: Dev commits without using skill, fixes violations without reporting them, skips validation.

---

## Framework Maintenance Skills

### aops-bug

**Purpose**: Track agent violations, framework bugs, and experiments in academicOps.

**When supervisor should require**: When agent violates axioms, infrastructure fails, or experiments need documentation.

**Explicit delegation pattern**:
```
Task(subagent_type="dev", prompt="
Use aops-bug skill to document this [violation/bug/experiment]:

Issue: [specific problem or violation]
Context: [where occurred, what task]
Evidence: [agent output, error message, or behavior]

The aops-bug skill will:
1. Identify which axiom was violated (if applicable)
2. Categorize the behavioral pattern
3. Search for existing GitHub issues
4. Update existing issue OR create new one
5. Create experiment log if in academicOps repo

After aops-bug skill completes, report:
- Issue number (existing or new)
- Behavioral pattern identified
- Whether experiment log was created
")
```

**Key constraints to enforce**:
- MUST search exhaustively before creating new issue
- MUST categorize by behavioral pattern
- MUST link to violated axiom from _CORE.md
- Creates experiment log ONLY if in academicOps repo

**Success signals**: Dev reports issue number, pattern identified, experiment log location (if created).

**Failure signals**: Dev creates duplicate issue, doesn't categorize pattern, skips search.

---

### github-issue

**Purpose**: Universal GitHub issue management (search, create, update, close).

**When supervisor should require**: When documenting bugs in any project (not academicOps-specific).

**Explicit delegation pattern**:
```
Task(subagent_type="dev", prompt="
Use github-issue skill to [search/create/update] issue in [owner/repo]:

Action: [search for existing / create new / update #123 / close #123]

[If searching]:
- Search terms: [keywords, error messages, component names]
- Use at least 3 search strategies
- Report all matches found

[If creating]:
- Title: [specific, searchable title]
- Type: [bug/feature/docs]
- Include: reproduction steps, error details, environment info
- Labels: [suggested labels]

[If updating]:
- Issue: #[number]
- Update: [new information, findings, commit links]

After github-issue skill completes, report:
- Issue number and URL
- Search results (if searching)
- Status (created/updated/closed)
")
```

**Key constraints to enforce**:
- MUST search before creating (3+ strategies)
- MUST use clear, specific titles
- MUST include technical details (file:line, errors, environment)
- MUST verify correct repository

**Success signals**: Dev reports issue number, URL, and action taken.

**Failure signals**: Dev creates duplicate (didn't search), vague title/description, wrong repository.

---

## Analysis & Documentation Skills

### scribe

**Purpose**: Silently capture tasks, priorities, and context to user's knowledge base.

**When supervisor should require**: RARELY - scribe operates automatically and invisibly.

**Note**: Supervisor should NOT typically invoke scribe skill. It runs proactively in background to capture information. Only mention if user explicitly requests task/context capture.

---

### archiver

**Purpose**: Archive experimental analysis into long-lived Jupyter notebooks before data removal.

**When supervisor should require**: When completing experiments that will become unreproducible (data removal, major pipeline changes).

**Explicit delegation pattern**:
```
Task(subagent_type="dev", prompt="
Use archiver skill to preserve this experimental work:

Experiment: [description]
Data location: [paths to data/analysis being removed]
Key findings: [what needs to be preserved]

The archiver skill will:
1. Create Jupyter notebook documenting analysis
2. Include data summaries, visualizations, findings
3. Export to HTML for permanent record
4. Clean up working directories

After archiver skill completes, report:
- Notebook location
- HTML export location
- What was archived
- What was cleaned up
")
```

**Key constraints to enforce**:
- MUST export to HTML (permanent record)
- MUST document methodology and findings
- Cleans up only AFTER archive complete

**Success signals**: Dev reports notebook and HTML locations, confirms cleanup.

**Failure signals**: Dev cleans up before archiving, skips HTML export, incomplete documentation.

---

### analyst

**Purpose**: Support academic research data analysis (dbt, Streamlit, statistical analysis).

**When supervisor should require**: When working with computational research projects (dbt/ directory, Streamlit apps).

**Note**: Analyst is typically invoked via `/analyst` command for research-focused work. Supervisor should reference this skill when working in academic research contexts but may not need to explicitly delegate to it (user invokes directly).

---

## Skill Usage Decision Tree

When orchestrating dev agent work, use this decision tree to determine which skills to require:

```
DECISION POINT: Tests needed?
├─ YES → REQUIRE test-writing skill
│   └─ Create failing test FIRST (TDD)
│       └─ Then implement minimal code to pass
│
DECISION POINT: Code ready to commit?
├─ YES → REQUIRE git-commit skill
│   ├─ If validation PASSES → Commit succeeds
│   └─ If validation FAILS → Fix violations, retry
│
DECISION POINT: Agent violated axiom or framework bug?
├─ YES, in academicOps → REQUIRE aops-bug skill
├─ YES, in other project → REQUIRE github-issue skill
│
DECISION POINT: Experiment complete with data removal pending?
├─ YES → REQUIRE archiver skill
│   └─ Archive BEFORE any cleanup
```

## Forbidden Patterns

**NEVER allow dev agent to**:
- Write tests without using test-writing skill
- Commit code without using git-commit skill
- Mock internal code (use respx for external APIs only)
- Load Hydra configs in test files (use real_bm/real_conf)
- Use .get() with defaults, fallbacks, or defensive programming
- Create new files when editing existing would work
- Do multiple steps without reporting back

**ALWAYS require dev agent to**:
- Use specified skill when supervisor requires it
- Report back after EACH atomic task
- Stop and wait for next instruction
- Use real fixtures and integration test patterns
- Follow fail-fast principles (no defaults, no fallbacks)
- Test behavior (not implementation)

## Supervisor's Responsibility

When instructing dev agent:

1. **Be explicit about skill usage**: "Use test-writing skill to..." not "Write a test for..."

2. **Provide complete requirements**: Don't just say "fix it" - specify exactly what needs to be done, which skill to use, what success looks like.

3. **Enforce single-task focus**: Dev agent does ONE thing, reports back, waits for next instruction.

4. **Iterate on failures**: When git-commit skill reports violations, YOU analyze them and give dev specific fix instructions.

5. **Verify skill was used**: Check dev's report to confirm skill was actually invoked (not just work done directly).

## Example: Correct vs Incorrect Delegation

❌ **INCORRECT** (vague, no skill required):
```
Task(subagent_type="dev", prompt="Write a test for authentication and commit it")
```

✅ **CORRECT** (explicit, skill required, specific):
```
Task(subagent_type="dev", prompt="
Use test-writing skill to create ONE failing test:

Behavior: User can log in with valid OAuth token
File: tests/test_auth.py
Function: test_user_login_with_valid_oauth_token

Requirements:
- Use real_bm fixture
- Load test token from tests/fixtures/auth/valid_token.json
- Mock external OAuth API with respx
- Test should fail with: 'AuthService not implemented'

After creating test, STOP and report:
- Test location: tests/test_auth.py::test_user_login_with_valid_oauth_token
- Run command: uv run pytest tests/test_auth.py::test_user_login_with_valid_oauth_token -xvs
- Expected failure message
")
```

## Summary

The supervisor's role is to TIGHTLY CONTROL the dev agent by:

1. **Specifying exactly which skill to use** - "Use test-writing skill to..." not "Write a test"
2. **Providing complete, specific instructions** - What to do, why, what success looks like
3. **Enforcing single-task atomicity** - ONE task, report back, wait
4. **Iterating on failures** - Analyze failures, give specific fix instructions
5. **Verifying skill usage** - Check that dev actually used the required skill

Skills are the supervisor's enforcement mechanism. Use them explicitly and consistently.
