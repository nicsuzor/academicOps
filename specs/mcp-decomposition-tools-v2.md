# MCP Decomposition Tools v2: Data Access Layer Specification

## Architectural Principle

**Dumb Server, Smart Agent**

The MCP server is a **data access layer only**. It exposes raw data structures that enable LLM agents (effectual-planner, decomposition agents) to reason and make decisions. The server does NOT:
- Make recommendations
- Score or rank tasks by "value"
- Generate proposals or suggestions
- Perform semantic analysis

The server DOES:
- Compute deterministic metrics
- Return structured data
- Filter and aggregate
- Expose graph topology

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
    include_similar: bool = True,
    similar_limit: int = 10,
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
            - project_tasks: list[task]    # other tasks in same project
            - common_patterns: list[str]   # frequent task types/prefixes in project
        - similar_tasks: list[{task, similarity_reason}]  # by title overlap
        - related_by_tags: list[task]      # tasks sharing tags
    """
```

**What moved to agent:** Generating decomposition proposal, deciding subtask structure, LLM reasoning about breakdown.

---

### 4. suggest_relationships() → `get_relationship_candidates()`

**Original Conception (WRONG):**
```python
async def suggest_relationships(task_id: str) -> List[RelationshipSuggestion]:
    """Suggest potential relationships with confidence scores."""
```
Server does semantic analysis, generates suggestions with confidence.

**New Conception (CORRECT):**
```python
@mcp.tool()
def get_relationship_candidates(
    task_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Return candidate tasks for relationships. Agent suggests connections.

    Returns:
        - task: Full task data
        - same_project_tasks: list[task]           # other tasks in project
        - similar_title_tasks: list[{task, overlap_terms}]  # word overlap
        - same_tag_tasks: list[task]               # shared tags
        - orphan_tasks: list[task]                 # tasks with no relationships
        - potential_parents: list[task]            # tasks that could be parents (higher type)
        - potential_dependencies: list[task]       # active tasks in same project
        - blocked_by_this: list[task]              # already depending on this task
        - this_depends_on: list[task]              # existing dependencies
    """
```

**What moved to agent:** Deciding which candidates should actually be related, suggesting relationship types, confidence scoring.

---

### 5. identify_refactoring_opportunities() → `get_structural_signals()`

**Original Conception (WRONG):**
```python
async def identify_refactoring_opportunities() -> List[RefactoringOpportunity]:
    """Find structural issues, return actionable recommendations."""
```
Server identifies issues and recommends actions.

**New Conception (CORRECT):**
```python
@mcp.tool()
def get_structural_signals(
    project: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return structural data patterns. Agent identifies issues.

    Returns:
        - orphans: list[task]                      # no parent, no dependencies
        - deep_tasks: list[{task, depth}]          # depth > 5
        - high_fanout_tasks: list[{task, blocking_count}]  # blocking > 5 others
        - long_chains: list[{start_id, chain_length, chain_ids}]  # dependency chains > 5
        - similar_titles: list[{task_a, task_b, shared_words}]  # potential duplicates
        - stale_ready: list[{task, ready_days}]    # ready > 7 days, not started
        - empty_parents: list[task]                # non-leaf tasks with no children
        - type_mismatches: list[{task, issue}]     # e.g., "action" type with children
    """
```

**What moved to agent:** Deciding which signals indicate actual problems, prioritizing issues, recommending specific refactoring actions.

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
def _compute_word_overlap(title_a: str, title_b: str) -> list[str]:
    """Return shared significant words between two titles."""

def _get_dependency_chain_length(task_id: str, index: TaskIndex) -> int:
    """Compute longest dependency chain starting from task."""

def _tasks_created_since(storage: TaskStorage, days: int) -> list[Task]:
    """Return tasks created in last N days."""
```

### Performance Considerations

- Most metrics can be computed from TaskIndex (cached)
- Similar title search may need optimization for large graphs
- Consider caching structural signals with TTL

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

| Original Name | New Name | Server Does | Agent Does |
|--------------|----------|-------------|------------|
| analyze_graph_health() | get_graph_metrics() | Compute metrics | Interpret health |
| identify_high_voi_tasks() | get_task_scoring_factors() | Return raw factors | Compute VOI, rank |
| propose_decomposition() | get_decomposition_context() | Gather context | Generate proposal |
| suggest_relationships() | get_relationship_candidates() | Find candidates | Suggest connections |
| identify_refactoring_opportunities() | get_structural_signals() | Expose patterns | Identify issues |
| daily_graph_review() | get_review_snapshot() | Snapshot state | Generate report |
