# Task: Fix Broken Task Management Scripts

**Date**: 2025-11-10 **Stage**: 2 (Scripted Tasks - fixing existing) **Priority**: P1 (daily pain, blocking productivity) **Estimated effort**: Medium (6-8h) **GitHub Issue**: https://github.com/nicsuzor/writing/issues/38

## Problem Statement

**What manual work are we automating?**

NOT automation - fixing broken tooling. Task scripts (task_view.py, task_archive.py, task_add.py) are unreliable:

- 8 tasks have YAML parsing errors that break scripts silently
- Inconsistent identifiers (view shows index 1-10, archive takes filename, frontmatter has task_id)
- No batch operations (can't archive 10 tasks at once - need to run script 10 times)
- Silent failures instead of clear error messages

**Why does this matter?**

User is overwhelmed by things to do, can't remember them, and the task system that should help is broken. This is blocking basic productivity. Daily pain of unreliable task tracking means things get forgotten or lost.

**Who benefits?**

Nic - needs reliable task tracking to manage ADHD challenges with memory and overwhelm. Also agents who need to help with task operations but can't trust the tooling.

## Success Criteria

**The automation is successful when**:

1. **All 79 tasks load without silent failures** - YAML errors detected and reported with filename and line number
2. **Consistent identifiers across operations** - Can reference tasks the same way in view/archive/modify (likely filename-based)
3. **Batch operations work** - Can run `task_archive.py task1.md task2.md task3.md` to archive multiple tasks at once
4. **Clear error messages** - When something fails, error says exactly what's wrong and where (filename, field name, expected format)
5. **You can reliably see your task list** - `task_view.py` shows all active tasks without crashes or missing tasks

**Quality threshold**:

- **Fail-fast on structural errors** (malformed YAML, missing required fields, invalid file format) - these indicate data corruption
- **Best effort on content** (missing optional fields like due date) - show task with warning, don't crash

## Scope

### In Scope

- **Fix YAML parsing**: Robust error detection and reporting (filename, line number, what's wrong)
- **Standardize identifiers**: Use filename consistently across all scripts (task_view, task_archive, task_add)
- **Add batch operations**: task_archive.py accepts multiple filenames
- **Fix the 8 broken tasks**: Repair YAML errors in existing task files
- **Improve error messages**: Clear, actionable errors when operations fail
- **Update task_view.py**: Show filename in output so users know what to pass to other scripts

### Out of Scope

- New features (auto-categorization, smart scheduling, etc.) - separate task
- Agent session start integration - that's a framework/documentation problem, not a script problem
- UI/visualization improvements beyond error messages
- Task format changes (keep existing bmem frontmatter format)
- Migration of completed tasks (separate operation)

**Boundary rationale**: This is "fix what's broken" not "build new features". DO ONE THING = make existing task scripts reliable. Agent integration and new automation features are separate problems that depend on this foundation working first.

## Dependencies

### Required Infrastructure

- `data/tasks/inbox/` directory exists with task files
- `data/tasks/archived/` directory exists for completed tasks
- Python environment with uv (already present)
- PyYAML library (already installed)
- Task format: markdown files with YAML frontmatter (already defined, just needs better parsing)

### Data Requirements

- Read/write access to `data/tasks/` directory structure
- Task files are `.md` format with frontmatter
- **No assumptions about data quality** - scripts must handle malformed data gracefully with clear errors

**What happens if data is missing or malformed?**

- Missing directory: Create it (mkdir -p)
- Malformed YAML: Report exact error with filename and line number, continue processing other tasks
- Missing required fields: Report which field in which file, suggest fix
- Invalid file format: Skip with warning, continue processing

## Integration Test Design

**Test must be designed BEFORE implementation**

### Test Setup

Create test task directory with known good and known bad tasks:

```bash
# Create test directory
mkdir -p /tmp/task_test/{inbox,archived}

# Create good task
cat > /tmp/task_test/inbox/good-task.md <<'EOF'
---
title: Good Task
type: task
status: inbox
priority: 1
---
# Good Task
## Context
This task has valid YAML.
EOF

# Create task with YAML error (invalid syntax)
cat > /tmp/task_test/inbox/bad-yaml.md <<'EOF'
---
title: Bad Task
tags:
  - test
  invalid indentation here
priority: 1
---
# Bad Task
EOF

# Create task with missing required field
cat > /tmp/task_test/inbox/missing-field.md <<'EOF'
---
type: task
priority: 1
---
# No Title Task
EOF

# Create 3 tasks for batch archive test
for i in 1 2 3; do
  cat > /tmp/task_test/inbox/batch-$i.md <<EOF
---
title: Batch Task $i
type: task
status: inbox
---
# Batch Task $i
EOF
done
```

### Test Execution

Test each script with test data:

```bash
# Test 1: View shows all valid tasks, reports errors clearly
python3 bots/skills/tasks/scripts/task_view.py --data-dir=/tmp/task_test 2>errors.log
# Should show 4 tasks (good-task, missing-field, batch-1, batch-2, batch-3)
# Should write clear error about bad-yaml.md to errors.log with line number

# Test 2: View shows filenames so user knows what to pass to archive
# Output should include: "good-task.md", "batch-1.md", etc.

# Test 3: Archive accepts batch of filenames
python3 bots/skills/tasks/scripts/task_archive.py \
  --data-dir=/tmp/task_test \
  batch-1.md batch-2.md batch-3.md

# Test 4: Archive gives clear error if file doesn't exist
python3 bots/skills/tasks/scripts/task_archive.py \
  --data-dir=/tmp/task_test \
  nonexistent.md 2>error-nonexistent.log
# Should say: "Error: Task file 'nonexistent.md' not found in /tmp/task_test/inbox/"
```

### Test Validation

```bash
# Verify good task still in inbox
test -f /tmp/task_test/inbox/good-task.md || echo "FAIL: good task missing"

# Verify batch tasks moved to archived
test -f /tmp/task_test/archived/batch-1.md || echo "FAIL: batch-1 not archived"
test -f /tmp/task_test/archived/batch-2.md || echo "FAIL: batch-2 not archived"
test -f /tmp/task_test/archived/batch-3.md || echo "FAIL: batch-3 not archived"
test ! -f /tmp/task_test/inbox/batch-1.md || echo "FAIL: batch-1 still in inbox"

# Verify error messages are clear and actionable
grep -q "bad-yaml.md" errors.log || echo "FAIL: no filename in error"
grep -q "line" errors.log || echo "FAIL: no line number in error"
grep -q "nonexistent.md.*not found" error-nonexistent.log || echo "FAIL: unclear error for missing file"

# Verify all scripts use filename consistently (not index numbers)
# task_view output should show filenames, not just index 1, 2, 3...
```

### Test Cleanup

```bash
rm -rf /tmp/task_test
rm -f errors.log error-nonexistent.log
```

### Success Conditions

- [ ] Test initially fails (current scripts don't pass these checks)
- [ ] Test passes after implementation
- [ ] Test covers happy path (view and archive good tasks)
- [ ] Test covers error cases (bad YAML, missing files, missing fields)
- [ ] Test validates all success criteria (batch operations, clear errors, consistent identifiers)
- [ ] Test is idempotent (can run repeatedly without side effects)
- [ ] Test cleanup leaves no artifacts

## Implementation Approach

### High-Level Design

Fix each script in place (task_view.py, task_archive.py) with robust error handling, then repair broken task files.

**Components**:

1. **Robust YAML Parser**: Wrap yaml.safe_load with detailed error catching (filename, line number, what's wrong)
2. **Error Reporter**: Centralized error formatting function for consistent, actionable messages
3. **Updated task_view.py**: Show filename in output, continue on errors, report errors to stderr
4. **Updated task_archive.py**: Accept multiple filenames as arguments, process each, report which succeeded/failed
5. **Task Repair Script**: Identify and fix the 8 broken task files (one-time operation)

**Data Flow**:

- View: Read all task files → Parse with error handling → Display valid tasks + error summary
- Archive: For each filename → Validate exists → Move to archived/ → Report result
- Repair: Scan all tasks → Identify YAML errors → Fix syntax → Validate fix

### Technology Choices

**Language/Tools**: Python 3 with uv (already in use)

**Libraries**:

- PyYAML (already installed) - YAML parsing
- pathlib (stdlib) - path operations
- sys.stderr (stdlib) - error output separate from data

**Rationale**: Keep existing Python stack. No new dependencies needed. Scripts already use this approach, just need better error handling.

### Error Handling Strategy

**Fail-fast cases** (halt script, per AXIOMS.md):

- Data directory doesn't exist and can't be created
- No read/write permissions on task directory
- Script syntax error or import failure

**Graceful degradation cases** (report and continue):

- Individual task has YAML parse error → Log error with filename/line, skip task, continue processing others
- Task missing optional fields (due date, project) → Show task with warning, continue
- Archive target doesn't exist → Report "file not found", continue with next file in batch

**Recovery mechanisms**:

- Errors written to stderr with filename so user can manually fix
- Valid tasks still processed even if some fail
- Batch operations report per-file success/failure
- No data loss - archive moves files atomically, doesn't delete

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: New parsing breaks currently working tasks
   - **Detection**: Integration test fails on production data; user reports tasks disappeared
   - **Impact**: Can't view any tasks, system unusable
   - **Prevention**: Test against all 79 real tasks before deployment; keep old scripts as backup
   - **Recovery**: Revert to old scripts immediately, investigate what broke

2. **Failure mode**: Batch archive partially succeeds (some tasks archived, some failed)
   - **Detection**: Some files in inbox, some in archived, unclear which succeeded
   - **Impact**: User uncertain which tasks were archived
   - **Prevention**: Script reports per-file success/failure; transaction-like behavior (validate all before moving any)
   - **Recovery**: Check stderr for which files failed; re-run with failed files only

3. **Failure mode**: Error messages reference wrong file or line number
   - **Detection**: User tries to fix reported error but can't find it at that location
   - **Impact**: Can't fix broken tasks, frustration
   - **Prevention**: Test error reporting with known-bad YAML; verify filename and line are correct
   - **Recovery**: Add verbose mode that shows full file context around error

4. **Failure mode**: Performance degradation with 79+ tasks
   - **Detection**: task_view takes >2 seconds to run
   - **Impact**: Annoying delay, makes system feel slow
   - **Prevention**: Don't optimize prematurely - 79 files is trivial; only optimize if actual problem
   - **Recovery**: Add caching or index if needed (separate task)

5. **Failure mode**: File corruption during archive move (filesystem error, permission issue)
   - **Detection**: Task file missing from both inbox and archived
   - **Impact**: DATA LOSS - task information lost
   - **Prevention**: Use shutil.move (atomic on same filesystem); verify target exists after move
   - **Recovery**: NO RECOVERY - data is gone. Prevention is critical. Consider backup before any destructive operation.

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- **YAML error count**: Should drop from 8 to 0 after repair
- **View reliability**: task_view.py should always complete without crash
- **Archive success rate**: Batch archive operations should succeed for all valid filenames
- **Error clarity**: User should be able to fix reported errors without asking "what does this mean?"

**Monitoring approach**:

- **First week**: Run task_view daily, verify no silent failures
- **After batch operations**: Check stderr output to confirm all files succeeded
- **User feedback**: Ask "did the error message make sense?" when errors occur
- **No automated logging** - this is too simple to need telemetry

**Validation frequency**:

- Initial: Test with real 79 tasks immediately after implementation
- Ongoing: Passive - user will notice if view/archive breaks
- Manual check if new YAML errors appear (should be rare)

## Documentation Requirements

### Code Documentation

- [ ] Docstrings for new error handling functions (parse_yaml_safe, report_error)
- [ ] Inline comments explaining error recovery logic
- [ ] Type hints for Python (mypy must pass)
- [ ] Update existing docstrings in task_view.py and task_archive.py to reflect new behavior

### User Documentation

- [ ] Update bots/skills/tasks/SKILL.md with:
  - Correct usage examples showing filenames (not index numbers)
  - Batch archive syntax: `task_archive.py file1.md file2.md file3.md`
  - How to interpret error messages
- [ ] No ROADMAP update needed (this is a fix, not new automation)
- [ ] Create experiment log entry when complete

### Maintenance Documentation

- [ ] Known limitations: Can't archive from outside data/tasks/inbox/
- [ ] Future improvements: Could add `task_archive.py --all` to archive everything
- [ ] Dependencies: PyYAML (already present in uv.lock)

## Rollout Plan

### Phase 1: Test and Fix (1-2 hours)

1. Run integration test suite (from Integration Test Design section)
2. Verify test initially fails as expected
3. Implement fixes in task_view.py and task_archive.py
4. Run integration test until passes
5. Test against real 79 tasks in data/tasks/inbox/

**Criteria to proceed**: All integration tests pass, real task view shows all 79 tasks

### Phase 2: Repair Broken Tasks (30 min)

1. Run task_view against production data, capture stderr with YAML errors
2. Manually fix each of the 8 broken tasks based on error messages
3. Re-run task_view, verify error count = 0
4. Commit fixed task files

**Criteria to proceed**: All 79 tasks load without YAML errors

### Phase 3: Deploy Fixed Scripts (immediate)

1. Commit updated task_view.py and task_archive.py
2. Update SKILL.md with correct usage
3. Test batch archive with real tasks: `task_archive.py 20250821-37a814eb.md 20251014-genai-workshop.md` (the first 2 from earlier)
4. Verify archived tasks moved correctly

**Rollback plan**:

- Keep old scripts in git history
- If catastrophic failure: `git revert HEAD` and re-deploy old scripts
- Old scripts are in academicOps/scripts/ as backup reference

## Timeline Estimate

**Design and specification**: 1 hour (DONE - this document) **Integration test development**: 1 hour (write bash test script from design above) **Implementation**: 3-4 hours (robust YAML parsing, error reporting, batch archive, task repair) **Testing and refinement**: 1-2 hours (run integration tests, test with real data, fix issues) **Documentation**: 30 min (update SKILL.md with corrected usage) **Total**: 6-8 hours

**Confidence level**: High

- Fixing existing code, not building from scratch
- Problem is well-understood (we've seen the failures)
- No new dependencies or infrastructure needed
- Integration test is straightforward

## Risks and Mitigations

**Risk 1**: Break currently working tasks (regression)

- **Likelihood**: Medium (touching parsing logic)
- **Impact**: High (system unusable if all tasks fail to load)
- **Mitigation**: Test against all 79 real tasks before deployment; keep old scripts in git history for instant rollback

**Risk 2**: Miss edge cases in YAML parsing

- **Likelihood**: Medium (YAML has many obscure syntax rules)
- **Impact**: Medium (some tasks fail to parse, but graceful degradation means others still work)
- **Mitigation**: Use PyYAML's safe_load (battle-tested); catch broad exception categories; test with known-bad YAML patterns

**Risk 3**: User workflow disrupted mid-fix

- **Likelihood**: Low (this is development system, not production)
- **Impact**: Medium (can't track tasks temporarily)
- **Mitigation**: Complete all work in one session (6-8 hours); commit atomically; if interrupted, rollback to old scripts immediately

## Open Questions

1. **Batch archive transaction behavior**: Should we validate all files exist before moving any (all-or-nothing), or move files as we go and report per-file success/failure?
   - **Recommendation**: Per-file with clear reporting - more flexible, user can see which succeeded

2. **Error output location**: stderr (console) or log file in data/logs/?
   - **Recommendation**: stderr for now - simpler, user sees errors immediately

3. **Required vs optional task fields**: What makes a valid task? Is `title` required?
   - **Recommendation**: Only `type: task` required; everything else optional with warnings

## Notes and Context

This spec addresses the highest-concentration failure pattern in the framework learning log (36% of recent failures involve task management).

**Related log entries**:

- Component-Level: Task Script Identifier Inconsistency (2025-11-10)
- Behavioral Pattern: Agent Doesn't Know Task Management Interface (2025-11-10)
- Behavioral Pattern: Silent Workaround Instead of Using Documented Tools (2025-11-10)
- Behavioral Pattern: Main Agent Lacks Task Management Knowledge (2025-11-10)
- Behavioral Pattern: Task Status Not Updated After Completion (2025-11-10)

**This spec does NOT address**: Agent session start integration, auto-categorization, or smart scheduling (those are separate tasks)

---

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably (>95% success rate)
- [ ] All failure modes addressed
- [ ] Documentation complete (code, user, maintenance)
- [ ] Experiment log entry created
- [ ] No documentation conflicts introduced
- [ ] Code follows AXIOMS.md principles (fail-fast, DRY, explicit)
- [ ] Monitoring in place and working
- [ ] Rollout plan executed successfully
- [ ] Framework ROADMAP.md updated with progress

## Post-Implementation Review

[After 2 weeks of production use]

**What worked well**:

- [Aspect that exceeded expectations]

**What didn't work**:

- [Aspect that underperformed or caused issues]

**What we learned**:

- [Insights for future automations]

**Recommended changes**:

- [Improvements to make or things to do differently next time]
