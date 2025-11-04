# Email Command: QUT Focus and Batch Archiving

## Metadata
- Date: 2025-11-04
- Issue: #181
- Commit: ee16822
- Model: claude-sonnet-4-5

## Hypothesis

Adding explicit workflow parameters to `/email` command will:
1. Focus task-manager on QUT account by default (reduce noise from personal newsletters)
2. Extend time window to 2-4 weeks (catch missed emails)
3. Improve FYI email presentation via category batching
4. Streamline inbox cleaning with batch archive proposals

## Changes Made

### File: `.claude/commands/email.md`
- Added "Workflow Parameters" section (22 lines)
- Specified default account: QUT (n.suzor@qut.edu.au)
- Changed time window: 2-4 weeks (was 24-48 hours)
- Added FYI batching strategy: Group by category, present summaries
- Added archive strategy: QUT only (personal account has folder issues)
- Updated task-manager workflow description to reflect new parameters

**Line count**:
- Before: 16 lines
- After: 36 lines
- Net change: +20 lines

**Token estimate**:
- Added content: ~100 tokens
- Context clarity gained: More focused queries, less iteration needed

## Success Criteria

**Primary metrics**:
- [ ] Task-manager defaults to QUT account emails (not all accounts)
- [ ] Retrieves emails from 2-4 week window (not just last 48 hours)
- [ ] Presents FYI emails grouped by category with summaries
- [ ] Proposes batch archives for QUT account only

**User experience**:
- [ ] Fewer irrelevant personal account newsletters in digest
- [ ] Catches older missed emails that need attention
- [ ] Easier to approve archive batches vs individual emails
- [ ] Cleaner inbox after `/email` command completes

**Efficiency**:
- [ ] Reduces back-and-forth clarifications about which account
- [ ] Decreases archive proposal noise (batches vs individuals)

## Results

[To be filled after testing]

**Test 1**: Run `/email` and observe:
- Which account(s) queried?
- Time range of emails retrieved?
- FYI email presentation format?
- Archive proposals (individual or batched)?

**Test 2**: User feedback on:
- Workflow improvement vs previous behavior
- Batch archiving usability
- Time window appropriateness

## Outcome

[To be determined: Success/Failure/Partial]

## Notes

**Design decision rationale**:
- Chose instructions over scripts/hooks/config because this is workflow customization, not behavior enforcement
- 20-line increase justified by token efficiency (reduces clarification rounds)
- Batch archiving addresses real pain point from testing (11 individual archive attempts)
- Time window extension addresses user's explicit request: "I frequently miss emails that are weeks old"

**Rollback plan**:
- If experiment fails: `git revert` to previous version
- Alternative: Move parameters to `.claude/settings.json` as static config
- Fallback: Consider script-based default account selection

**Related work**:
- Issue #181: Email workflow alignment
- Issue #170: Task-manager agent creation (complete)
