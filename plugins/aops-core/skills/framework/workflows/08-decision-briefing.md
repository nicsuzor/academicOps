---
title: Decision Briefing Workflow
type: instruction
category: instruction
permalink: workflow-decision-briefing
description: Generate user-facing briefing for bd issues requiring approval or decision
---

# Workflow 8: Decision Briefing

**When**: User needs to review and make decisions on bd issues blocking progress.

**Key principle**: Surface issues requiring human judgment with complete context so the user can make informed decisions quickly. Per AXIOMS #22 (Acceptance Criteria Own Success) - agents cannot make decisions that modify requirements or weaken criteria.

**CRITICAL**: This workflow generates briefings, not recommendations. Per categorical imperative, agents must not make subjective recommendations - instead provide structured consequence analysis for each option.

## Issue Categories Requiring User Decision

| Category            | Detection Pattern                             | Decision Needed                |
| ------------------- | --------------------------------------------- | ------------------------------ |
| **RFC**             | Title starts with "RFC:"                      | Approve/reject proposed change |
| **Blocked**         | Has dependencies shown in `bd blocked` output | Prioritize resolution or defer |
| **Design Decision** | Description contains "Design decision needed" | Choose implementation approach |
| **Experiment**      | Label `experiment`, status `open`             | Direct next steps or close     |
| **Investigation**   | Title contains "Investigate:"                 | Approve proposed solution      |

## Verified bd Commands

These commands are confirmed to work (verified 2026-01-12):

```bash
bd search "[query]" --status open --json    # Searches title, description, ID
bd blocked --json                            # Shows issues with unmet dependencies
bd list --label [label] --status open --json # Filter by label
bd close [ID] --reason "[text]"              # Close with reason
bd defer [ID]                                # Defer for later
bd comments add [ID] "[text]"                # Add comment to issue
```

## Workflow

### Phase 1: Gather Issues Needing Decision

```bash
# RFC issues (awaiting approval)
bd search "RFC" --status open --json

# Issues explicitly marked as needing approval
bd search "approval" --status open --json

# Blocked issues (something is in the way)
bd blocked --json

# Experiments needing direction
bd list --label experiment --status open --json

# Investigations with proposed solutions
bd search "Investigate" --status open --json
```

**If ALL searches return empty**: Report "No issues currently require decision" and exit workflow.

**If ANY search returns results**: Continue to Phase 2.

### Phase 2: Categorize and Deduplicate

Group issues by decision type. An issue may match multiple patterns - assign to highest-priority category:

**Priority order** (highest first):

1. **RFC** - Explicit approval requests
2. **Blocked** - Unblocking enables other work
3. **Investigation** - Has proposed solution
4. **Design Decision** - Needs approach choice
5. **Experiment** - Needs direction

If issue appears in multiple searches, include only once under highest-priority category.

### Phase 3: Generate Briefing Document

For each issue requiring decision, extract and structure:

1. **Issue ID and Title** - From bd output
2. **Category** - From Phase 2 classification
3. **Summary** - First sentence of description, or agent-written one-liner
4. **Context** - What blocks this issue / what this issue blocks
5. **Options** - If multiple approaches in description, list them; otherwise "Approve / Reject / Defer"
6. **Consequence Matrix** - For each option: what happens if chosen (factual, not opinion)
7. **Dependent Issues** - What gets unblocked if this is resolved

**Structure requirement**: Briefing must be actionable. User should be able to respond with just issue ID and action.

### Phase 4: Present to User

Format as structured briefing with AskUserQuestion for batch input:

```markdown
# Decision Briefing: [DATE]

**Total issues requiring decision**: N
**Categories**: X RFCs, Y Blocked, Z Others

---

## RFCs Awaiting Approval (N issues)

### ns-xyz: [Title]

**Summary**: [one sentence from description]
**Blocks**: [dependent issues, or "nothing currently"]
**Options**:

- **Approve**: [consequence - what happens next]
- **Reject**: [consequence - issue closed, no implementation]
- **Defer**: [consequence - remains open, revisit later]

---

## Blocked Issues (N issues)

### ns-abc: [Title]

**Summary**: [one sentence]
**Blocked by**: [list issue IDs with titles]
**Unblocks**: [what becomes ready if resolved]
**Options**:

- **Prioritize blocker [ID]**: [work on blocker first]
- **Defer this issue**: [wait for blocker resolution naturally]
- **Remove dependency**: [if dependency is incorrect]

---

## Other Decisions (N issues)

### ns-def: [Title]

**Summary**: [one sentence]
**Options**: [list specific options from issue]
**Consequences**: [for each option]
```

Then use AskUserQuestion with multiSelect to capture batch decisions.

### Phase 5: Execute Decisions

Parse user response and execute. Handle one decision at a time with verification:

```bash
# For approved RFCs
bd show [ID]  # Verify still open
bd close [ID] --reason "Approved by user [DATE]"
# Note: Implementation task creation is SEPARATE work, not part of this workflow

# For rejected RFCs
bd close [ID] --reason "Rejected: [user-provided reason if any]"

# For deferred items
bd defer [ID]

# For prioritization decisions - add comment documenting decision
bd comments add [ID] "User decision [DATE]: [decision text]"
```

**Error handling**: If any bd command fails, report error and continue to next decision. Do not halt entire workflow for single failure.

**State verification**: Before executing each decision, verify issue is still open. If already closed, skip and report.

## Acceptance Criteria for Briefing

A good briefing must:

- [ ] Include ALL open issues matching decision patterns (verified via bd search)
- [ ] Deduplicate issues appearing in multiple searches
- [ ] Provide enough context to decide without reading full issue
- [ ] Clearly separate categories with headers
- [ ] Show consequence matrix (not subjective recommendations)
- [ ] Show dependent issues for each decision
- [ ] Be under 4000 tokens (manageable in single view)
- [ ] Be actionable - user can respond with "approve ns-xyz, defer ns-abc"

## Empty State Handling

If no issues need decision after all searches:

```markdown
# Decision Briefing: [DATE]

**No issues currently require user decision.**

All RFCs have been processed, no blocked issues, and no experiments need direction.

Next briefing recommended: [suggest when to check again based on project activity]
```

## Constraints

**DO ONE THING**: Generate briefing and capture decisions. Do NOT:

- Implement approved changes (that's separate work)
- Make subjective recommendations (provide consequence matrix instead)
- Close issues without explicit user instruction
- Create new issues as part of this workflow

**VERIFY-FIRST**:

- Verify issue still needs decision before including in briefing
- Verify issue still open before executing decision
- Check bd command success before proceeding

## Example Session

```
User: Generate a decision briefing

Agent:
1. Runs Phase 1 searches
2. Finds: 3 RFCs, 2 blocked issues, 1 experiment
3. Generates briefing document
4. Presents with AskUserQuestion

---
# Decision Briefing: 2026-01-12

**Total issues requiring decision**: 6
**Categories**: 3 RFCs, 2 Blocked, 1 Experiment

## RFCs Awaiting Approval

### ns-p8n: RFC: Hydrator continuation detection
**Summary**: Add continuation detection to avoid invoking hydrator during ongoing dialogue
**Blocks**: ns-y8v (Hydrator Classification Failures epic)
**Options**:
- **Approve**: Creates implementation task, unblocks ns-y8v
- **Reject**: Issue closed, hydrator behavior unchanged
- **Defer**: Remains open for future consideration

[... more issues ...]
---

Agent: [Uses AskUserQuestion]
"Which decisions would you like to make? You can respond with multiple, e.g., 'approve ns-p8n, defer ns-0ct'"

User: approve ns-p8n, reject ns-0ct, defer ns-tme

Agent:
1. bd show ns-p8n → still open ✓
2. bd close ns-p8n --reason "Approved by user 2026-01-12"
3. bd show ns-0ct → still open ✓
4. bd close ns-0ct --reason "Rejected by user"
5. bd defer ns-tme

Reports: "Executed 3 decisions: ns-p8n approved, ns-0ct rejected, ns-tme deferred"
```

## Related Workflows

- [[07-learning-log.md]] - Creates issues that may need decision
- [[06-develop-specification.md]] - RFCs often result from spec development
- [[02-debug-framework-issue.md]] - Investigations may surface decision points
