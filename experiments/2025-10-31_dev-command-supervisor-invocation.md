# /dev Command: Invoke Supervisor Agent

## Metadata
- Date: 2025-10-31
- Issue: #179
- Commit: [pending]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Changing `/dev` command from invoking the `dev` skill to invoking the `supervisor` agent will provide better structured development workflow through proper orchestration and delegation, resulting in improved TDD discipline and quality outcomes.

## Changes Made

Modified `commands/dev.md` (line 48):

**Before**:
```markdown
Invoke the `dev` skill for systematic development workflow with comprehensive capability guides.
```

**After**:
```markdown
Invoke the `supervisor` agent to orchestrate development work through structured TDD workflow with proper delegation to specialized subagents (Explore, Plan, dev).

The supervisor will:
- Take full responsibility for the development task
- Enforce test-driven development discipline
- Delegate exploration and planning to specialized agents
- Tightly control developer subagent through atomic steps
- Ensure quality gates at each stage
- Handle test failures through iteration
- Manage commits via git-commit skill validation
```

**Architectural change**:
- From: Slash command loads skill into current agent (all-in-one pattern)
- To: Slash command invokes dedicated orchestrator agent (multi-agent pattern)

**Key differences**:
1. **Responsibility**: Supervisor owns entire task vs current agent juggling everything
2. **Delegation**: Supervisor delegates to Plan, Explore, dev vs current agent doing all
3. **Workflow enforcement**: Supervisor enforces TDD gates vs current agent following suggestions
4. **Iteration**: Supervisor handles test failures automatically vs current agent needing guidance
5. **Quality gates**: Supervisor requires git-commit skill validation vs current agent skipping

## Success Criteria

1. `/dev` command invokes supervisor agent successfully
2. Supervisor takes ownership of development task (evident in agent behavior)
3. Supervisor delegates to specialized subagents:
   - Plan agent for breaking down tasks
   - Explore agent for codebase understanding
   - dev agent for implementation
4. TDD workflow enforced through orchestration:
   - Test created first
   - Minimal implementation
   - Quality check via git-commit skill
   - Iteration on failures
5. User receives structured, disciplined development workflow
6. Improved outcomes vs direct dev skill invocation:
   - Fewer test failures at completion
   - Better adherence to fail-fast principles
   - Atomic commits with proper validation

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial]

## Notes

This aligns with Issue #135 (slash commands and subagents architecture) by establishing pattern: slash commands should invoke orchestrator agents for complex workflows, not load skills directly.
