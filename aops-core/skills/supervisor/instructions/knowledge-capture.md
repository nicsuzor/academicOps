# Knowledge Capture

## Phase 6: Knowledge Capture

Post-merge, supervisor extracts learnings and files structured follow-ups.

**Extraction Protocol**:

```markdown
## Supervisor: Capture Knowledge

1. Collect sources:
   - PR description and comments
   - Commit messages
   - Task body
   - Review comments

2. Extract learnings:
   - Decisions made
   - Alternatives rejected
   - Patterns discovered
   - Mistakes caught
   - Estimate accuracy

3. Store via /remember skill

4. Create follow-up tasks if needed:
   - TODO comments → tech-debt task
   - Reviewer suggestions → enhancement task (needs approval)
   - Estimate >50% off → learn task for estimation improvement
```

## Post-Run Follow-Up (MANDATORY)

After a dogfood run completes, the supervisor (or the agent working through the merge queue) MUST:

### 1. Assess Wasted Work

Check every PR and task for signs of misdirected effort:

- Did any worker target **deprecated code**? (file/module superseded by another implementation)
- Did any worker target the **wrong repo**? (task belongs in a different repository)
- Did any worker implement something that **already exists**? (duplicate of existing functionality)

For each instance: file a GitHub Issue via `/learn` explaining the root cause and what validation would have prevented it.

### 2. File Structured Follow-Ups

Create two tasks under the supervisor epic:

**a) "Pre-next-run fixes" epic** — everything that must be fixed before repeating:

- Infrastructure issues (Docker, CI, tooling failures)
- Process issues (validation gaps, missing context, deprecated code signals)
- Include links to GitHub Issues filed

**b) "Repeat and reassess" task** — blocked on the fixes epic:

- Baseline metrics from this run
- What to measure next time
- AC for declaring improvement

### 3. Update Supervisor Instructions

If the run revealed new failure modes or limitations, update:

- This file's extraction protocol
- `SKILL.md` known limitations section
- `worker-execution.md` if dispatch needs new checks

**Anti-pattern**: Leaving findings only in task bodies or session notes. Follow-up tasks are the durable output — without them, the next run hits the same problems.
