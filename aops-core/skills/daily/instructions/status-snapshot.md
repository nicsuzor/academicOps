# Daily Note: Status Snapshot

## 3. Status

Populate the `## Status` section with a factual snapshot of the task graph, upcoming deadlines, today's calendar, and pending decision counts. **No recommendations. No curated categories. No suggested sequences.** The user ranks their own day.

### 3.1: Load Task Data

```python
summary = mcp__pkb__task_summary()
# Returns: { "ready": N, "blocked": N,
#            "by_priority": { "p0": N, "p1": N, "p2": N, "p3": N },  # READY tasks in each class
#            "by_priority_total": { "p0": N, "p1": N, "p2": N, "p3": N },  # (future) total tasks in each class
#            "deadlines": { "overdue": N, "due_today": N, "due_this_week": N } }
```

`by_priority["pN"]` is the count of **ready** tasks in priority class N, and `ready` is the total ready count. These are the canonical numbers — **never recompute them by listing and counting tasks yourself** (P#78: aggregation is the PKB's job, not the LLM's, precisely because LLM counting is what produced the stale/impossible figures this surface exists to fix).

### 3.2: Priority Distribution

Report counts only. Do not annotate with "→ recommended tasks" pointers. Labels P0–P3 follow the canonical definitions — see [Priority Labels in TAXONOMY.md](skills/remember/references/TAXONOMY.md#priority-labels-p0p4).

**Per-class denominators.** Each P-row shows the ready count _within that priority class_ against the size of that class — **not** against the global ready total. This makes each bar a completion-progress indicator for its own class ("how much P2 work is ready vs. still blocked/in-flight"), instead of "what share of all ready work happens to be P2". The shared global denominator is the specific defect this section was changed to remove (GitHub #182 §4).

- **Numerator**: `summary["by_priority"]["pN"]` — ready tasks in class N.
- **Denominator**: the per-class total reported by `task_summary` for class N (all non-closed tasks in that class), expected under `summary["by_priority_total"]["pN"]` (P#78). Source it from `task_summary` — never count tasks yourself.

```
P0 ░░░░░░░░░░ 0/4
P1 ██░░░░░░░░ 3/14
P2 ████░░░░░░ 107/240
P3 ██████░░░░ 265/410
```

**Graceful degradation.** The currently-shipped `task_summary` emits only the ready count per class (`by_priority`), not the per-class total. Until it also emits per-class totals, render the ready count alone, with no denominator and no bar fill implying completeness:

```
P0  0
P1  3
P2  107
P3  265
```

Do **not** fabricate a denominator, reuse the global `ready` total as a stand-in, or have the LLM count tasks to synthesise one. A wrong denominator is worse than none — it reintroduces exactly the impossible-ratio failure (#182) this surface was built to prevent.

### 3.3: Deadline List

Pull tasks with `due` ≤ 7 days via `mcp__pkb__list_tasks(format=json)` and sort by due date ascending. List each on its own line:

```
- [task-id] [[Title]] — due YYYY-MM-DD (Nd away / overdue Nd)
```

### 3.3a: High-Focus Surface (Target-Driven Grouping)

After the deadline list, emit a factual block of tasks ranked by composite `focus_score` — restricted to `status` in {`queued`, `ready`, `in_progress`}. `focus_score` is the canonical composite (embeds severity, priority, downstream weight, urgency, stakeholder waiting; see [[multi-parent]] §7).

**Loading and Grouping Logic**:

1. Use `mcp__pkb__list_tasks(status=["queued","ready","in_progress"], limit=100, format="json")` and sort by `focus_score` descending. Load this once and reuse the result for the §3.3b SEV4 count.
2. **Threshold**: A task qualifies for the SEV3+ bucket when it has `urgency >= 100` (a high-urgency tier per the PKB's urgency scale; see [[multi-parent]] §7) **and** at least one entry in its `goals` field links to a target node with `severity >= 3`.
3. **Badging**: For tasks in the top list, read their `goals` field. Fetch each linked target's metadata — cache results per target ID to avoid redundant calls when multiple tasks share a target. If a linked target has `severity >= 3`, prepare an inline badge `[→[[Target Title]]]`.
4. **Display rule** (deterministic): Take the top 10 tasks by `focus_score` and split into:
   - **Target-propagated urgency (SEV3+)**: tasks meeting both criteria in step 2.
   - **Other high-focus work**: the remaining tasks from the top 10.
     Show all SEV3+ tasks first (sorted by `focus_score` descending), then Other tasks. If the SEV3+ bucket is empty, show the top 5 Other tasks. If SEV3+ is non-empty, add up to 5 Other tasks (hard ceiling: 10 total).

List each on its own line:

```
High-focus:
Target-propagated (SEV3+):
- [task-id] [[Title]] [→[[Target Title]]] — focus 0.95 (urgency 1000)
- [task-id] [[Title]] [→[[Target Title]]] — focus 0.92 (urgency 1000)

Other:
- [task-id] [[Title]] — focus 0.83 (SEV3, due 2026-05-02)
- [task-id] [[Title]] — focus 0.61 (SEV2)
```

This is **factual surfacing**, not ranking-as-recommendation — it reports what the graph computes. If `focus_score` is absent or zero across all tasks, omit this block entirely. Do **not** call `focus_score` a "priority" or attach editorial framing. Component fields like `urgency` may be filtered/displayed for debug, but ranking always goes through `focus_score`.

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
