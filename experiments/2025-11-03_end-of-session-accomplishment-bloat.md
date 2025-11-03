# Experiment: Fix end-of-session Agent Accomplishment Bloat

## Metadata
- **Date**: 2025-11-03
- **Issue**: #186 (end-of-session: Searches past sessions and captures too much detail)
- **Related Issues**: #152 (accomplishments.md bloat)
- **Commit**: TBD
- **Model**: claude-sonnet-4-5

## Hypothesis

Removing scribe skill invocation from end-of-session agent and replacing it with direct accomplishment evaluation will:
1. Eliminate searching past sessions (performance issue)
2. Apply "standup level" filter to only capture completed work
3. Write one-line entries instead of detailed summaries

## Problem

**User feedback**: "the end of session agent / skill isn't meant to go looking for stuff that other agents did in OTHER sessions. It's just meant as a reminder to 'save anything important (from what you just did!) that we need to remember nextime we're planning.' the stuff it's saving (a) takes too long to go find and isn't relevant; (b) is way too detailed (it's not an 'accomplishment' to send an email to josh)"

**Root causes**:
1. end-of-session invokes scribe skill (lines 59-68)
2. scribe has "continuous capture" instructions (searches past work)
3. No "accomplishment" filter applied (writes operational work)

**Impact**:
- Slow session end (searches past conversations)
- accomplishments.md polluted with operational work
- Violates DRY (duplicates information from current session)

## Changes Made

### 1. Updated end-of-session.md agent

**File**: `bot/agents/end-of-session.md`

**Key changes**:

1. **Removed scribe skill invocation** (old lines 59-68):
   - Deleted "Always invoke scribe skill" section
   - Removed scribe from integration section

2. **Added direct accomplishment evaluation** (new Section 2):
   - Accomplishment criteria from Issue #152
   - ✅ Completed work that creates value
   - ❌ Operational work (email, tasks, planning)
   - Test: "Did they deliver something or complete something?"

3. **Added format guidelines**:
   - One-line entries only
   - Format: `## YYYY-MM-DD - [Brief title]\n- [One sentence]`

4. **Updated examples** (Scenarios 1-4):
   - Show evaluation against criteria
   - Demonstrate operational work filtering
   - Show one-line format

5. **Updated constraints**:
   - DO: Evaluate work description, write one-line entries
   - DON'T: Search past sessions, capture operational work, invoke scribe

6. **Updated success criteria**:
   - Only writes for completed work
   - Doesn't search past sessions
   - One-line entries only

## Design Decisions

**Why remove scribe invocation?**
- Scribe instructions say "continuously capture" (searches history)
- end-of-session receives work description from calling agent
- Direct evaluation is faster and more accurate

**Why one-line format?**
- User feedback: "way too detailed"
- accomplishments.md is for morale/motivation, not documentation
- "Standup level" - what you'd mention in 30-second update

**Why "completed work that creates value"?**
- From Issue #152 analysis
- Filters out operational tasks (email, task creation)
- Focuses on deliverables and achievements

## Success Criteria

**Performance**:
- [ ] Completes within 30 seconds (no session searching)
- [ ] No tool calls except git operations

**Filtering**:
- [ ] Email processing → NO entry in accomplishments.md
- [ ] Task creation → NO entry in accomplishments.md
- [ ] Strategic planning → NO entry in accomplishments.md
- [ ] Feature implemented → ONE LINE in accomplishments.md
- [ ] Paper submitted → ONE LINE in accomplishments.md

**Format**:
- [ ] Entries are one line only
- [ ] Follow format: "## YYYY-MM-DD - [title]\n- [sentence]"
- [ ] No detailed summaries or bullet lists

## Test Plan

1. **Baseline**: Verify current behavior causes bloat
2. **Email processing test**: Invoke after email triage
   - Expected: No accomplishment entry
3. **Task creation test**: Invoke after creating tasks
   - Expected: No accomplishment entry
4. **Feature implementation test**: Invoke after completing hook
   - Expected: One-line entry "Implemented autocommit hook for task database"
5. **Strategic planning test**: Invoke after planning session
   - Expected: No accomplishment entry
6. **Performance test**: Measure completion time
   - Expected: < 10 seconds (no searching)

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial - to be determined]

## Follow-up Actions

- [ ] Test with real end-of-session invocations
- [ ] Monitor accomplishments.md for bloat over 1 week
- [ ] Update GitHub issue #186 with results
- [ ] Consider if same pattern needed for scribe skill (separate issue)
- [ ] Document pattern in best practices if successful

## Rollback Plan

If fix causes issues:
1. Edit `bot/agents/end-of-session.md`
2. Restore scribe skill invocation (lines 59-68 from previous version)
3. Commit rollback
4. Document failure reason in this experiment log
5. Consider alternative approaches (e.g., pass filter to scribe)
