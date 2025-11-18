# Task: Visual Task Mind Map (Excalidraw)

**Date**: 2025-11-17 (Updated: 2025-11-18)
**Stage**: 2 (Scripted Tasks)
**Priority**: P1 (High impact - solves documented accommodation need)

## Problem Statement

**What manual work are we automating?**

Need to quickly understand across all repositories:
- Where everything fits (goals → projects → tasks)
- What needs to be done (outstanding tasks)
- What we're waiting on (blockers and sequencing)
- How things are prioritised and aligned
- Where we've been (completed tasks as context)
- Why some projects have no tasks (are we making progress?)

**Current state**: Started manual Excalidraw map (`data/views/current-tasks.excalidraw`) but it's ugly - poor layout, hard to maintain, doesn't scale.

**Why does this matter?**

**Impact**:
- Reduces cognitive load when context switching (ACCOMMODATIONS.md line 30)
- Addresses core ADHD accommodation: "Need to understand progress at a glance" (ACCOMMODATIONS.md line 37)
- Directly supports VISION.md success criterion #4: "Tasks are automatically prioritized, tracked, and surfaced at the right time"
- Solves acute multi-window cognitive load problem

**Time savings**: From 5-10 minutes mentally reconstructing state → <30 seconds to scan visual map.

**Quality improvement**: Reduces task loss rate from ~20% (forgotten in mental queue) to <5% (visible in map).

**Who benefits?**

Nic - across ALL academic work (not just framework development). This solves a general workflow problem affecting every project and repository.

## Success Criteria

**The automation is successful when**:

1. **Visual hierarchy**: Mind map clearly shows goals at top → projects linked to goals → tasks under projects
2. **Outstanding work prominent**: Active/blocked tasks are large and visually prominent (what needs attention NOW)
3. **Completed work context**: Completed tasks shown in small font attached to projects (where we've been)
4. **Idle projects visible**: Projects with no outstanding tasks explicitly shown (monitoring progress)
5. **Blocker/sequencing clarity**: Blockers and task dependencies visually indicated
6. **Strategic alignment**: Tasks connected to goals they support
7. **Generation speed**: Map generates in <10 seconds from command invocation
8. **Cross-repo coverage**: Automatically discovers tasks/projects from all repositories

**Visual design goals** (replacing ugly manual version):
- Clean layout with proper spacing (not cramped)
- Logical grouping (goals → projects → tasks hierarchy)
- Color coding meaningful (status-based, not decorative)
- Text readable (appropriate font sizes)
- Connections clear (arrows show relationships)

**Quality threshold**:
- Fail-fast: If task/project file malformed, halt with clear error
- Best effort: If project→goal mapping ambiguous, show project without goal connection
- Graceful degradation: If strategic priority missing, default to "Medium"

## Scope

### In Scope

- Read all task files from `data/tasks/*.md` across multiple repositories
- Read bmem goal entities from `data/goals/` (top-level strategic objectives)
- Read bmem project entities from `data/projects/` (link to goals)
- Parse task frontmatter: title, status, project, priority, blockers, due dates
- Generate Excalidraw JSON mind map with three-tier hierarchy:
  - **Level 1 (Top)**: Goals - large boxes at top of canvas
  - **Level 2 (Middle)**: Projects - medium boxes linked to goals
  - **Level 3 (Bottom)**: Tasks - boxes sized by priority, colored by status
- Visual encodings:
  - **Size**: Outstanding tasks large, completed tasks small
  - **Color**: Active=blue, Blocked=red, Queued=yellow, Completed=green (muted)
  - **Position**: Hierarchy (goals→projects→tasks), priority left-to-right
  - **Arrows**: Goal→Project, Project→Task, Task→Blocking Task
- Show projects with no tasks explicitly (monitoring idle projects)
- Slash command `/task-map` to trigger generation
- Output replaces `data/views/current-tasks.excalidraw`

### Out of Scope

- Real-time updates (manual regeneration via `/task-map`)
- Interactive task editing (read-only visualization)
- Historical trends (Stage 4 concern)
- Automatic prioritization suggestions (Stage 4 concern)
- Calendar/deadline integration (future)

**Layout philosophy**: Don't enforce strict top-down hierarchy - use maps, clusters, organic positioning, and 2D spatial thinking where appropriate. Goals→Projects→Tasks relationship should be clear through connections, not rigid vertical structure. Allow creative/organic layouts that make visual sense.

**Boundary rationale**: Focus on clear visual representation of current state using goal→project→task hierarchy from bmem data. Editing, automation, and advanced features are Stage 3+ concerns.

## Dependencies

### Required Infrastructure

- Task files must exist in standard JSONL format at `data/tasks/*.jsonl`
- Each task must have minimum fields: `id`, `title`, `status`
- Optional task fields: `project`, `priority`, `blockers`
- Bmem entities for projects (optional - improves strategic mapping)
- ROADMAP.md for strategic priority reference (optional - improves categorization)

### Data Requirements

**Task file format**: Markdown (bmem-compliant) with YAML frontmatter
```markdown
---
title: Fix bug in parser
created: 2025-11-17T10:00:00Z
priority: 1
status: active
project: framework
---

Task description here...
```

**Note**: Original spec incorrectly assumed JSONL format. Actual format is Markdown as documented in skills/tasks/SKILL.md authoritative domain knowledge.

**What happens if data is missing or malformed?**
- Missing task file directory: Create empty dashboard with message "No tasks found"
- Malformed Markdown/YAML: Halt with error pointing to specific file (fail-fast per AXIOMS #5)
- Missing optional fields: Use defaults (priority=2/"medium", project="uncategorized")
- Missing bmem entities: Continue without strategic context enrichment

### Cross-Repository Discovery

**Problem**: Tasks exist in multiple repositories (academicOps, writing, privacy-research, etc.)

**Solution**: Scan known work locations:
- `~/src/*/data/tasks/*.md` (all repos in src directory)
- Configurable via environment variable `$TASK_REPOS` if needed

**Fallback**: If no global discovery mechanism, start with current repo only and expand later.

## Integration Test Design

**Test must be designed BEFORE implementation**

### Test Setup

Create test environment with multiple mock repositories:

```bash
# Create test directory structure
mkdir -p /tmp/task-viz-test/{repo1,repo2,repo3}/data/tasks

# Create test task files
cat > /tmp/task-viz-test/repo1/data/tasks/tasks.jsonl <<EOF
{"id":"t1","title":"Active framework task","status":"active","project":"framework","priority":"high","blockers":[]}
{"id":"t2","title":"Blocked doc task","status":"blocked","project":"framework","priority":"medium","blockers":["waiting-input"]}
EOF

cat > /tmp/task-viz-test/repo2/data/tasks/tasks.jsonl <<EOF
{"id":"t3","title":"Privacy paper draft","status":"active","project":"privacy","priority":"high","blockers":[]}
{"id":"t4","title":"Review literature","status":"queued","project":"privacy","priority":"medium","blockers":[]}
EOF

cat > /tmp/task-viz-test/repo3/data/tasks/tasks.jsonl <<EOF
{"id":"t5","title":"Completed task example","status":"completed","project":"teaching","priority":"low","blockers":[]}
EOF
```

### Test Execution

```bash
# Run task-viz skill pointing to test repos
# Agent workflow:
# 1. Glob for /tmp/task-viz-test/*/data/tasks/*.jsonl
# 2. Read each JSONL file
# 3. Parse and aggregate task data
# 4. Generate Excalidraw JSON via script
uv run python scripts/generate_task_viz.py /tmp/task-viz-test-data.json /tmp/output.excalidraw
```

### Test Validation

```bash
# Validate generated Excalidraw file
test -f /tmp/output.excalidraw || exit 1

# Validate it's valid JSON
jq empty /tmp/output.excalidraw || exit 1

# Validate contains expected task count (5 tasks)
task_count=$(jq '[.elements[] | select(.type == "rectangle")] | length' /tmp/output.excalidraw)
[[ "$task_count" -eq 5 ]] || exit 1

# Validate project grouping (3 projects: framework, privacy, teaching)
# (Implementation detail - verify structure has grouping)

# Validate color coding by status
# Active tasks should have blue color
# Blocked tasks should have red color
# Completed tasks should have green color
# (Check color properties in Excalidraw JSON)
```

### Test Cleanup

```bash
# Remove test directories and output
rm -rf /tmp/task-viz-test
rm -f /tmp/task-viz-test-data.json /tmp/output.excalidraw
```

### Success Conditions

- [x] Test initially fails (no implementation yet)
- [ ] Test passes after implementation
- [ ] Test covers happy path (multiple repos, multiple projects, various states)
- [ ] Test covers error case (malformed JSONL)
- [ ] Test validates all success criteria (completeness, grouping, color coding)
- [ ] Test is idempotent (can run repeatedly)
- [ ] Test cleanup leaves no artifacts

## Implementation Approach

### High-Level Design

**Pattern**: Agent does ALL creative/analytical work → Helper script (if needed) for repetitive tasks only

**CRITICAL FRAMEWORK PRINCIPLE**: Our framework approach is to have very small helper scripts for purely mechanical, repetitive operations, while ALL creative, thinking, and analytical work is done by Claude Code agents. Claude Code INVOKES Python scripts for mechanical tasks, not the other way around.

**Components**:

1. **Task Discovery** (Agent via Glob)
   - Find all `data/tasks/*.md` files across repositories
   - Support single-repo and multi-repo modes

2. **Task Data Aggregation** (Agent via Read + LLM reasoning)
   - Read each Markdown file
   - Parse YAML frontmatter and content
   - Validate required fields
   - Enrich with bmem project data (project goals, strategic context)
   - Map projects to goals from bmem entities

3. **Visual Mind-Map Design** (Agent reasoning + LLM creativity)
   - Understand user goals: "quickly understand where everything fits, what needs to be done, what we're waiting on, what sequencing/blockers we need to deal with, and how things are prioritised and aligned"
   - Design visual layout that shows:
     - **Goals** at top level (strategic context)
     - **Projects** linked to goals
     - **Outstanding tasks** prominently displayed (what needs attention)
     - **Completed tasks** in small font attached to projects (where we've been)
     - **Projects with no tasks** explicitly shown (why not? are we making progress?)
     - **Blockers and sequencing** visually indicated
   - Determine appropriate visual encodings (size, color, position, connections)

4. **Excalidraw Generation** (Agent directly creates JSON)
   - Agent generates complete Excalidraw JSON structure
   - Creates visual elements: boxes for projects/tasks, text labels, arrows for relationships
   - Applies visual hierarchy: large/prominent for outstanding work, small for completed
   - Encodes status through color/styling
   - Groups related elements
   - **Optional helper script**: If turning task/project files into structured format proves repetitive, may create small helper to aggregate data, but visualization design and generation is LLM work

5. **Output** (Agent via Write)
   - Write to `~/current-tasks.excalidraw`
   - Confirm successful generation
   - Report summary of what's shown

**Data Flow**:
```
Task files (*.md) + Project entities (bmem) + Goals (bmem)
  → Agent Glob/Read → Parse/validate
  → Agent reasoning → Enrich with strategic context
  → Agent analyzes → Understand what story to tell visually
  → Agent designs → Layout strategy, visual encodings
  → Agent creates → Excalidraw JSON directly
  → Excalidraw file output
```

### Technology Choices

**Language/Tools**:
- Agent orchestration: Claude Code built-in tools (Glob, Read, Write, Bash)
- Visualization script: Python with `uv` (per AXIOMS #9)
- Output format: Excalidraw JSON (text-based, version-control friendly)

**Libraries**:
- Standard library only for generation script (json, dataclasses for type safety)
- No external dependencies unless absolutely necessary
- If Excalidraw library exists: Evaluate vs. manual JSON generation

**Rationale**:
- Python: Type-safe (mypy), standard in framework (AXIOMS #9)
- Excalidraw: Industry-standard diagramming, git-friendly, visual, editable
- No complex dependencies: Keeps script simple and maintainable (MINIMAL principle)

**Alternative considered**: SVG generation
- Rejected: Less editable, not standard in diagram tooling ecosystem
- Excalidraw provides better workflow integration

### Error Handling Strategy

**Fail-fast cases** (halt immediately, per AXIOMS #5):

- Task file exists but is malformed JSON
- Task file missing required fields (id, title, status)
- Invalid status value (not in: queued, active, blocked, completed)
- Visualization script fails (malformed input data)

**Error messages must include**:
- Exact file path and line number for JSONL errors
- Field name for missing required fields
- Clear remediation steps

**Graceful degradation cases** (best effort):

- Missing optional fields (project, priority, blockers) → Use defaults
- Missing bmem project data → Continue without enrichment
- Ambiguous project mapping → Label as "Uncategorized"
- Missing ROADMAP strategic priority → Default to "Medium"

**Recovery mechanisms**:

- If single task file is malformed: Skip that file, continue with others, report warning
- If ALL task files malformed: Generate empty dashboard with error summary
- Failed generation: Preserve any existing dashboard file, report error

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Task file has malformed JSONL
   - **Detection**: JSON parse error when reading file
   - **Impact**: Cannot visualize tasks from that repository
   - **Prevention**: Task creation tools must validate JSONL format
   - **Recovery**: Skip malformed file, report clear error with file:line, continue with valid files

2. **Failure mode**: Multiple repositories have task ID collisions
   - **Detection**: Duplicate task IDs when aggregating
   - **Impact**: Tasks overwrite each other in visualization
   - **Prevention**: Task IDs should include repo prefix (e.g., "aops-t123")
   - **Recovery**: Detect collision, append repo name to duplicate IDs, warn user

3. **Failure mode**: Excalidraw generation script produces invalid JSON
   - **Detection**: JSON validation fails on output
   - **Impact**: Dashboard file cannot be opened in Excalidraw
   - **Prevention**: Integration test validates JSON structure
   - **Recovery**: Halt generation, preserve previous dashboard, report error

4. **Failure mode**: Visualization becomes unreadable with 100+ tasks
   - **Detection**: Manual observation, or layout exceeds reasonable bounds
   - **Impact**: Dashboard too cluttered to be useful
   - **Prevention**: Start with simple layout, test with realistic task counts
   - **Recovery**: Implement filtering/grouping/pagination in future iteration (Stage 3)

5. **Failure mode**: Task discovery finds wrong directories
   - **Detection**: Tasks from unrelated projects appear
   - **Impact**: Dashboard shows irrelevant information
   - **Prevention**: Clear documentation of task discovery pattern, configurable paths
   - **Recovery**: User configuration override via environment variable

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- **Generation success rate**: % of invocations that produce valid dashboard
- **Task coverage**: % of known tasks that appear in dashboard
- **Generation time**: Seconds from invocation to output file
- **Error rate**: % of repositories skipped due to malformed data

**Monitoring approach**:

- Log each generation attempt: timestamp, repo count, task count, duration, success/failure
- Weekly review: Check if error rate increasing (indicates task file quality issues)
- User feedback: Note when dashboard is missing expected tasks

**Validation frequency**:

- Automated: Each invocation validates output JSON structure
- Manual: User verification that dashboard matches mental model of task state
- Periodic: Weekly check that all active repositories discovered

## Documentation Requirements

### Code Documentation

- [ ] Docstrings for all functions (purpose, inputs, outputs, failure modes)
- [ ] Type hints for Python (mypy must pass)
- [ ] Inline comments for Excalidraw layout calculations
- [ ] Script header docstring explaining agent orchestration pattern

### User Documentation

- [ ] Add `/task-viz` command documentation to commands/README.md
- [ ] Update CORE.md with trigger phrase for dashboard generation
- [ ] Document in ROADMAP.md as Stage 2 automation #5
- [ ] Create experiment log entry when validated

### Maintenance Documentation

- [ ] Known limitations: Single-repo vs multi-repo discovery, task count limits
- [ ] Future improvements: Real-time updates, interactive editing, historical trends
- [ ] Dependencies: Task JSONL format specification, Excalidraw JSON structure

## Rollout Plan

### Phase 1: Validation (Experiment)

- Test with current academicOps task files only (single repo)
- Generate dashboard manually, verify visual accuracy
- Refine layout based on actual usage
- Validate generation time <10sec
- Document in experiment log

**Criteria to proceed**: Dashboard accurately represents all tasks in academicOps, generation reliable (100% success over 10 runs)

### Phase 2: Limited Deployment (Multi-Repo)

- Extend to 2-3 active repositories (e.g., academicOps, writing, privacy-research)
- Test cross-repo task discovery
- Validate task ID collision handling
- Monitor for missing tasks or incorrect grouping
- Keep manual task list as verification

**Criteria to proceed**: Multi-repo discovery works reliably, no missing tasks, <5% manual corrections needed

### Phase 3: Full Deployment

- Enable for all repositories in `~/src/`
- Make `/task-viz` default workflow for task overview
- Reduce manual task tracking
- Periodic validation: monthly check that dashboard complete

**Rollback plan**: If visualization becomes unreliable or generation fails frequently, revert to manual task lists. Dashboard generation script is read-only and doesn't modify task files, so rollback is safe.

## Risks and Mitigations

**Risk 1**: Excalidraw JSON format changes in future versions

- **Likelihood**: Low (format relatively stable)
- **Impact**: Medium (dashboards stop rendering correctly)
- **Mitigation**: Use minimal Excalidraw features (rectangles, text, arrows), test with current version, document format version used

**Risk 2**: Task file format inconsistencies across repositories

- **Likelihood**: High (different repos may evolve independently)
- **Impact**: Medium (some tasks not visualized correctly)
- **Mitigation**: Define strict task JSONL schema, validate on creation, fail-fast on invalid format

**Risk 3**: Performance degrades with large task counts (100+)

- **Likelihood**: Medium (depends on project growth)
- **Impact**: Low (generation time acceptable up to ~200 tasks)
- **Mitigation**: Test with realistic dataset sizes (50-100 tasks), optimize layout algorithm if needed, consider pagination for >200 tasks

**Risk 4**: Visual layout becomes cluttered/unreadable

- **Likelihood**: Medium (depends on task/project count)
- **Impact**: High (defeats "at a glance" purpose)
- **Mitigation**: Start simple, iterate on layout based on real usage, consider filtering options (show active only, etc.)

## Open Questions

1. **Multi-repo discovery strategy**: Should we scan all `~/src/*/data/tasks/` automatically, or require explicit repository configuration?
   - **Proposed answer**: Start with automatic scan of `~/src/`, allow override via `$TASK_REPOS` environment variable

2. **Strategic priority source**: Should priority come from ROADMAP.md, bmem project entities, or task file itself?
   - **Proposed answer**: Hierarchy: task.priority (explicit) > bmem project.priority > "medium" default

3. **Blocker visualization**: How to show blocking relationships between tasks (arrows)?
   - **Proposed answer**: Start without arrows (just show blocker text), add arrows in Phase 2 if needed

4. **Completed task handling**: Should completed tasks appear in dashboard or be filtered?
   - **Proposed answer**: Include completed tasks in different visual area (bottom), allow user to see recent completions for satisfaction

5. **Update frequency**: Should dashboard auto-update on task changes, or manual regeneration only?
   - **Proposed answer**: Manual regeneration initially (via `/task-viz`), auto-update is Stage 3 concern

## Notes and Context

**Related documents**:
- experiments/2025-11-17_multi-window-cognitive-load-solutions.md (Problem statement)
- ACCOMMODATIONS.md lines 30, 37 (User requirements)
- VISION.md success criterion #4 (Strategic alignment)
- ROADMAP.md Stage 2 automation target #2 (Task Capture and Filing)

**Design principles applied**:
- AXIOM #8 (DRY, Modular): Agent orchestrates, script is simple utility
- AXIOM #16 (Long-term infrastructure): Reusable across all repos
- VISION.md scope: Works across ALL projects, not just academicOps
- ACCOMMODATIONS.md: Visual, glanceable, reduces cognitive load

**Excalidraw choice rationale**:
- Text-based JSON format (git-friendly)
- Industry-standard tool (AXIOM #9)
- Editable after generation (user can adjust layout)
- Visual and glanceable (ACCOMMODATIONS requirement)
- Supports color coding and spatial organization

---

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably (>95% success rate)
- [ ] All failure modes addressed with error handling
- [ ] Documentation complete (code docstrings, user guide, maintenance notes)
- [ ] Experiment log entry created with validation results
- [ ] No documentation conflicts introduced
- [ ] Code follows AXIOMS.md principles (fail-fast, DRY, explicit, type-safe)
- [ ] Monitoring/logging in place
- [ ] Rollout plan executed through Phase 2 minimum
- [ ] ROADMAP.md updated with completion status

## Post-Implementation Review

[After 2 weeks of production use]

**What worked well**:
- [TBD after implementation]

**What didn't work**:
- [TBD after implementation]

**What we learned**:
- [TBD after implementation]

**Recommended changes**:
- [TBD after implementation]
