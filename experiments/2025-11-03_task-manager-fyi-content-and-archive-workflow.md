# Experiment: Task-Manager FYI Content Presentation and Archive Workflow

## Metadata

- Date: 2025-11-03
- Issue: #181
- Commit: 5df41bb2b0885204186d762e94eab3c97b3f6851
- Model: claude-sonnet-4-5

## Hypothesis

Adding explicit instructions for FYI content presentation and archive workflow will result in:

1. Agent presenting actual email content (subject, sender, summary) in FYI section, not just email titles
2. Agent proposing archives and waiting for user confirmation instead of executing immediately

## Problem

User feedback from `/email` invocation showed two issues:

1. **Missing FYI content**: Agent listed FYI emails by title only, didn't present actual information from emails
2. **Premature archival**: Agent may have attempted to archive tasks based on user statement without explicit confirmation of archive proposal

User quote: "You should also actually present me with the information for FYI things, don't just list the email."

## Changes Made

Modified `agents/task-manager.md` with 3 surgical edits:

### Edit 1: Enhanced FYI digest format (lines 62-70)

**Before**:

```markdown
- Note FYI emails (no action needed)
- Suggest emails to archive (optional)
```

**After**:

```markdown
- Present FYI emails with content:
  - Subject line
  - Sender
  - Key information/summary (2-3 sentences)
  - Why no action needed
- Propose emails to archive (request confirmation, DO NOT archive automatically)
```

### Edit 2: Added explicit digest example (new section ~187-211)

Added "Example 2: Digest Output Format" showing:

- Concrete FYI format with actual email summaries
- Archive recommendations with confirmation request
- Note emphasizing FYI content requirement

### Edit 3: Clarified archive workflow (new section ~170-178)

Added explicit two-step archive process:

1. Propose (in digest)
2. Wait for confirmation
3. Execute only after user approves

Added CRITICAL constraint: "NEVER archive emails automatically based on user statements like 'i'm not applying for DP27'. User must explicitly confirm the archive proposal."

## Anti-Bloat Assessment

- Enforcement hierarchy verified: Scripts/Hooks/Config cannot control digest output format (instruction-only territory)
- DRY check: No duplication of _CORE.md or other agent instructions
- Modularity: Content too specific to task-manager to extract
- Token cost: ~40 lines added (task-manager.md: 240→280 lines, under 500 limit)
- Justification: Output format specification requires instructions

## Success Criteria

**Primary metrics**:

1. FYI section includes email content summaries (subject + sender + 2-3 sentence summary + why no action)
2. Archive recommendations presented with explicit confirmation request
3. Agent waits for user "Y" or "yes" before executing archives

**Secondary metrics**:

- User doesn't need to ask "what was that email about?" after seeing digest
- No premature archival of tasks/emails
- Digest remains concise despite added content

## Test Plan

1. Invoke `/email` with mix of actionable and FYI emails
2. Verify FYI section shows email content, not just titles
3. Verify archive recommendations include "Confirm archive? (Y/N)"
4. Respond to agent without explicit "Y" confirmation (e.g., "archive the DP27 tasks")
5. Verify agent doesn't archive without explicit confirmation
6. Provide explicit "Y" confirmation
7. Verify agent then executes archives

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial - to be determined]

## Next Steps

If successful:

- Close #181
- Update #170 status
- Monitor for agent verbosity (too much FYI content)

If failure:

- Analyze why instructions weren't followed
- Consider moving to hook-based validation (archive confirmation check)
- Consider splitting digest formatting into separate skill

If partial:

- Iterate on instruction clarity
- Add more examples if needed
- Test with different email scenarios
