---
id: batch-processing
category: operations
---

# Batch Processing Workflow

## Overview

Efficient workflow for processing multiple similar items concurrently. Uses parallel subagents to maximize throughput while maintaining quality.

## When to Use

- Processing multiple files/items with same operation
- Running tests across multiple modules
- Batch updates or migrations
- Generating multiple outputs
- Any work that can be parallelized

## When NOT to Use

- Items have dependencies between them
- Work must be done in specific order
- Shared mutable state would cause conflicts
- Serial processing is required

## Steps

### 1. Track work in bd ([[bd-workflow]])

Follow the [[bd-workflow]] to set up issue tracking:
- Check for existing issues
- Create issue if needed: `bd create --title="Batch: [operation] on [items]" --type=task --priority=2`
- Mark as in-progress

### 2. Identify scope of work and create plan for concurrent execution

**Determine items to process:**
- List all files/items/targets
- Group by similarity if needed
- Estimate total work

**Create parallelization plan:**
- How many items per agent?
- How many concurrent agents?
- What's the optimal batch size?
- Are there resource constraints?

**Example:**
```
Total items: 50 files
Batch size: 10 files per agent
Concurrent agents: 5
Expected time: ~5 minutes
```

### 3. Spawn parallel subagents for items 1-N

Launch background agents for concurrent processing:

```javascript
// Spawn first batch of agents
Task(
  subagent_type="general-purpose",
  run_in_background=true,
  prompt=`Process items 1-10: [list items]

  For each item:
  1. [operation description]
  2. Verify success
  3. Report completion

  Return summary of results.`
)

Task(
  subagent_type="general-purpose",
  run_in_background=true,
  prompt=`Process items 11-20: [list items]
  ...`
)

// Spawn remaining batches...
```

**Best practices:**
- Use `run_in_background=true` for parallelization
- Give each agent a clear subset of work
- Include verification in agent instructions
- Request summary reports

### 4. Monitor progress and spawn additional agents when needed

Track agent completion:

```bash
# Check background task status
/tasks

# Read agent output files
Read(file_path="[output_file from task]")
```

**Adjust as needed:**
- Spawn more agents if some finish early
- Re-run failed items with dedicated agents
- Adjust batch sizes based on performance

**Handle failures:**
- Identify which items failed
- Investigate common failure patterns
- Re-process failed items
- Document issues for follow-up

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

### 6. Commit, push, close bd issue ([[bd-workflow]])

Land all changes:

```bash
./scripts/format.sh          # Format all changes
git add -A                    # Stage everything
git commit -m "feat: batch [operation] on [N items]

Processed: [N] items
Success: [M] items
Deferred: [P] items

Method: Parallel subagents (batch size: [X])

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git pull --rebase
bd sync                       # Sync bd (per [[bd-workflow]])
git push
```

Close the issue per [[bd-workflow]]:
```bash
bd close <id>                 # Mark work complete
```

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
