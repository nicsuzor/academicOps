# Framework Migration Status

**Goal**: Enable run-from-anywhere architecture using `$AOPS` and `$ACA_DATA` environment variables.

## Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc:
export AOPS="/home/nic/src/academicOps"
export ACA_DATA="/home/nic/src/writing/data"
```

## Completed ✅

1. **Clean slate** - Wiped old academicOps, created fresh `dev` branch
2. **Framework migration** - Moved `writing/bots/` → `academicOps/` root
3. **Path library** - Created `lib/paths.py` with fail-fast resolution
4. **Test infrastructure** - Updated `tests/paths.py` to delegate to lib.paths
5. **Task scripts** - Updated task_view.py, task_add.py, task_archive.py
6. **All hooks updated** - All 8 hooks now use lib.paths
   - log_session_stop.py, log_posttooluse.py
   - log_pretooluse.py, log_sessionstart.py
   - log_subagentstop.py, log_userpromptsubmit.py
   - autocommit_state.py (finds git repo from $ACA_DATA)
   - extract_session_knowledge.py
7. **Test files updated** - tests/integration/conftest.py, tests/test_paths.py
8. **Environment variables set** - Added to ~/.env
   - `AOPS=/home/nic/src/academicOps`
   - `ACA_DATA=/home/nic/src/writing/data`
9. **Symlinks updated** - ~/.claude/ now points to $AOPS
10. **Setup script created** - `setup.sh` automates all configuration for new installations
11. **Documentation updated** - Replaced outdated `bots/` path references in markdown files
12. **Skill script architecture validated** - End-to-end tests confirm skills work from any directory
    - Created `tests/integration/test_skill_discovery_standalone.py`
    - Created `tests/integration/test_skill_script_discovery.py` (pytest version)
    - All tests passing: symlinks, script execution, cross-repo functionality
13. **Python imports fixed** - Updated all `from bots.` → `from skills.` or `from tests.`
14. **Script API compatibility** - Fixed task_view.py to use current task_ops API

## Validation ✅

### Tested and Working:
- ✅ Task scripts work from any directory (via `~/.claude/skills/` symlinks)
- ✅ Scripts accessible from writing repo with `PYTHONPATH=$AOPS`
- ✅ Symlinks resolve correctly to `$AOPS/skills/`
- ✅ No need to search for scripts in CWD
- ✅ Automated tests catch regression

## Pending 📋

1. **Integration testing** - Test from multiple directories
2. **Clean up** - Remove `writing/bots/` after validation
3. **Push to GitHub** - Push dev branch for review

## Testing Checklist

After all updates complete:

```bash
# 1. Set environment variables
export AOPS="/home/nic/src/academicOps"
export ACA_DATA="/home/nic/src/writing/data"

# 2. Test lib.paths from different directories
cd /tmp
python3 -c "from lib.paths import validate_environment; validate_environment()"

# 3. Test task scripts
cd $AOPS
uv run python skills/tasks/scripts/task_view.py

cd ~/Documents
uv run python $AOPS/skills/tasks/scripts/task_view.py

# 4. Test hooks (start Claude session from different directory)
cd /tmp
claude-code  # Should still log to $ACA_DATA/sessions

# 5. Run test suite
cd $AOPS
uv run pytest tests/

# 6. Test from writing repo
cd /home/nic/src/writing
# Claude session should still work
```

## Implementation Notes

### Path Resolution Strategy

- **Fail-fast**: No defaults, no fallbacks, explicit env vars required
- **$AOPS**: Framework root (skills, hooks, commands, tests)
- **$ACA_DATA**: Shared memory vault (tasks, sessions, projects, logs)
- **lib/paths.py**: Single source of truth for all path operations

### Why This Architecture

1. **Run from anywhere**: Framework not tied to specific directory
2. **Cross-device**: Same framework, different data locations
3. **Portable**: Others can use framework with their own data
4. **Clean separation**: Framework (code) vs content (data)
5. **Fail-fast**: Clear errors when environment not configured

## Next Session

Continue from "In Progress" section above. Priority:
1. Finish updating remaining hooks
2. Update test files
3. Set environment variables
4. Update symlinks
5. Multi-directory integration testing

Estimated time remaining: 2-3 hours
