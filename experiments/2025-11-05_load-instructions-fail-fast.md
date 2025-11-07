# Experiment: Load Instructions Fail-Fast Validation

## Metadata

- Date: 2025-11-05
- Issue: #192
- Commit: [pending]
- Model: claude-sonnet-4-5

## Hypothesis

Adding fail-fast validation for project tier in `load_instructions.py` will catch configuration errors (like wrong filename) immediately instead of silently falling back to framework-only instructions.

## Problem

**Issue #191 root cause:** Writing repo had `docs/bots/INSTRUCTIONS.md` but SessionStart hook looked for `docs/bots/_CORE.md`. Hook silently succeeded with framework+personal only, causing agent to lack project context for entire session.

**Fail-fast violation:** Script treated project tier as optional, couldn't distinguish between:

1. Intentionally empty (new project, no docs yet)
2. Wrong filename (file exists with different name)
3. Structural inconsistency (has docs/bots/ but missing file)

User's observation: "but it didn't fail fast. why not?"

## Changes Made

### File: `~/.claude/hooks/load_instructions.py`

**Change 1: Check if docs/bots/ exists (lines 76-81)**

Before:

```python
# Project tier (OPTIONAL)
paths["project"] = Path.cwd() / "docs" / "bots" / filename
```

After:

```python
# Project tier (REQUIRED if docs/bots/ exists)
project_dir = Path.cwd() / "docs" / "bots"
if project_dir.exists():
    paths["project"] = project_dir / filename
else:
    paths["project"] = None
```

**Change 2: Validate project file exists if directory exists (lines 293-303)**

Added after framework validation:

```python
# Project tier is REQUIRED if docs/bots/ exists
if paths["project"] is not None and "project" not in contents:
    print(f"ERROR: docs/bots/ directory exists but {args.filename} not found", file=sys.stderr)
    print(f"Searched at: {paths['project']}", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"This usually means:", file=sys.stderr)
    print(f"  1. File has wrong name (e.g., INSTRUCTIONS.md instead of {args.filename})", file=sys.stderr)
    print(f"  2. File needs to be created in docs/bots/", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"Fix: Rename existing file or create {args.filename} in docs/bots/", file=sys.stderr)
    sys.exit(1)
```

## Success Criteria

### Positive Tests (Should Succeed)

1. ✅ **New project with no docs/bots/** - Should succeed with framework+personal only
2. ✅ **Project with docs/bots/_CORE.md** - Should succeed with all three tiers
3. ✅ **Project without docs/bots/ directory** - Should succeed (no project context expected)

### Negative Tests (Should Fail-Fast)

4. ✅ **Wrong filename** - Has `docs/bots/INSTRUCTIONS.md`, looks for `_CORE.md` → EXIT 1 with clear error
5. ✅ **Empty docs/bots/** - Directory exists but no `_CORE.md` → EXIT 1 with helpful message
6. ✅ **Typo in filename** - Has `_CORE.md` but something breaks → EXIT 1 (not silent success)

## Test Results

### Test 1: New project (no docs/)

```bash
cd /tmp/test-new-project
mkdir test-repo && cd test-repo
git init
uv run python ~/.claude/hooks/load_instructions.py
# Expected: SUCCESS (framework + personal only)
# Result: [to be filled]
```

### Test 2: Project with correct _CORE.md

```bash
cd /home/nic/src/writing
uv run python ~/.claude/hooks/load_instructions.py
# Expected: SUCCESS (framework + personal + project)
# Result: [to be filled]
```

### Test 3: Wrong filename (Issue #191 scenario)

```bash
cd /home/nic/src/writing/docs/bots
mv _CORE.md INSTRUCTIONS.md  # Simulate wrong name
cd /home/nic/src/writing
uv run python ~/.claude/hooks/load_instructions.py
# Expected: EXIT 1 with error explaining wrong filename
# Result: [to be filled]
```

### Test 4: Empty docs/bots/

```bash
cd /tmp/test-empty-docs
mkdir -p test-repo/docs/bots && cd test-repo
git init
uv run python ~/.claude/hooks/load_instructions.py
# Expected: EXIT 1 with error explaining file needed
# Result: [to be filled]
```

## Outcome

[To be filled after testing]

**Success / Failure / Partial**

## Impact

- **Breaking change:** Repos with `docs/bots/` directory but no `_CORE.md` will now fail
- **Migration needed:** Create `docs/bots/_CORE.md` or remove empty `docs/bots/` dirs
- **Benefit:** Catches configuration errors immediately instead of silent failures

## Rollback Plan

If experiment fails or causes unexpected issues:

```bash
cd ~/.claude/hooks
git checkout HEAD -- load_instructions.py
```

## Notes

- This enforces Axiom #7 (fail-fast) consistently with framework tier validation
- Error message explicitly mentions common causes (wrong filename, missing file)
- Distinguishes "no docs yet" (OK) from "docs exist but file missing" (ERROR)
