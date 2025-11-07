# Experiment: Multi-Stage Quality-Gated Supervisor Agent

**Date**: 2025-10-29 **Commit**: [pending] **Issue**: #127 (SUPERVISOR agent for orchestrating multi-agent workflows) **Agent**: New SUPERVISOR agent with comprehensive quality gates **Environment**: Design and implementation phase **Model**: Sonnet 4.5

## Hypothesis

A multi-stage supervisor agent with explicit quality gates at each phase will:

1. Ensure higher reliability through test-first micro-iterations
2. Prevent scope drift through continuous plan reconciliation
3. Detect infrastructure gaps (missing/buggy agents) and log them systematically
4. Eliminate "declare victory with failing tests" pattern via NO EXCUSES enforcement
5. Achieve higher quality through mandatory independent review at each stage

## User Requirements

User requested supervisor that:

1. ✅ Calls planning agent first to create detailed plan
2. ✅ Calls review agent to validate plan before execution
3. ✅ Chunks work into very small components (micro-tasks)
4. ✅ Ensures testing agent creates ONE failing test first (test-first)
5. ✅ One tiny change at a time via subagents
6. ✅ Calls review subagent after each change
7. ✅ Calls test validation subagent to verify tests pass
8. ✅ Calls code quality agent/skill to review and commit each change
9. ✅ Iterates with plan updates and scope drift checking
10. ✅ Logs errors via aops-bug skill when:
    - Subagent missing (with suggestion for creation)
    - Agent buggy/inefficient
    - Going in circles/thrashing
11. ✅ Enforces best practices and helps improve agent ecosystem

## Research Foundation

Based on 2025 LLM orchestration research:

**Patterns integrated**:

- **Checklist-based supervision** (AutoGen, CrewAI): TodoWrite for success criteria and micro-tasks
- **Validation layers** (ScenGen): Independent plan review before execution
- **Evaluation-driven development**: Inspired by TDD but for LLM agent workflows
- **Supervisor consistency checking**: Validates against completion targets throughout
- **Multi-agent delegation patterns** (LangGraph): Structured agent invocation with context flow

**Key insight applied**:

> "Even with RAG and schema enforcement, LLM agents can go astray, which is why real-time validation is essential."

This informed the iteration gate (Stage 3) with scope drift and thrashing detection.

## Implementation

### File Created: `agents/SUPERVISOR.md`

**Line count**: 424 lines

**Anti-Bloat Analysis**:

- **Target**: <250 lines (from solution design)
- **Actual**: 424 lines
- **Justification**: Complex orchestration logic inherent to supervisor responsibility
  - Multi-stage workflow: ~200 lines (core orchestration - cannot simplify)
  - Self-monitoring protocols: ~40 lines (required for infrastructure gap detection)
  - Quality gate checklists: ~30 lines (essential validation)
  - Example workflow: ~40 lines (demonstrates proper usage)
  - Remaining: ~114 lines (purpose, principles, available agents, anti-patterns)
- **Compliance**: Under 500 line hard cap
- **DRY**: References _CORE.md for NO EXCUSES (no duplication)
- **Modularity**: References existing skills (aops-bug, git-commit, test-writing)

**Note**: If supervisor proves too complex in practice, consider extracting stage details to separate referenced docs (e.g., `docs/SUPERVISOR-STAGES.md`). Test first, optimize later.

### Architecture

**4-Stage Workflow**:

```
Stage 0: Planning Phase
├─ Success checklist creation (REQUIRED FIRST)
├─ Detailed plan creation via Plan subagent
├─ Independent plan review via second subagent
└─ Micro-task breakdown in TodoWrite

Stage 1: Test-First Phase (per micro-task)
├─ ONE failing test via test-writing skill
├─ Verify test fails correctly
└─ Update plan if complexity discovered

Stage 2: Implementation Phase (per micro-task)
├─ MINIMUM code change via dev subagent
├─ Independent review via code-review
├─ Validate tests pass
└─ Atomic commit via git-commit skill

Stage 3: Iteration Gate
├─ Mark micro-task complete
├─ Plan reconciliation
├─ Scope drift detection (>20% = STOP)
├─ Thrashing detection (same file 3+ times = STOP)
└─ Next micro-task or completion

Stage 4: Completion
├─ Verify ALL success criteria with evidence
├─ Demonstrate working result NOW
└─ NO EXCUSES - no rationalization
```

**Self-Monitoring Capabilities**:

- Missing agent detection → log via aops-bug with suggestion
- Buggy agent detection (0 tokens 2+ times) → log performance issue
- Thrashing detection (same file 3+ modifications) → STOP and log
- Scope drift detection (>20% growth) → STOP and ask user
- 0-token recovery protocol (retry once, switch approach, or fail explicitly)

### Integration Points

**Skills**:

- `aops-bug`: Infrastructure gap reporting
- `git-commit`: Code quality validation and atomic commits
- `test-writing`: TDD test creation

**Subagents**:

- `Plan`: Planning and plan review
- `Explore`: Codebase understanding
- `dev`: Implementation
- Code-review invoked via git-commit skill

**Compliance**:

- Axiom #1 exception: Explicit DO ONE THING exception for orchestration
- Axiom #4: References _CORE.md for NO EXCUSES enforcement
- Axiom #7: Fail-fast on scope drift, thrashing, missing infrastructure
- Axiom #15: Write for long term - atomic commits, tested, reviewed

## Success Criteria

**For this implementation phase**:

- [x] SUPERVISOR.md created with all required stages
- [x] Self-monitoring protocols documented
- [x] Multi-agent request parsing included (from #126)
- [x] NO EXCUSES enforcement with reference to _CORE.md
- [x] Quality gate checklists defined
- [x] Example workflow provided
- [ ] Experiment log created (this file)
- [ ] INSTRUCTION-INDEX.md updated
- [ ] Changes committed with reference to #127
- [ ] User validation received

**For future testing phase**:

- Supervisor successfully completes complex task following all stages
- Zero regressions introduced (all tests pass)
- Scope drift detected and handled appropriately
- Infrastructure gaps logged via aops-bug when encountered
- Success criteria verified with evidence (no claims without demonstration)
- Working demo provided at completion

## Experiment Plan

**Phase 1: Design & Implementation** (CURRENT)

- Create SUPERVISOR.md based on research and user requirements
- Document in experiment log
- Commit and track in #127

**Phase 2: Initial Testing** (NEXT)

- User invokes supervisor on real complex task
- Monitor adherence to stages
- Track scope drift, thrashing, quality gate violations
- Measure: task completion, test pass rate, commits quality

**Phase 3: Iteration** (FUTURE)

- Refine based on real-world usage
- Extract stages to separate docs if bloat becomes issue
- Add validation hooks if violations occur repeatedly
- Consider automated experiment tracking

## Evaluation Metrics

**Reliability**:

- Test pass rate at completion (target: 100%)
- Regressions introduced (target: 0)
- Success criteria verification rate (target: 100%)

**Quality**:

- Code review pass rate (target: 100%)
- Commits following fail-fast principles (target: 100%)
- Atomic commits (one micro-task per commit)

**Process Adherence**:

- Planning phase completion before execution (target: 100%)
- Test-first followed (target: 100%)
- Independent review performed (target: 100%)
- Plan reconciliation at each iteration (target: 100%)

**Self-Monitoring**:

- Scope drift detections vs actual drifts
- Thrashing detections vs actual thrashing
- Infrastructure gaps logged
- 0-token failures handled appropriately

**Efficiency**:

- Overhead of multi-stage process vs value delivered
- Time to complete vs quality improvement
- User intervention required (target: minimal)

## Risks & Mitigations

**Risk**: Supervisor too complex, becomes unwieldy in practice **Mitigation**: Monitor usage, extract stages to referenced docs if needed **Status**: To be evaluated in Phase 2

**Risk**: Orchestration overhead slows down simple tasks **Mitigation**: Document when to use Supervisor (complex tasks) vs direct agent **Status**: Documented in Purpose & Authority section

**Risk**: Supervisor itself violates anti-bloat at 424 lines **Mitigation**: References existing docs, hard cap at 500 lines, can extract later **Status**: Within limits, monitor for actual bloat in practice

**Risk**: Multi-agent coordination fails on API timeouts **Mitigation**: 0-token recovery protocol (retry, switch, fail explicitly) **Status**: Protocol documented, to be tested

## Related Experiments

- `2025-10-19_supervisor-testcleaner-chain.md`: Original supervisor test (91% success)
- `2025-10-19_supervisor-no-excuses-violation.md`: NO EXCUSES violation and fix
- `2025-10-22_supervisor-never-declare-success-with-failing-tests.md`: Success criteria enforcement

## Next Steps

1. Update INSTRUCTION-INDEX.md with SUPERVISOR.md entry
2. Commit changes with reference to #127
3. Post implementation summary to #127
4. Get user validation
5. Phase 2: Test on real complex task
6. Refine based on real-world results

## Notes

**Design Decisions**:

- Success checklist REQUIRED FIRST to prevent retroactive rationalization
- Micro-tasks keep changes small and testable
- Independent review at each stage prevents accumulation of technical debt
- Plan reconciliation prevents scope creep
- Self-monitoring makes supervisor responsible for framework health

**Alignment with academicOps Philosophy**:

- Test-driven development mandatory
- Fail-fast (stop on scope drift, thrashing, infrastructure gaps)
- Self-documenting (each commit atomic and clear)
- Explicit (no defaults, no guessing)
- Long-term focused (atomic commits, proper tests, quality gates)

**Lessons from Previous Experiments**:

- NO EXCUSES critical - supervisor tried to claim success without verification (#2025-10-19)
- Success checklist prevents rationalization
- 0-token failures need explicit handling
- Code-review must be enforced (was skipped in #2025-10-19)
- Plan review prevents bad plans from becoming bad implementations
