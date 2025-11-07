# Experiment: Scribe Detail Level Balance

## Metadata

- Date: 2025-10-30
- Issue: #152
- Commit: c2042b5
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Adding explicit "Detail Level Guidelines" to scribe skill will prevent:

1. Over-detailed accomplishments entries (already partially fixed in #152)
2. Under-detailed project file entries (NEW problem identified today)

Expected behavior:

- Accomplishments: One-line "standup level" summaries
- Project files: "Resumption context level" with decisions, next steps, references

## Changes Made

Modified `/home/nic/.claude/skills/scribe/SKILL.md`:

1. **Added "Detail Level Guidelines" section** (~35 lines) after line 249:
   - Accomplishments: "Weekly standup level" with examples
   - Project files: "Resumption context level" with examples
   - Goals files: "Theory of change level"
   - Balance principle explaining why (daily growth vs per-project growth)
   - Two tests: "30-second standup?" and "Resume in 2 weeks?"

2. **Updated Critical Rules** (lines 403-424):
   - NEVER: "Write implementation details to accomplishments"
   - NEVER: "Write bare one-liners to project files"
   - ALWAYS: "Match detail level to file type"

## Success Criteria

**Accomplishments.md**:

- ✅ One line per item (unless significant strategic decision)
- ✅ Result + brief impact only
- ✅ NO implementation details (line counts, technical specifics)
- Test: "Would I say this in 30-second standup?"

**Project files**:

- ✅ Enough detail to resume work after 2-week gap
- ✅ Key decisions and WHY
- ✅ Next steps or open questions
- ✅ References to detailed docs if they exist
- Test: "Can I resume work from this in 2 weeks?"

**Negative tests**:

- ❌ Accomplishments should NOT have: "Reduced from 132 lines to 52 lines (60% reduction), eliminated ALL mocking..."
- ❌ Project files should NOT have: Just "TJA scorer validation - SUCCESS" with no context

**Positive tests**:

- ✅ Accomplishments: "TJA scorer validation - STRONG SUCCESS (88.9% accuracy, 9.7% FN rate, exceeds targets)"
- ✅ Project file: "Scorer validation experiment (scorer_validation_v1 vs BASELINE) achieved 88.9% accuracy. Validates redesigned QualScore scorer. Ready for production deployment. See tja/docs/SCORER_VALIDATION_EXPERIMENT.md"

## Evaluation Period

1 week of real usage

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial - to be determined]

## Notes

- This builds on #152 which fixed "what belongs in accomplishments"
- #152 focused on CATEGORY (accomplishments vs operational work)
- This experiment focuses on DETAIL LEVEL within each category
- User feedback came from diff showing inverse problem: accomplishments fixed but project files too brief
