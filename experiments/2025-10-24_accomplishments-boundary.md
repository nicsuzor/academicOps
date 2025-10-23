# Experiment: Define Clear Boundaries for accomplishments.md

## Metadata
- **Date**: 2025-10-24
- **Issue**: #152
- **Commit**: 850a5fde953edf80d3c5e68e7d82a56a0235328d
- **Model**: claude-sonnet-4-5-20250929
- **Agent**: trainer / task-management skill

## Hypothesis

Adding explicit definition of "accomplishment" with positive/negative examples and concrete trigger conditions will prevent agents from writing operational work (email processing, task creation) to accomplishments.md while still capturing valid completed work.

## Problem Context

Agent was writing to accomplishments.md:
- Email processed (2,982 unread) - operational work ✗
- Tasks created (10 tasks added) - operational work ✗
- Meeting details and deadlines - reference material ✗

Instead of only:
- Meetings attended and completed ✓
- Deliverables submitted ✓
- Tasks archived ✓

## Changes Made

Modified `.claude/skills/task-management/SKILL.md` Step 6 (lines 284-350):

1. **Added "What is an Accomplishment?" section** (~24 lines):
   - Explicit definition: "completed work that creates value"
   - Positive examples (✅): task completed, meeting concluded, deliverable submitted
   - Negative examples (❌): email processed, task created, meeting scheduled
   - Test question: "Did I deliver or complete something?"

2. **Replaced vague trigger language** (~10 lines):
   - OLD: "Throughout conversation, silently capture... Progress updates"
   - NEW: "ONLY when: User explicitly mentions completing work, task archived, deliverable shipped"

3. **Added explicit data boundary rule** (~15 lines):
   - Task System = operational tracking (created, updated, queued)
   - Accomplishments = completed value only
   - Rule: "If it's not complete, it's not an accomplishment"

4. **Updated Critical Rules** section (lines 513-531):
   - NEVER: "Write operational work to accomplishments.md"
   - ALWAYS: "Ask 'Did they deliver or complete something?' before writing to accomplishments.md"

**Total addition**: ~49 lines (within acceptable range, file now ~570 lines)

## Success Criteria

**Negative tests** (should NOT write to accomplishments.md):
- [ ] Agent processes emails → No write to accomplishments.md
- [ ] Agent creates tasks → No write to accomplishments.md
- [ ] Agent schedules meeting → No write to accomplishments.md
- [ ] Agent does planning work → No write to accomplishments.md

**Positive tests** (SHOULD write to accomplishments.md):
- [ ] User says "I delivered the keynote" → Write to accomplishments.md
- [ ] Agent archives task when user says "I finished X" → Write to accomplishments.md
- [ ] User reports "meeting went well, we decided Y" → Write to accomplishments.md
- [ ] User says "I submitted the paper" → Write to accomplishments.md

**Quality metrics**:
- Zero invalid entries in accomplishments.md over 1 week
- User does NOT complain about "random stuff" in accomplishments.md
- Valid accomplishments still captured (no false negatives reported)

## Results

(To be filled after testing in real conversations)

### Test 1: Email Processing
- Date:
- Scenario:
- Outcome:

### Test 2: Task Creation
- Date:
- Scenario:
- Outcome:

### Test 3: Completed Work
- Date:
- Scenario:
- Outcome:

## Outcome

(To be marked after 1 week evaluation)

Options:
- **Success**: Zero invalid entries, valid entries still captured
- **Failure**: Still writes operational work OR misses valid accomplishments
- **Partial**: Improvement but edge cases remain

## Next Steps

(To be determined based on outcome)

If Partial:
- Consider adding "completion verb" list (delivered, shipped, submitted, finished)
- Add "when in doubt, don't write" fallback
- Consider building examples pattern matching

If Failure:
- Revert changes
- Explore hook-based solution (warning before write)
- Consider separate accomplishments skill
