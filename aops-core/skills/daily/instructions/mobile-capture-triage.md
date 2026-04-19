# Mobile Capture Sweep

Process unprocessed mobile captures into durable PKB state (tasks or knowledge), then delete the originals. Git history is the archive — the `notes/mobile-captures/` directory is a holding pen, not a store.

## When this runs

After email triage (section 2) and before Focus composition (section 4). Runs on every `/daily` invocation.

## 1. Scan

List captures under `$ACA_DATA/notes/mobile-captures/`. For each file:

- Read the frontmatter.
- If `processed: true` → **skip**.
- Otherwise → unprocessed, include in the sweep.

**Empty or missing directory**: omit the captures summary entirely. Do not create an empty section. Do not error.

## 2. Route each capture

For each unprocessed capture, decide — **without asking the user** — which of these applies:

| Content signal                                                            | Route                          |
| ------------------------------------------------------------------------- | ------------------------------ |
| Verb-phrase, TODO, deadline, request for action, "I should…"              | `/q` (task)                    |
| Fact, reference, idea, observation, finding, insight worth preserving     | `/remember` (knowledge)        |
| Both an action and a reusable insight                                     | Both — create task AND persist |
| Transient thought with no durable value (e.g. "test", "asdf", duplicates) | Discard (still delete file)    |

Judge by content, not by length. "Look at the GitHub rate-limit docs before the migration" is both — a task to do the lookup, and a reminder worth pinning to the migration project's context.

### 2a. Route → task

Invoke: `Skill(skill="q", args="<concise task title>\n\n<capture body verbatim>")`

The planner in capture mode resolves project, parent, priority, and tags. Do not set these yourself unless the capture explicitly specifies them.

Record the returned task ID for step 4.

### 2b. Route → knowledge

Invoke: `Skill(skill="remember", args="<capture content + any context>")`

The remember skill decides whether to create a new document, append to an existing one, or store as a memory. Do not write to `$ACA_DATA/knowledge/` directly.

Record the returned document ID / path for step 4.

### 2c. Route → both

Invoke both skills. Link them: when creating the task, include the knowledge doc reference in the body so future readers can find the source material.

### 2d. Route → discard

No downstream call. Proceed to step 3.

## 3. Delete the original

After a capture has been successfully routed (or confirmed as discard):

```
mcp__pkb__delete(path="notes/mobile-captures/<filename>.md")
```

Git retains the history. Do not rename, archive, or flag-as-processed — the file is gone.

**Only delete after** the downstream `/q` or `/remember` call returned successfully. If routing failed, leave the capture in place and log the failure — it will be retried next run.

## 4. Summarise in the daily note

Add a brief summary under `## Mobile Captures` in the "What Needs Attention" section (sibling to FYI):

```markdown
## Mobile Captures

- **Register microcommons** → Task `[aops-xyz]`
- **GitHub rate-limit gotcha** → Knowledge: [[github-rate-limits]]
- **Faster note processing** → Task `[aops-abc]` + [[note-processing-ideas]]
- **(test)** → discarded

_4 captures processed_
```

One line per capture. Link to the created task ID (wikilink or code span per local convention) and/or knowledge doc. Do not include the capture body — the body lives in the task / knowledge now.

If this is a repeat run during the day, append new captures to the existing section; do not duplicate lines already there.

## Error handling

- `/q` fails → skip delete, log "capture <filename> routing failed: <reason>", leave for next run.
- `/remember` fails → same behaviour.
- Capture is malformed (no body, corrupt frontmatter) → log and skip; user can fix or delete manually.
