# Mobile Capture Triage

Process unprocessed notes captured via iPhone shortcut or quick-capture workflow.

## 1.5.1: Scan for Unprocessed Captures

```bash
# Find captures where processed: false (or missing processed field)
Glob: notes/mobile-captures/*.md
```

Read each file. A capture is **unprocessed** if:

- `processed: false` in frontmatter, OR
- No `processed` field in frontmatter

If no unprocessed captures exist, skip to step 2 (email briefing).

## 1.5.2: Present Captures for Triage

For each unprocessed capture, present to user with triage options:

```markdown
## Mobile Captures (N unprocessed)

1. **"Register microcommons"** (2026-02-10)
2. **"Faster note processing idea"** (2026-01-17)

What should we do with these?
```

Use `AskUserQuestion` for each capture (or batch if the user prefers):

**Triage actions:**

- **→ Task**: Create a task via `mcp__pkb__create_task()` with content from the capture. Ask user for project/priority if not obvious.
- **→ Note**: Keep as-is in `notes/mobile-captures/`, just mark processed. The note is already stored.
- **→ Expand**: The idea needs fleshing out. Create a task with `type: learn` or `type: feature` and include the raw capture as the body.
- **→ Discard**: The idea is stale or no longer relevant. Mark processed.

## 1.5.3: Mark Processed

After each capture is triaged, update its frontmatter:

```yaml
processed: true
processed_date: 2026-02-17
triage_action: task  # or: note, expand, discard
triage_ref: aops-abc123  # task ID if created, omit otherwise
```

Use the Edit tool to update the frontmatter in place.

## 1.5.4: Record in Daily Note

Add a summary to the daily note under `## Mobile Captures` (insert before `## FYI`):

```markdown
## Mobile Captures

- **Register microcommons** → Task [aops-xyz] in [[project-name]]
- **Faster note processing** → Discarded (implemented)

_2 captures processed_
```

If captures were triaged on a previous run today, update the section incrementally.
