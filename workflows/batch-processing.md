---
id: batch-processing
category: operations
---

# Batch Processing Workflow

## Overview

Efficient workflow for processing multiple similar items concurrently. Uses the **worker-hypervisor architecture** (see [[specs/worker-hypervisor]]) for parallel execution with proper coordination.

## When to Use

- Processing multiple files/items with same operation
- Running tests across multiple modules
- Batch updates or migrations
- Generating multiple outputs
- Multiple independent bd tasks ready for parallel work

## When NOT to Use

- Items have dependencies between them
- Work must be done in specific order
- Shared mutable state would cause conflicts
- Serial processing is required

## Architecture

This workflow uses the **worker-hypervisor pattern**:

- **Workers**: Autonomous agents that each execute ONE bd task
- **Hypervisor**: Coordinator that manages worker pool (4-8 concurrent)
- **bd**: Task queue that workers pull from

```
Hypervisor
    │
    ├─ Worker 1 (bd task A)
    ├─ Worker 2 (bd task B)
    ├─ Worker 3 (bd task C)
    └─ Worker 4 (bd task D)
```

## Steps

### 1. Track work in bd ([[bd-workflow]])

Follow the [[bd-workflow]] to set up issue tracking:
- Check for existing issues: `bd ready` to see tasks available
- Create issues for each parallelizable unit of work
- Mark parent issue as in-progress

### 2. Identify scope and validate task independence

**Determine items to process:**
- List all bd tasks ready for parallel work: `bd ready`
- Verify no task has blockers on another parallel task
- Identify scope boundaries (which files each task will touch)

**Validate independence:**
- Tasks MUST NOT modify same files
- Tasks MUST NOT have circular dependencies
- Each task has clear success criteria

**Example:**
```
Ready tasks: ns-abc, ns-def, ns-ghi, ns-jkl
All independent: Yes (different file scopes)
Concurrent workers: 4
```

### 3. Spawn hypervisor OR spawn workers directly

**Option A: Use hypervisor (recommended for 5+ tasks)**

```javascript
Task(
  subagent_type="hypervisor",
  prompt=`Manage parallel execution of ready bd tasks.

  Tasks to process:
  - ns-abc: [description]
  - ns-def: [description]
  - ns-ghi: [description]
  - ns-jkl: [description]

  Maintain pool of 4 concurrent workers.
  Coordinate git push after all complete.`
)
```

**Option B: Spawn workers directly (for 2-4 tasks)**

```javascript
// Each worker gets full task context
Task(
  subagent_type="worker",
  run_in_background=true,
  prompt="/tmp/worker-context-ns-abc.md"  // Pre-generated context file
)

Task(
  subagent_type="worker",
  run_in_background=true,
  prompt="/tmp/worker-context-ns-def.md"
)
```

**Worker context file format** (generated before spawning):

```markdown
## Worker Task Context

**BD Issue**: ns-abc
**Title**: Refactor authentication module
**Scope**: src/auth/*.py (can modify), tests/auth/*.py (can modify)
**Out of scope**: src/core/*, config/*

### Success Criteria
1. All auth functions use new token format
2. Tests pass
3. No imports from deprecated module
```

### 4. Monitor progress (hypervisor handles this automatically)

If using hypervisor, it manages monitoring. If spawning workers directly:

```bash
# Check background task status
/tasks

# Check bd state for worker progress
bd list --status=in_progress
```

**Handle failures:**
- Worker reports failure with specific reason
- Hypervisor retries once, then logs and continues
- Failed tasks remain in bd with comments explaining failure

### 5. CHECKPOINT: All items processed successfully

Verify completion:

**Check counts:**
```bash
# Count expected vs. processed
Expected: [N items]
Processed: [M items]
Failed: [P items]
```

**Verify quality:**
- Spot-check random samples
- Run validation tests
- Check output format/structure
- Look for patterns in failures

**All items must be:**
- ✓ Processed or explicitly deferred
- ✓ Results verified
- ✓ Failures investigated
- ✓ Quality checks passed

If anything failed, return to step 4 to process failures.

### 6. Coordinate push and close bd issues

**If using hypervisor**: Hypervisor handles git coordination:
- Collects all worker commits (local)
- Runs combined test suite
- Single `git pull --rebase && git push`
- Closes all worker bd issues

**If spawning workers directly**: Coordinate push yourself:

```bash
# After all workers complete
./scripts/format.sh          # Format all changes
git pull --rebase            # Get any remote changes
# Workers already committed, just push
git push

bd sync                       # Sync bd (per [[bd-workflow]])
bd close <parent-id>          # Close parent issue if applicable
```

**Why single push point?** Workers commit locally but don't push. This prevents:
- Push conflicts between concurrent workers
- Partial work on remote
- Merge conflicts from interleaved pushes

## Parallel Processing Patterns

### Fixed Batches

Best for known item count:
- Divide items into equal batches
- Spawn all agents upfront
- Wait for all to complete

### Dynamic Scaling

Best for unknown duration:
- Start with small agent pool
- Spawn more as agents complete
- Adaptive to workload

### Pipeline Pattern

Best for multi-stage processing:
- Stage 1 agents feed Stage 2 agents
- Each stage processes independently
- Overall parallelization across stages

## Error Handling

### Partial Failures

If some items fail:
1. Document which items failed
2. Identify common patterns
3. Fix issue if possible
4. Re-process failed items
5. If unfixable, document and defer

### Complete Failures

If batch processing completely fails:
1. Stop all agents
2. Investigate root cause
3. Fix the issue
4. Restart from beginning or checkpoint

### Graceful Degradation

For non-critical batch work:
- Process as many as possible
- Document failures
- Create follow-up issues
- Complete with partial success

## Success Metrics

- [ ] All items identified and scoped
- [ ] Parallel agents spawned efficiently
- [ ] All items processed or explicitly deferred
- [ ] Results verified for quality
- [ ] Failures investigated and documented
- [ ] Changes committed and pushed
- [ ] bd issue closed with summary

## Performance Tips

**Optimize batch size:**
- Too small: overhead dominates
- Too large: no parallelization
- Sweet spot: 10-20 items per agent usually

**Resource limits:**
- Don't spawn more agents than CPU cores
- Consider memory usage per agent
- API rate limits if calling external services

**Progress tracking:**
- Use consistent output format
- Report progress periodically
- Enable easy aggregation of results
