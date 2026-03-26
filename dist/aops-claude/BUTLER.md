# Butler: Framework Coordination & Institutional Memory

The Butler is the **self-aware core** of academicOps. It ensures that every session, tool call, and decision aligns with the framework's long-term integrity and the researcher's intent.

## The Lightweight Hydrator (Skills Routing)

Instead of blocking gates and heavy context injection, the Butler provides **non-blocking skills-routing hints** via the `UserPromptSubmit` hook.

### Design Principles

1. **Non-blocking**: No gate, no `PreToolUse` hook, no blocking of any kind — ever.
2. **Minimal content**: Entries are added only when a specific, demonstrated failure justifies it.
3. **Measurement**: Each addition is tracked and measured over multiple sessions.
4. **Purpose**: Remind agents which skill/workflow is relevant for the work they are about to do.

### Routing Table

| If you are about to... | Relevant Skill | Why? |
| ---------------------- | -------------- | ---- |
| [Baseline state]       | -              | -    |

## Institutional Memory

The Butler owns the **strategic verification layer**. It is responsible for:

1. **Instruction Maintenance**: Fixing instructions at the source (`CORE.md`, `AXIOMS.md`, `SKILL.md`) when gaps are identified.
2. **Decision Briefing**: Ensuring that significant system observations are surfaced before being encoded as interpreted fact.
3. **Framework Governance**: Managing the evolution of the framework's axioms and heuristics.

## Verification Loop

"Edit landed" does NOT equal "problem solved." The Butler ensures that every system change follows the lifecycle:

1. **Land change**: Apply the fix/instruction.
2. **Verification**: Confirm the change actually prevents the targeted failure.
3. **Measurement**: Monitor effectiveness across multiple sessions.
4. **Pruning**: Remove instructions that do not demonstrably help.

## Contact

When in doubt about framework evolution or alignment, invoke the `/butler` skill.
