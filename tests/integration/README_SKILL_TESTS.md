---
title: Skill Script Discovery Tests
type: spec
permalink: skill-script-discovery-tests
description: End-to-end tests for skill and script discovery from any working directory
tags:
  - testing
  - skills
  - integration
---

# Skill Script Discovery Tests

End-to-end tests validating that skills and their scripts work correctly from any directory.

## Quick Validation

Run the standalone test (no pytest required):

```bash
cd $AOPS
python3 tests/integration/test_skill_discovery_standalone.py
```

This validates:

- ✓ `$AOPS` environment variable is set and valid
- ✓ `~/.claude/skills/` symlinks exist and point to framework
- ✓ Task scripts are accessible via `~/.claude/skills/tasks/scripts/`
- ✓ Scripts execute correctly from writing repo (different working directory)

## Full Test Suite

Run with pytest (requires pytest installed):

```bash
cd $AOPS
pytest tests/integration/test_skill_script_discovery.py -v
```

Tests include:

1. **Symlink architecture** - Verifies skill symlinks exist and resolve correctly
2. **Script discovery** - Confirms scripts are found without searching CWD
3. **Cross-repo execution** - Validates scripts work from non-[[AOPS]] directories
4. **Claude headless integration** - Tests that [[Claude Code]] can find and use scripts

## What These Tests Prevent

These tests catch the bug where:

- Agent runs in `writing` repo
- Agent searches for `skills/tasks/scripts/*.py` in [[CWD]]
- Search returns 0 files (because scripts are in [[AOPS]], not `writing`)
- Agent gives up thinking scripts don't exist

With proper architecture:

- Scripts live in `[[AOPS]]/skills/tasks/scripts/`
- Accessible via `~/.claude/skills/tasks/scripts/` symlink
- Skill documentation tells agents the correct path
- No searching needed - agents use documented paths directly

## Expected Output

```
======================================================================
SKILL SCRIPT DISCOVERY TEST SUITE
======================================================================

Testing AOPS environment variable...
  ✓ AOPS=/home/nic/src/academicOps
✅ PASS: AOPS environment variable valid

Testing symlink structure...
  ✓ Found: task_view.py
  ✓ Found: task_add.py
  ✓ Found: task_archive.py
✅ PASS: All required scripts exist via symlink

Testing symlink resolution...
  ✓ Both resolve to: /home/nic/src/academicOps/skills/tasks/scripts
✅ PASS: Symlink correctly points to AOPS

Testing script execution from writing repo...
  Running from: /home/nic/src/writing
  Command: uv run python ~/.claude/skills/tasks/scripts/task_view.py --compact
  ✓ Script executed successfully
  ✓ Found data directory in output
✅ PASS: Script runs from writing repo

======================================================================
SUMMARY
======================================================================
Passed: 4/4

🎉 ALL TESTS PASSED
```

## Troubleshooting

If tests fail:

1. **AOPS not set**: Add `export AOPS="/path/to/academicOps"` to `~/.bashrc`
2. **Symlinks missing**: Run `make install-dev` (or `uv run python $AOPS/scripts/install.py`) to create symlinks
3. **Scripts not found**: Check `$AOPS/skills/tasks/scripts/` exists
4. **Import errors**: Verify `PYTHONPATH=$AOPS` is set when running scripts

## Architecture

```
$AOPS/skills/tasks/scripts/       # Framework: Scripts live here
    ├── task_view.py
    ├── task_add.py
    └── task_archive.py

~/.claude/skills/tasks/scripts/   # Symlink: Agents access via this
    → $AOPS/skills/tasks/scripts/

/any/working/directory/           # Works from anywhere
    $ PYTHONPATH=$AOPS uv run python ~/.claude/skills/tasks/scripts/task_view.py
    ✓ SUCCESS
```
