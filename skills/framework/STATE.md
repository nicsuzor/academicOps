# Framework Current State

**Last updated**: 2025-11-17

**Purpose**: Ground truth snapshot of framework's current state. Meta skill loads this FIRST to establish current reality before reading aspirational documents (VISION, ROADMAP).

---

## Current Stage

**Stage**: Transitioning from Stage 1 (Documented) to Stage 2 (Scripted Tasks)

**Stage 1 completion**: 90%
- ✅ Documentation structure complete
- ✅ Framework skill operational
- ✅ Experiment system in place
- ⚠️ Integration testing framework: 70% complete
- ❌ Task management reliability: 60%

**Stage 2 progress**: 70%
- ✅ Email→tasks workflow validated
- ⚠️ Task format inconsistencies
- ❌ Agents bypass task scripts

---

## Authoritative Facts (Foundational Infrastructure)

### Task Management

**Format**: Markdown (bmem-compliant) with YAML frontmatter
**Storage**: `data/tasks/*.md` in each repository
**Required fields**: title, created, priority
**Optional fields**: due, project, classification
**Scripts**: task_add.py, task_view.py, task_archive.py (in skills/tasks/scripts/)
**Write access**: Scripts ONLY - agents must not write task files directly

**Current blocker**: Format inconsistencies, agents bypass scripts (reliability 60%)

### bmem Knowledge Management

**Format**: Markdown entities with YAML frontmatter
**Storage**: `data/` hierarchy (projects/, people/, events/, concepts/)
**Entity types**: project, person, event, concept, relation
**Linking**: WikiLinks ([[entity-name]])
**Relations**: Frontmatter fields (related:, part-of:, etc.)

### Framework Logging

**Format**: Append-only monolithic file
**Location**: experiments/LOG.md
**Structure**: Chronological entries, all in single file, never delete entries
**Purpose**: Pattern recognition from successes AND failures over time

---

## Mandatory Processes (Non-Negotiable)

**Development approach**: Spec-first (ROADMAP line 99: "NOT optional")
1. Create task spec from TASK-SPEC-TEMPLATE.md
2. Design integration test first (must fail initially)
3. Implement minimum viable automation
4. Test until passes
5. Document in experiment log

**No timeline estimates**: ACCOMMODATIONS line 50 prohibits development time estimates (uncalibrated)

**User context loading**: ACCOMMODATIONS and CORE are as binding as AXIOMS - load before making recommendations

**Framework scope**: Supports ALL academic work across ALL repositories, not just academicOps (VISION line 11-15)

---

## Active Blockers

**P1 - Task Management Reliability**
- Issue: Agents bypass task scripts, format inconsistencies
- Impact: Blocks Stage 2 completion, blocks task-viz development
- Status: Known issue (ROADMAP line 260, 275)
- Next: Standardize format, enforce script usage

**P1 - E2E Testing Infrastructure**
- Issue: Agent behavior validation harness missing
- Impact: Can't validate workflow reliability
- Status: Structural tests only, need behavioral tests
- Next: Build test harness for agent execution validation

**P2 - Format Inconsistencies**
- Issue: Uncertainty about authoritative data formats
- Impact: Cascading failures, wrong assumptions in specs
- Status: Documented in this session's LOG entry
- Next: Add authoritative domain knowledge to all skills

---

## Recent Decisions

**2025-11-17**: Spec-first approach confirmed MANDATORY (updated ROADMAP line 99)
**2025-11-17**: No timeline estimates policy (updated ACCOMMODATIONS line 50)
**2025-11-17**: Framework scope clarified - ALL repos not just academicOps (updated VISION, ACCOMMODATIONS)
**2025-11-17**: STATE.md created to solve meta-cognizance problem

---

## Next Priorities

**Immediate**:
1. Add authoritative domain knowledge headers to skills/tasks/ and skills/bmem/
2. Update meta skill context loading: ACCOMMODATIONS/CORE → STATE → VISION/ROADMAP/AXIOMS
3. Document task format standardization approach

**Near-term**:
1. Task-viz visual dashboard (spec complete: skills/framework/specs/2025-11-17_task-visualization-dashboard.md)
2. E2E test harness design
3. Resolve task management reliability issues

**Deferred**:
1. Tasks MCP server (spec exists)
2. Multi-repo task discovery
3. Real-time dashboard updates (Stage 3 concern)

---

## Meta Skill Role Evolution

**Current**: Component maintainer focused on framework tasks
**Required**: Strategic systems coordinator

**Must demonstrate**:
- Cross-skill dependency awareness
- Systemic problem flagging (component failures → root causes)
- Binding constraint enforcement (MANDATORY = no alternatives)
- Strategic pattern recognition (multiple symptoms → diagnosis)
- System-level thinking (how pieces interrelate)

**Recent failure**: Task format uncertainty exposed as systemic architecture problem, not component issue (LOG.md 2025-11-17 entry)

---

## User Context (Always Binding)

**Primary role**: Full-time academic across multiple projects
**Framework scope**: Infrastructure for ALL academic work, ALL repositories
**ADHD accommodations**: Visual progress, zero-friction capture, clear boundaries, no timeline estimates
**Communication**: Direct action, no hedging, document immediately, don't make user carry cognitive load

**Critical quote**: "don't make me carry the cognitive load" - Document analysis immediately, don't wait for confirmation, could be interrupted at any time.
