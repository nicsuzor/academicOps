---
title: Decision Briefing Workflow
type: instruction
category: instruction
permalink: workflow-decision-briefing
description: Generate user-facing briefing for tasks requiring approval or decision
---

# Workflow 8: Decision Briefing

**When**: User needs to review and make decisions on tasks blocking progress.

**Key principle**: Surface issues requiring human judgment with complete context so the user can make informed decisions quickly. Per AXIOMS #22 (Acceptance Criteria Own Success) - agents cannot make decisions that modify requirements or weaken criteria.

**CRITICAL**: This workflow generates briefings, not recommendations. Per categorical imperative, agents must not make subjective recommendations - instead provide structured consequence analysis for each option.

## Task Categories Requiring User Decision

| Category            | Detection Pattern                                | Decision Needed                |
| ------------------- | ------------------------------------------------ | ------------------------------ |
| **RFC**             | Title starts with "RFC:"                         | Approve/reject proposed change |
| **Blocked**         | Has dependencies shown in `get_blocked_tasks()`  | Prioritize resolution or defer |
| **Design Decision** | Body contains "Design decision needed"           | Choose implementation approach |
| **Experiment**      | Tag `experiment`, status `active`                | Direct next steps or complete  |
| **Investigation**   | Title contains "Investigate:"                    | Approve proposed solution      |

## Tasks MCP Commands

```python
mcp__plugin_aops-core_tasks__search_tasks(query="[query]")           # Search tasks
mcp__plugin_aops-core_tasks__get_blocked_tasks()                      # Tasks with unmet dependencies
mcp__plugin_aops-core_tasks__list_tasks(status="active")              # Filter by status
mcp__plugin_aops-core_tasks__complete_task(id="[ID]")                 # Complete task
mcp__plugin_aops-core_tasks__update_task(id="[ID]", status="waiting") # Defer for later
mcp__plugin_aops-core_tasks__update_task(id="[ID]", body="...")       # Add notes to task
```

## Workflow

### Phase 1: Gather Tasks Needing Decision

```python
# RFC tasks (awaiting approval)
mcp__plugin_aops-core_tasks__search_tasks(query="RFC")

# Tasks explicitly marked as needing approval
mcp__plugin_aops-core_tasks__search_tasks(query="approval")

# Blocked tasks (something is in the way)
mcp__plugin_aops-core_tasks__get_blocked_tasks()

# Experiments needing direction - search for experiment tag
mcp__plugin_aops-core_tasks__search_tasks(query="experiment")

# Investigations with proposed solutions
mcp__plugin_aops-core_tasks__search_tasks(query="Investigate")
```

**If ALL searches return empty**: Report "No tasks currently require decision" and exit workflow.

**If ANY search returns results**: Continue to Phase 2.

### Phase 2: Categorize and Deduplicate

Group tasks by decision type. A task may match multiple patterns - assign to highest-priority category:

**Priority order** (highest first):

1. **RFC** - Explicit approval requests
2. **Blocked** - Unblocking enables other work
3. **Investigation** - Has proposed solution
4. **Design Decision** - Needs approach choice
5. **Experiment** - Needs direction

If task appears in multiple searches, include only once under highest-priority category.

### Phase 3: Generate Briefing Document

For each task requiring decision, extract and structure:

1. **Task ID and Title** - From tasks MCP output
2. **Category** - From Phase 2 classification
3. **Summary** - First sentence of description, or agent-written one-liner
4. **Context** - What blocks this task / what this task blocks
5. **Options** - If multiple approaches in description, list them; otherwise "Approve / Reject / Defer"
6. **Consequence Matrix** - For each option: what happens if chosen (factual, not opinion)
7. **Dependent Tasks** - What gets unblocked if this is resolved

**Structure requirement**: Briefing must be actionable. User should be able to respond with just task ID and action.

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

```python
# For approved RFCs
task = mcp__plugin_aops-core_tasks__get_task(id="[ID]")  # Verify still active
mcp__plugin_aops-core_tasks__update_task(id="[ID]", body=task["body"] + "\n\nApproved by user [DATE]")
mcp__plugin_aops-core_tasks__complete_task(id="[ID]")
# Note: Implementation task creation is SEPARATE work, not part of this workflow

# For rejected RFCs
mcp__plugin_aops-core_tasks__update_task(id="[ID]", body="Rejected: [user-provided reason if any]", status="cancelled")

# For deferred items
mcp__plugin_aops-core_tasks__update_task(id="[ID]", status="waiting")

# For prioritization decisions - add note documenting decision
task = mcp__plugin_aops-core_tasks__get_task(id="[ID]")
mcp__plugin_aops-core_tasks__update_task(id="[ID]", body=task["body"] + "\n\nUser decision [DATE]: [decision text]")
```

**Error handling**: If any MCP call fails, report error and continue to next decision. Do not halt entire workflow for single failure.

**State verification**: Before executing each decision, verify task is still active. If already completed, skip and report.

## Acceptance Criteria for Briefing

A good briefing must:

- [ ] Include ALL active tasks matching decision patterns (verified via tasks MCP search)
- [ ] Deduplicate tasks appearing in multiple searches
- [ ] Provide enough context to decide without reading full issue
- [ ] Clearly separate categories with headers
- [ ] Show consequence matrix (not subjective recommendations)
- [ ] Show dependent issues for each decision
- [ ] Be under 4000 tokens (manageable in single view)
- [ ] Be actionable - user can respond with "approve ns-xyz, defer ns-abc"

## Empty State Handling

If no tasks need decision after all searches:

```markdown
# Decision Briefing: [DATE]

**No tasks currently require user decision.**

All RFCs have been processed, no blocked tasks, and no experiments need direction.

Next briefing recommended: [suggest when to check again based on project activity]
```

## Constraints

**DO ONE THING**: Generate briefing and capture decisions. Do NOT:

- Implement approved changes (that's separate work)
- Make subjective recommendations (provide consequence matrix instead)
- Close issues without explicit user instruction
- Create new issues as part of this workflow

**VERIFY-FIRST**:

- Verify task still needs decision before including in briefing
- Verify task still active before executing decision
- Check MCP call success before proceeding

## Example Session

```
User: Generate a decision briefing

Agent:
1. Runs Phase 1 searches
2. Finds: 3 RFCs, 2 blocked tasks, 1 experiment
3. Generates briefing document
4. Presents with AskUserQuestion

---
# Decision Briefing: 2026-01-12

**Total tasks requiring decision**: 6
**Categories**: 3 RFCs, 2 Blocked, 1 Experiment

## RFCs Awaiting Approval

### ns-p8n: RFC: Hydrator continuation detection
**Summary**: Add continuation detection to avoid invoking hydrator during ongoing dialogue
**Blocks**: ns-y8v (Hydrator Classification Failures epic)
**Options**:
- **Approve**: Creates implementation task, unblocks ns-y8v
- **Reject**: Task cancelled, hydrator behavior unchanged
- **Defer**: Remains active for future consideration

[... more tasks ...]
---

Agent: [Uses AskUserQuestion]
"Which decisions would you like to make? You can respond with multiple, e.g., 'approve ns-p8n, defer ns-0ct'"

User: approve ns-p8n, reject ns-0ct, defer ns-tme

Agent:
1. mcp__plugin_aops-core_tasks__get_task(id="ns-p8n") → still active ✓
2. mcp__plugin_aops-core_tasks__complete_task(id="ns-p8n")  # with approval note
3. mcp__plugin_aops-core_tasks__get_task(id="ns-0ct") → still active ✓
4. mcp__plugin_aops-core_tasks__update_task(id="ns-0ct", status="cancelled")
5. mcp__plugin_aops-core_tasks__update_task(id="ns-tme", status="waiting")

Reports: "Executed 3 decisions: ns-p8n approved, ns-0ct rejected, ns-tme deferred"
```

## Related Workflows

- [[07-learning-log.md]] - Creates issues that may need decision
- [[06-develop-specification.md]] - RFCs often result from spec development
- [[02-debug-framework-issue.md]] - Investigations may surface decision points
