# Daily Note: Status Snapshot

## 3. Status

Populate the `## Status` section with a factual snapshot of the task graph, upcoming deadlines, today's calendar, and pending decision counts. **No recommendations. No curated categories. No suggested sequences.** The user ranks their own day.

### 3.1: Load Task Data

```python
summary = mcp__pkb__task_summary()
# Returns: { "ready": N, "blocked": N,
#            "by_priority": { "p0": N, "p1": N, "p2": N, "p3": N },
#            "deadlines": { "overdue": N, "due_today": N, "due_this_week": N } }
```

Use `summary["ready"]` as the denominator for priority bars.

### 3.2: Priority Distribution

Report counts only. Do not annotate with "→ recommended tasks" pointers. Use the count from `summary["ready"]` as the total of **ready tasks**.

```
P0 ░░░░░░░░░░ 3/85
P1 █░░░░░░░░░ 12/85
P2 ██████████ 55/85
P3 ██░░░░░░░░ 15/85
```

### 3.3: Deadline List

Pull tasks with `due` ≤ 7 days via `mcp__pkb__list_tasks(format=json)` and sort by due date ascending. List each on its own line:

```
- [task-id] [[Title]] — due YYYY-MM-DD (Nd away / overdue Nd)
```

Do **not**:

- Wrap with "🚨 DEADLINE TODAY" siren framing
- Rank within the list by "significance"
- Write "start here because..."
- Move items between categories (SHOULD/DEEP/etc)

Include `consequence` text only if the task itself carries a `consequence` field — verbatim, not paraphrased.

### 3.4: Calendar

List today's events from the calendar source in time order. Show start time, title, and location. No commentary on which matters most.

```
- 09:00 — [[Event Title]] — (location)
- 12:00 — [[Other Event]] — (location)
```

Cancelled events appear struck through with `(canceled)` suffix.

### 3.5: Pending Decisions

One line — a count, not a curated queue:

```
Pending decisions: 4 (assigned to you in ready + review status)
```

Do not enumerate or rank them here. The user can open `/decision-extract` if they want detail.

### 3.6: `### My priorities`

Ensure the `### My priorities` subsection exists (as an empty heading on first creation). Never ask the user what their priorities are, and never write content under this heading. It is a user-owned space.

If the user has written priorities on a previous run, preserve them verbatim. Do not restate them elsewhere in the note.

### 3.7: What this section does NOT contain

Explicitly forbidden — the skill previously emitted these and the user has asked for them to be removed:

- **SHOULD / DEEP / ENJOY / QUICK / UNBLOCK categories** — no curated task recommendations of any kind.
- **"Suggested sequence"** paragraphs — no rationales for what to work on first.
- **"Framework day warning"** or similar weighting ("heavy infra day, consider actual tasks"). The user decides what kind of day it is.
- **Engagement prompts** — do not `AskUserQuestion` for priorities or "how are you feeling about your workstreams". If the user wants to reset, they can invoke `/strategy` themselves.
- **Archive suggestions** — the daily note does not nominate candidate tasks for archive. Archive hygiene belongs to `/sleep` or explicit user action.

### 3.8: Stale review/merge_ready (from Task Completion Sweep)

If the task completion sweep (pipeline Step 7) identified tasks stuck >14 days in `review` or `merge_ready` with no merge/email evidence, list them here — one line each, factually:

```
Stale (>14d awaiting evidence):
- [task-id] [[Title]] — in review since YYYY-MM-DD
```

No judgment about whether to close them; that's the user's call.
