# Experiment: validate_env.py Flat Architecture Refactor

**Date**: 2025-10-17
**Commit**: (rolled back, not committed)
**Issue**: #114 (architecture), #118 (experiment tracking)
**Agent**: General agent (developer instructions should have been active)

## Hypothesis

Updating validate_env.py to support flat architecture (~/src/bot, ~/src/writing, ~/src/buttermilk as siblings) would enable incremental migration from polyrepo structure.

## Implementation

**Changes attempted**:
1. Added `find_sibling_directory()` function to search for `../writing`
2. Modified `get_repo_root()` to detect flat vs polyrepo architecture
3. Added fallback logic: try flat architecture, fall back to polyrepo

**Code violation #1: Dual code paths**
```python
# Check if we're in flat architecture (bot is sibling to writing)
if writing_sibling and writing_sibling.is_dir():
    # Flat architecture: return parent of siblings
    return bot_root.parent

# Fall back to polyrepo: repo root is two levels up from bot/
return bot_root.parent
```

**Code violation #2: Hardcoded paths**
```python
def get_repo_root() -> Path:
    """Returns ~/src/ (parent directory containing bot/, writing/, and project repos)."""
    # ...
    return bot_root.parent  # ~/src/  <-- assumes ~/src/
```

## Violations

1. **Dual code paths**: Added backward compatibility instead of committing to one golden path
   - Violates simplicity principle
   - Creates maintenance burden
   - Delays full migration commitment

2. **Hardcoded path assumptions**: Assumed `~/src/` directory structure
   - Violates "no hardcoded paths" principle
   - Breaks if user organizes repos differently (e.g., `/opt/academicops/`)

3. **Trainer performance failure**: Failed to track violations in experiment system when user requested
   - Posted to issue #114 instead of experiments/
   - Did not reference experiment tracking infrastructure
   - Required second user intervention to correct

## Outcome

**FAILED**: Changes rolled back before commit.

**User feedback**:
- "nope, no dual paths. one golden path."
- "nope, no hardcoded paths."
- "not in issue 114. this is about agents not following the developer instructions."

## Lessons

### For CODE.md Enforcement

**Gap identified**: Developer instructions (CODE.md) not actively loaded for general agents doing Python work.

**Question**: Should CODE.md be loaded globally, or only for developer agent?

**Related issue**: #95 (code-review agent blocks on missing CODE.md)

### For Experiment Tracking

**Gap identified**: TRAINER.md mandates experiment tracking (lines 126-153) but:
- No experiments/ directory existed
- No index or template provided
- Trainer didn't reference tracking location when called out

**Fix implemented**:
- Created `bot/experiments/` directory
- Created `experiments/INDEX.md` master log
- Logged this failure as first experiment
- Created issue #118 for systemic tracking enforcement

### For Flat Architecture

**Still needed**: Define discovery mechanism without hardcoded paths or dual logic.

**Options to explore**:
1. Environment variables (WRITING_ROOT, BOT_ROOT)
2. Sentinel files (.writing-root markers)
3. Configuration file
4. Pure relative discovery (must work from any project)

**Decision pending**: User to specify golden path approach.

## Related Issues

- #114: Polyrepo architecture search inefficiency
- #118: Experiment tracking enforcement
- #95: CODE.md shadow file enforcement
- #111: Modular documentation (DRY principle)

## Modified Files

- `bot/scripts/validate_env.py` (changes rolled back, not committed)
- `bot/experiments/INDEX.md` (created)
- `bot/experiments/2025-10-17_validate-env-flat-arch.md` (this file)
