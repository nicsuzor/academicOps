# Decision Briefing Detailed Procedures

Detailed procedures, categories, and examples for generating decision briefings.

## Task Categories Requiring User Decision

| Category            | Detection Pattern                               | Decision Needed                |
| ------------------- | ----------------------------------------------- | ------------------------------ |
| **RFC**             | Title starts with "RFC:"                        | Approve/reject proposed change |
| **Blocked**         | Has dependencies shown in `get_blocked_tasks()` | Prioritize resolution or defer |
| **Design Decision** | Body contains "Design decision needed"          | Choose implementation approach |
| **Experiment**      | Tag `experiment`, status `active`               | Direct next steps or complete  |
| **Investigation**   | Title contains "Investigate:"                   | Approve proposed solution      |

## Detailed Workflow Phases

### Phase 1: Gather Tasks Needing Decision

Search for "RFC", "approval", "experiment", "Investigate", and use `get_blocked_tasks()`. If no results, report and exit.

### Phase 2: Categorize and Deduplicate

Group tasks by priority: RFC > Blocked > Investigation > Design Decision > Experiment. Deduplicate tasks appearing in multiple categories.

### Phase 3: Generate Briefing Document

Extract Task ID, Title, Category, Summary, Context, Options, Consequence Matrix, and Dependent Tasks. Ensure the briefing is actionable and structured for batch input.

### Phase 4: Present to User

Format as a structured briefing with categories and headers. Use `AskUserQuestion` with multi-select for batch decisions.

### Phase 5: Execute Decisions

Parse user response and execute decisions (approve, reject, defer, prioritize) one by one with verification and error handling.

## Consequence Matrix Requirements

For each option, provide a factual (not subjective) analysis of the consequences. For example:

- **Approve**: "Creates implementation task, unblocks ns-y8v."
- **Reject**: "Task cancelled, hydrator behavior unchanged."
- **Defer**: "Remains active for future consideration."

## Example Briefing Format

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

- **Approve**: [consequence]
- **Reject**: [consequence]
- **Defer**: [consequence]

[... other categories ...]
```

## Example Session

1. **Agent** runs searches and finds 6 tasks.
2. **Agent** generates and presents briefing.
3. **User** responds: "approve ns-p8n, reject ns-0ct, defer ns-tme".
4. **Agent** verifies tasks are still active and executes decisions via MCP calls.
5. **Agent** reports results: "Executed 3 decisions: ns-p8n approved, ns-0ct rejected, ns-tme deferred".
