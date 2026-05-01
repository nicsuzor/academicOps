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

Report counts only. Do not annotate with "→ recommended tasks" pointers. Use the count from `summary["ready"]` as the total of **ready tasks**. Labels P0–P3 follow the canonical definitions — see [Priority Labels in TAXONOMY.md](../../remember/references/TAXONOMY.md#priority-labels-p0p4).

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

### 3.3a: High-Urgency Surface

After the deadline list, emit a short factual block of the top 5 tasks ranked by composite `urgency` (severity × edge weight × slack × decay) — restricted to `status` in {`queued`, `ready`, `in_progress`}. Use `mcp__pkb__list_tasks(status=["queued","ready","in_progress"], limit=100, format="json")` and read each task's `urgency` field; sort descending. Load this once and reuse the result for the §3.3b SEV4 count. List one per line:

```
High-urgency:
- [task-id] [[Title]] — urgency 0.83 (SEV3, due 2026-05-02)
- [task-id] [[Title]] — urgency 0.61 (SEV2)
```

This is **factual surfacing**, not ranking-as-recommendation — it reports what the graph computes, the user still decides what to work on. If `urgency` is absent or zero across all tasks (mem-side emission not yet landed), omit this block entirely rather than falling back to an alternative ordering. Do **not** call urgency a "priority" or attach editorial framing.

### 3.3b: SEV4 Concurrency-Cap Warning

Count tasks with `severity == 4` and `status` in {`queued`, `ready`, `in_progress`} (i.e. not done/cancelled/archived). The "don't lose my job" target-node concurrency cap is **2 active SEV4 nodes**. If the count exceeds 2, emit a single-line warning at the top of the Status section:

```
⚠ SEV4 concurrency cap exceeded: N active (cap = 2). Review or downgrade before adding more.
```

If the count is ≤ 2, emit nothing. Do not editorialise about which to downgrade; that is the user's choice. If `severity` is absent on all tasks (mem-side emission not yet landed), omit the check entirely.

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
