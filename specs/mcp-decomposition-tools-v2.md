# MCP Decomposition Tools v2: Data Access Layer Specification

## Giving Effect

- [[aops-tools/tasks_server.py]] - MCP server with 18 thin data-access tools following "Dumb Server, Smart Agent" pattern
- [[mcp__plugin_aops-core_task_manager__get_task_tree]] - Tree retrieval for decomposition
- [[mcp__plugin_aops-core_task_manager__get_task_neighborhood]] - Graph neighborhood for relationship discovery
- [[mcp__plugin_aops-core_task_manager__decompose_task]] - Atomic decomposition tool
- [[mcp__plugin_aops-core_task_manager__get_tasks_with_topology]] - Topology metrics for agent analysis
- [[mcp__plugin_aops-core_task_manager__get_graph_metrics]] - Raw graph metrics for health analysis

## Architectural Principle

**Dumb Server, Smart Agent**

The MCP server is a **data access layer only**. It exposes raw data structures that enable LLM agents (effectual-planner, decomposition agents) to reason and make decisions. The server does NOT:

- Make recommendations
- Score or rank tasks by "value"
- Generate proposals or suggestions
- Perform semantic analysis

The server DOES:

- Compute deterministic metrics (counts, depths, degrees)
- Return structured data
- Apply mechanical filters (status, project, type)
- Expose graph topology

The server does NOT:

- Compute similarity (no word overlap, no NLP)
- Apply hardcoded thresholds (agent decides what's "deep" or "stale")
- Select "candidates" (return all data, agent filters)

**Per P#78**: Deterministic computation (counting, aggregation) stays in code. Judgment (similarity, classification, threshold decisions) goes to LLM.

Reference: `tasks_server.py` already follows this pattern with 18 thin data-access tools.

---

## Tool Reconceptions

### 1. analyze_graph_health() → `get_graph_metrics()`

**Original Conception (WRONG):**

```python
async def analyze_graph_health() -> GraphHealthReport:
    """Returns: readiness_ratio, bottlenecks, orphans, etc."""
```

Server analyzes health, identifies "bottlenecks" (a judgment).

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_graph_metrics(
    scope: str = "all",  # "all", "project", or task_id for subtree
    scope_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return raw graph metrics. Agent interprets health.

    Returns:
        - total_tasks: int
        - tasks_by_status: dict[str, int]  # {active: 10, done: 50, ...}
        - tasks_by_type: dict[str, int]    # {task: 30, action: 20, ...}
        - orphan_count: int                 # tasks with no parent or dependencies
        - root_count: int
        - leaf_count: int
        - max_depth: int
        - avg_depth: float
        - dependency_stats:
            - total_edges: int
            - max_in_degree: int           # most dependencies on single task
            - max_out_degree: int          # single task blocking most others
            - tasks_with_high_out_degree: list[{id, title, out_degree}]  # raw data, not "bottlenecks"
        - readiness_stats:
            - ready_count: int
            - blocked_count: int
            - in_progress_count: int
    """
```

**What moved to agent:** Interpreting whether metrics indicate "healthy" or "unhealthy", identifying which high-out-degree tasks are problematic "bottlenecks".

---

### 2. identify_high_voi_tasks() → `get_task_scoring_factors()`

**Original Conception (WRONG):**

```python
async def identify_high_voi_tasks(limit: int = 10) -> List[ScoredTask]:
    """Find tasks with highest information value."""
```

Server decides which tasks are "high VOI" using embedded scoring logic.

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_task_scoring_factors(
    ready_only: bool = True,
    include_done: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Return tasks with raw scoring factors. Agent computes VOI.

    Returns per task:
        - id, title, type, status, priority
        - created_age_days: float
        - modified_age_days: float
        - complexity: str | None
        - blocking_count: int              # how many tasks depend on this
        - blocked_by_count: int            # how many dependencies this has
        - soft_blocking_count: int         # non-blocking relationships
        - child_count: int
        - parent_chain_length: int         # depth in hierarchy
        - tags: list[str]
        - project: str | None
        - body_length: int                 # proxy for specification completeness
        - has_acceptance_criteria: bool    # body contains "acceptance" or "[ ]"
    """
```

**What moved to agent:** VOI scoring algorithm, ranking, determining what "high value" means in current context.

---

### 3. propose_decomposition() → `get_decomposition_context()`

**Original Conception (WRONG):**

```python
async def propose_decomposition(rough_idea: str) -> DecompositionProposal:
    """Generate a proposed task decomposition."""
```

Server does LLM calls, generates proposals.

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_decomposition_context(
    task_id: str,
) -> dict[str, Any]:
    """
    Return context for decomposition. Agent proposes breakdown.

    Returns:
        - task: Full task data (title, body, type, complexity, etc.)
        - existing_children: list[task]    # if already decomposed
        - parent_context:
            - parent: task | None
            - siblings: list[task]         # other children of parent
        - project_context:
            - project: str | None
            - project_tasks: list[task]    # ALL other tasks in same project (agent decides relevance)
    """
```

**What moved to agent:**

- Finding "similar" tasks (LLM reads titles, decides similarity)
- Generating decomposition proposal
- Deciding subtask structure

**Removed from server:** `similar_tasks`, `common_patterns`, `related_by_tags` - all require judgment about relevance. Agent gets raw project task list and reasons over it.

---

### 4. suggest_relationships() → `get_task_neighborhood()`

**Original Conception (WRONG):**

```python
async def suggest_relationships(task_id: str) -> List[RelationshipSuggestion]:
    """Suggest potential relationships with confidence scores."""
```

Server does semantic analysis, generates suggestions with confidence.

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_task_neighborhood(
    task_id: str,
) -> dict[str, Any]:
    """
    Return the task and its graph neighborhood. Agent decides relationships.

    Returns:
        - task: Full task data (title, body, tags, project, etc.)
        - existing_relationships:
            - parent: task | None
            - children: list[task]
            - depends_on: list[task]
            - blocks: list[task]              # tasks that depend on this
        - same_project_tasks: list[task]      # ALL tasks in same project
        - orphan_tasks: list[task]            # tasks with no parent AND no dependencies
    """
```

**What moved to agent:**

- Deciding which tasks are "similar" (LLM reads titles)
- Suggesting relationship types
- Identifying "candidates" (agent reviews same_project_tasks list)

**Removed from server:** `similar_title_tasks`, `potential_parents`, `potential_dependencies` - all imply server deciding what's "potential". Agent gets raw lists and reasons.

---

### 5. identify_refactoring_opportunities() → `get_tasks_with_topology()`

**Original Conception (WRONG):**

```python
async def identify_refactoring_opportunities() -> List[RefactoringOpportunity]:
    """Find structural issues, return actionable recommendations."""
```

Server identifies issues and recommends actions.

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_tasks_with_topology(
    project: Optional[str] = None,
    status: Optional[str] = None,  # filter by status
    min_depth: Optional[int] = None,  # agent specifies threshold
    min_blocking_count: Optional[int] = None,  # agent specifies threshold
) -> dict[str, Any]:
    """
    Return tasks with their topology metrics. Agent identifies issues.

    Returns list of tasks, each with:
        - id, title, type, status, project, tags
        - depth: int                    # levels from root
        - parent: str | None
        - child_count: int
        - blocking_count: int           # tasks depending on this
        - blocked_by_count: int         # dependencies this has
        - is_leaf: bool
        - created: datetime
        - modified: datetime
        - ready_days: float | None      # days since became ready (if status=active)
    """
```

**What moved to agent:**

- Deciding what depth is "too deep" (agent passes min_depth if desired)
- Deciding what blocking count is "high fanout" (agent passes min_blocking_count)
- Identifying "similar titles" (agent reads titles, uses LLM for similarity)
- All threshold decisions and issue classification

**Removed from server:** `deep_tasks`, `high_fanout_tasks`, `similar_titles`, `stale_ready` as pre-filtered lists. Server returns raw metrics; agent applies its own thresholds.

---

### 6. daily_graph_review() → `get_review_snapshot()`

**Original Conception (WRONG):**

```python
async def daily_graph_review() -> ReviewReport:
    """Periodic health check that flags issues proactively."""
```

Server performs review, generates flags/recommendations.

**New Conception (CORRECT):**

```python
@mcp.tool()
def get_review_snapshot(
    since_days: int = 1,
) -> dict[str, Any]:
    """
    Return snapshot data for periodic review. Agent generates report.

    Returns:
        - timestamp: str
        - metrics: get_graph_metrics() output
        - signals: get_structural_signals() output
        - changes_since:
            - tasks_created: list[task]
            - tasks_completed: list[task]
            - tasks_modified: list[task]
        - staleness:
            - oldest_ready_task: {task, days_ready}
            - oldest_in_progress: {task, days_in_progress}
        - velocity:
            - completed_last_7_days: int
            - created_last_7_days: int
    """
```

**What moved to agent:** Interpreting the snapshot, deciding what's worth flagging, generating the review report, determining if intervention is needed.

---

## Implementation Notes

### Shared Helper Functions

These existing helpers in tasks_server.py can be reused:

- `_get_index()` - Load task index
- `_get_storage()` - Get storage instance
- `_task_to_dict()` - Convert Task to dict
- `_index_entry_to_dict()` - Convert index entry to dict

### New Helper Functions Needed

```python
def _get_dependency_chain_length(task_id: str, index: TaskIndex) -> int:
    """Compute longest dependency chain starting from task."""

def _tasks_created_since(storage: TaskStorage, days: int) -> list[Task]:
    """Return tasks created in last N days."""

def _compute_ready_days(task: Task) -> float | None:
    """Days since task became ready (status=active, deps satisfied)."""
```

**Removed:** `_compute_word_overlap()` - no NLP in server per P#78.

### Performance Considerations

- Most metrics can be computed from TaskIndex (cached)
- Large project task lists may need pagination
- Agent can request filtered subsets via parameters

---

## Agent Integration

The effectual-planner agent will:

1. Call these data tools to gather context
2. Apply judgment and reasoning over the raw data
3. Generate recommendations/proposals
4. Present to human for review

Example flow for VOI prioritization:

```
1. Agent calls get_task_scoring_factors(ready_only=True)
2. Agent applies VOI heuristics: blocking_count * 2 + (7 - created_age_days) + ...
3. Agent ranks and explains top picks
4. Human reviews and selects
```

---

## Affected Tasks

These 6 P0 tasks need body updates to reflect the new conception:

- aops-ec26e932 → get_graph_metrics()
- aops-50b9c259 → get_task_scoring_factors()
- aops-7eaa5f3e → get_decomposition_context()
- aops-0453de17 → get_relationship_candidates()
- aops-d77c9f56 → get_structural_signals()
- aops-6164b13a → get_review_snapshot()

---

## Summary Table

| Original Name                        | New Name                    | Server Does                 | Agent Does                        |
| ------------------------------------ | --------------------------- | --------------------------- | --------------------------------- |
| analyze_graph_health()               | get_graph_metrics()         | Compute counts/metrics      | Interpret health                  |
| identify_high_voi_tasks()            | get_task_scoring_factors()  | Return raw factors          | Compute VOI, rank                 |
| propose_decomposition()              | get_decomposition_context() | Return task + project tasks | Find similar, propose breakdown   |
| suggest_relationships()              | get_task_neighborhood()     | Return graph neighborhood   | Decide similarity, suggest links  |
| identify_refactoring_opportunities() | get_tasks_with_topology()   | Return tasks + metrics      | Apply thresholds, identify issues |
| daily_graph_review()                 | get_review_snapshot()       | Return snapshot data        | Generate report                   |

## P#78 Compliance Checklist

- [x] No word overlap / NLP functions in server
- [x] No hardcoded thresholds (all via parameters or agent decision)
- [x] No "candidate selection" - raw lists returned
- [x] No "similarity" computation - agent uses LLM
- [x] Deterministic only: counts, depths, degrees, timestamps
