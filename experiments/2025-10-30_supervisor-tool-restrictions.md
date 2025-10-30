# Supervisor Tool Restrictions Experiment

## Metadata
- Date: 2025-10-30
- Issue: #127
- Commit: 38debe1
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Restricting supervisor agent's tool access via configuration will force it to delegate implementation work to dev subagent instead of using Edit/Write directly, ensuring it follows its orchestration-only design.

## Problem Background

**Observed behavior:** Supervisor agent completed paths.toml reorganization task but:
- Made 11 Edit calls directly (modified files itself)
- Made 0 Task calls (no delegation to dev subagent)
- Violated its own instructions (SUPERVISOR.md:112-116: "Invoke dev subagent")

**Root cause:** No configuration restrictions on supervisor's tool access. Instructions said "delegate" but configuration allowed direct implementation.

**Evidence:** Execution log analysis (`agent-3242aeb7.jsonl`) showed:
- 80 total tool calls
- 11 Edit calls (direct implementation)
- 0 Task calls to dev subagent
- 1 Skill call (git-commit)

## Changes Made

Added subagent-specific permissions to `config/settings.json` (lines 17-37):

```json
"subagents": {
  "supervisor": {
    "permissions": {
      "allow": [
        "Task",
        "TodoWrite",
        "Skill",
        "Bash(git *)",
        "Bash(uv run pytest*)",
        "Read",
        "Grep",
        "Glob"
      ],
      "deny": [
        "Edit",
        "Write",
        "NotebookEdit"
      ]
    }
  }
}
```

**Enforcement:** Hard block at platform level - supervisor can no longer use Edit/Write/NotebookEdit.

## Success Criteria

1. **Delegation pattern:** Supervisor must invoke dev subagent (Task call) for implementation work
2. **Tool restriction:** Edit/Write attempts by supervisor fail with permission error
3. **Workflow compliance:** Supervisor follows SUPERVISOR.md instructions (delegate instead of implement)
4. **Task completion:** Multi-step tasks still complete successfully through proper delegation
5. **Log evidence:** Execution logs show Task calls to dev, no Edit calls from supervisor

**Measurement approach:**
- Assign supervisor a multi-file editing task
- Analyze execution log for tool call patterns
- Verify delegation to dev subagent occurred
- Confirm no Edit calls from supervisor

## Results

[To be filled after testing]

**Test scenario:**
- Task description: [describe test task]
- Expected: Supervisor delegates to dev subagent
- Actual: [observed behavior]

**Log analysis:**
- Supervisor tool calls: [summary]
- Dev subagent invoked: [yes/no]
- Edit calls from supervisor: [count]
- Permission errors: [any errors encountered]

## Outcome

[Success/Failure/Partial - to be filled after testing]

**Findings:**
- [What we learned about enforcement hierarchy]
- [Whether config restrictions work as expected]
- [Any unintended side effects]

**Decision:** [Keep/Revert/Iterate]

**Next Steps:** [If iteration needed]

## Notes

This experiment tests Enforcement Hierarchy principle: Configuration (Q3) should enforce architectural constraints that instructions (Q4) cannot reliably enforce.

Related experiments:
- Supervisor commit enforcement (#127 comment)
- Developer agent permission system (#93)
