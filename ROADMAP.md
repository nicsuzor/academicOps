# Automation Framework Roadmap

**Last updated**: 2025-11-11 (Week 1 Audit)

## Maturity Progression Model

How we move from manual chaos to sophisticated automation, one validated step at a time.

## Stage 0: Manual Chaos (Pre-Automation)

**Characteristics**:

- Everything done by hand
- Ad-hoc processes, inconsistent quality
- Knowledge in Nic's head only
- Difficult to reproduce or delegate

**Goal**: Document what we actually do

**Exit criteria**:

- [ ] Core workflows documented (research, writing, task management)
- [ ] Pain points identified and prioritized
- [ ] Success criteria defined for each workflow

## Stage 1: Documented Workflows (Current Foundation)

**Characteristics**:

- Processes documented in markdown
- Principles codified (AXIOMS.md, CORE.md)
- Quality standards explicit
- Single source of truth established

**Goal**: Make implicit knowledge explicit

**Current state**: Largely complete

- ✅ Core principles in AXIOMS.md
- ✅ Work style in ACCOMMODATIONS.md
- ✅ Writing style in STYLE.md
- ✅ Framework maintenance in framework/SKILL.md
- ✅ Experiment tracking in place

**Next**: Identify first automation targets

**Exit criteria**:

- [ ] All regular workflows documented
- [ ] Pain points ranked by impact and automation difficulty
- [ ] First automation candidates selected

## Stage 2: Scripted Tasks (Targeted Automation)

**Characteristics**:

- Individual tasks automated with scripts
- Each script handles one specific job
- Integration tests validate each script
- Scripts work independently (no orchestration yet)

**Goal**: Automate high-impact, low-complexity tasks first

**Priority automation targets**:

1. **Research Data Quality** (High impact, Medium complexity)
   - Automated data validation and cleaning checks
   - Statistical assumption validation
   - Reproducibility verification
   - Success metric: Zero manual quality checks needed

2. **Task Capture and Filing** (High impact, Low complexity)
   - Voice/text dump auto-categorization to projects
   - Smart inbox triage
   - Deadline extraction and scheduling
   - Success metric: Zero manual filing needed

3. **Citation and Reference Management** (Medium impact, Medium complexity)
   - Auto-formatting citations in Nic's style
   - Reference completeness checking
   - Cross-reference validation
   - Success metric: Zero manual citation formatting

4. **Writing Style Consistency** (Medium impact, Low complexity)
   - Automated style checking against STYLE.md
   - Voice consistency validation
   - Structural template enforcement
   - Success metric: Drafts match style guide on first pass

**Development pattern for each**:

1. Create task spec from TASK-SPEC-TEMPLATE.md
2. Design integration test first (must fail initially)
3. Implement minimum viable automation
4. Test until passes
5. Document in experiment log
6. Deploy and monitor

**Exit criteria**:

- [ ] Top 5 pain points automated with passing tests
- [ ] Each automation reduces manual work by >50%
- [ ] Reliability >95% (automation works without intervention)

## Stage 3: Integrated Pipelines (Workflow Automation)

**Characteristics**:

- Individual scripts chain together
- Complete workflows automated end-to-end
- State management across pipeline stages
- Error handling and recovery automated

**Goal**: Automate complete workflows, not just tasks

**Target pipelines**:

1. **Research Analysis Pipeline**
   - Raw data → Cleaned data → Analysis → Visualization → Results doc
   - Automated quality gates at each stage
   - One-command reproducibility
   - Success metric: Data to draft in <1 day with minimal input

2. **Paper Writing Pipeline**
   - Research questions → Literature review → Methods → Results → Discussion
   - Template-driven structure with auto-population
   - Citation and reference auto-management
   - Success metric: First draft from analysis in <1 week

3. **Task Management Pipeline**
   - Capture → Categorize → Prioritize → Schedule → Track → Complete
   - Cross-device sync and consistency
   - Proactive surfacing based on context
   - Success metric: Zero tasks lost or forgotten

**Development pattern**:

1. Map workflow stages and handoffs
2. Identify state requirements and data flow
3. Design pipeline tests (end-to-end scenarios)
4. Build orchestration layer
5. Test complete workflows
6. Monitor and refine

**Exit criteria**:

- [ ] Top 3 workflows fully automated end-to-end
- [ ] Pipeline reliability >90%
- [ ] Manual intervention only for substantive decisions
- [ ] State management robust across interruptions

## Stage 4: Adaptive Systems (Intelligent Automation)

**Characteristics**:

- Systems make tactical decisions autonomously
- Learning from usage patterns
- Context-aware automation (adapts to situation)
- Proactive error detection and recovery

**Goal**: Reduce cognitive load through intelligent defaults and decisions

**Target capabilities**:

1. **Smart Task Triage**
   - Learn priority patterns from Nic's decisions
   - Auto-prioritize based on context (deadline, dependencies, strategic value)
   - Surface right tasks at right time
   - Success metric: >80% priority suggestions accepted

2. **Adaptive Writing Assistance**
   - Learn structure patterns from past papers
   - Suggest relevant citations from reading context
   - Auto-adjust detail level based on audience
   - Success metric: >70% writing suggestions accepted

3. **Intelligent Quality Control**
   - Learn what "good enough" means from feedback
   - Adjust validation strictness by context
   - Predict likely issues before they occur
   - Success metric: Catch 90% of issues before manual review

**Development pattern**:

1. Collect baseline data from Stage 3 pipelines
2. Identify decision patterns
3. Build prediction/classification models
4. A/B test against rule-based approaches
5. Monitor and retrain

**Exit criteria**:

- [ ] 3+ adaptive systems deployed and improving
- [ ] Acceptance rate >75% for automated decisions
- [ ] False positive rate <10%
- [ ] Measurable reduction in cognitive load

## Stage 5: Proactive Assistance (Anticipatory Automation)

**Characteristics**:

- System anticipates needs before they're expressed
- Automated opportunity identification
- Predictive resource allocation
- Self-improving through continuous learning

**Goal**: Automation as proactive research partner

**Target capabilities**:

1. **Proactive Research Opportunities**
   - Identify promising research directions from data exploration
   - Suggest methodological improvements
   - Predict publication readiness
   - Success metric: 1+ proactive suggestion leads to publication

2. **Anticipatory Task Management**
   - Predict task bottlenecks before they occur
   - Auto-schedule prep work for upcoming deadlines
   - Suggest strategic reallocation based on goals
   - Success metric: Zero missed deadlines, reduced last-minute work

3. **Automated Knowledge Synthesis**
   - Identify patterns across research projects
   - Suggest connections between ideas
   - Auto-generate literature review sections
   - Success metric: Accelerate literature review by >50%

**Development pattern**:

1. Build on Stage 4 learning systems
2. Implement goal-directed planning
3. Test anticipatory actions with human-in-loop
4. Gradually increase autonomy as trust grows

**Exit criteria**:

- [ ] System regularly makes valuable proactive suggestions
- [ ] Nic's role shifts primarily to strategic direction
- [ ] Research output increases without time increase
- [ ] Quality remains publication-grade

## Current Status

**Stage**: Transitioning from Stage 1 (Documented) to Stage 2 (Scripted Tasks)

**Last updated**: 2025-11-11 (Week 1 Audit)

**Stage 1 Completion**: ⚠️ 90%

- ✅ Documentation structure complete
- ✅ Workflow documentation complete
- ✅ Session start loading working
- ✅ Framework skill and experiment system established
- ✅ Session knowledge extraction implemented
- ✅ User prompt hook automation added
- ⚠️ Integration testing framework: 70% (7 tests, missing E2E agent behavior validation)
- ❌ Task management reliability: 60% (scripts exist but agents bypass, format inconsistencies)

**Stage 2 Progress**: ⚠️ 70%

Target automation #2 (Task Capture and Filing):

- ✅ Task scripts migrated from academicOps (task_view.py, task_archive.py, task_add.py)
- ✅ Specifications written (email→tasks workflow, Tasks MCP server)
- ✅ Email workflow documentation complete (email-capture.md with validated MCP parameters)
- ✅ /email slash command created
- ✅ CORE.md trigger phrases added (6 explicit phrases)
- ✅ Integration tests created (3/3 passing)
- ✅ E2E workflow validation complete (20 emails → 3 tasks created successfully)
- ✅ bmem categorization working (HIGH/MEDIUM/LOW confidence scoring)
- ⚠️ Duplicate detection not tested (no duplicate emails in test run)
- ❌ Task management reliability issues (agents bypass scripts, format mismatches)
- ❌ MCP infrastructure not built

**Blockers to Stage 2**:

1. ✅ **COMPLETED - Email Workflow E2E Validation**: Workflow validated end-to-end with real emails
   - Status: 100% complete (docs ✅, tests ✅, agent execution ✅)
   - Result: 20 emails processed → 3 tasks created successfully with proper categorization
   - Fix applied: bmem MCP parameters corrected (removed invalid n_results, search_mode)
   - Remaining: Duplicate detection edge case (needs test with actual duplicates)
   - Unblocked: Email→task workflow ready for production use

2. **P1 - Tasks MCP Server**: No enforcement of exclusive write access (spec ready: 2025-11-11_task-mcp-server.md)
   - Effort: 8-12h
   - Blocks: Task management reliability

3. **P1 - E2E Testing Infrastructure**: Agent behavior validation harness missing (structure tests only)
   - Effort: 8-12h for harness + priority tests
   - Blocks: Confidence in workflow reliability across all automations

**Next milestones**:

1. ✅ Complete task specifications (email→tasks, Tasks MCP) - DONE
2. ✅ Validate email→tasks workflow E2E - DONE (2025-11-11)
3. Fix task management reliability (agents bypass scripts) - **NEXT**
4. Add E2E test harness for automated validation
5. Optionally implement Tasks MCP server
6. Document learning in experiment logs

## Governance

### Progression Rules

1. **No skipping stages**: Must complete exit criteria before advancing
2. **Parallel work allowed**: Can work on multiple automations within same stage
3. **Regression okay**: Drop back if reliability falls below thresholds
4. **Learning required**: Every automation must produce documented lessons

### Quality Gates

Before advancing to next stage:

- All exit criteria met
- Reliability thresholds achieved
- Integration tests passing at >95%
- Documentation complete and conflict-free
- Experiment logs show learning patterns

### Risk Management

**Stage 2-3 risks**:

- Over-automation of low-value tasks → Mitigate: Strict prioritization by impact
- Brittle scripts → Mitigate: Comprehensive integration tests
- Maintenance burden → Mitigate: DRY principles, modular design

**Stage 4-5 risks**:

- AI errors with high stakes → Mitigate: Human-in-loop for substantive decisions
- Complexity explosion → Mitigate: Aggressive simplification, clear boundaries
- Loss of academic control → Mitigate: Nic always owns final decisions

## Metrics Dashboard

Track progress across stages:

**Automation coverage**: % of workflows automated **Reliability**: % of automation runs succeeding without intervention **Impact**: Time saved per week (measured) **Quality**: Publication acceptance rate, review feedback **Cognitive load**: Subjective assessment (weekly check-in)

## Related Documents

- [[VISION.md]] - End state we're building toward
- [[TASK-SPEC-TEMPLATE.md]] - How to specify each automation
- [[experiments/LOG.md]] - Learning from experiments
- [[experiments/2025-11-11_week-one-audit.md]] - Week 1 comprehensive audit
- [[../../AXIOMS.md]] - Principles governing all stages
