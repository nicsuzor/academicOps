# WORKERS — Worker Registry

The configuration source the supervisor consults at dispatch time. Modify
this file to add workers, change cost/speed profiles, capacity limits, or
selection rules — without editing the skill instructions themselves.

> Referenced from [[instructions/worker-dispatch]] and [[SKILL.md]]. The
> supervisor reads this file fresh on each ORIENT pass, so changes here take
> effect on the next dispatch decision.

---

## Worker Types

Three worker types are wired into the supervisor today:

| Worker   | Engine             | Dispatch                               | Sandbox        | Async? |
| -------- | ------------------ | -------------------------------------- | -------------- | ------ |
| `claude` | Claude (Anthropic) | `polecat run -t <id> -p <project>`     | local worktree | No     |
| `gemini` | Gemini (Google)    | `polecat run -t <id> -p <project> -g`  | local worktree | No     |
| `jules`  | Jules (Google)     | `aops task <id> \| jules new --repo …` | Google infra   | Yes    |

`claude` and `gemini` are the two polecat flavours: same dispatcher, same
worktree pattern, different underlying CLI. `jules` is a different beast —
asynchronous, runs on Google infrastructure, returns a session URL and
requires human approval on the Jules web UI before a PR appears.

---

## Capabilities Matrix

| Capability                         | claude |   gemini    |           jules           |
| ---------------------------------- | :----: | :---------: | :-----------------------: |
| File edits in repo worktree        |   ✓    |      ✓      |             ✓             |
| Multi-file refactors               |   ✓    |      ⚠      |             ✓             |
| Test execution / verification      |   ✓    |      ✓      |             ✓             |
| Critic-gated / high-blast-radius   |   ✓    |      ✗      |             ✗             |
| Methodology / academic-integrity   |   ✓    |      ✗      |             ✗             |
| Bulk mechanical edits (low risk)   |   ✓    |      ✓      |             ✓             |
| Survives local network drop        |   ✗    |      ✗      |             ✓             |
| Triggers PR pipeline automatically |   ✓    |      ✓      | ⚠ (after web-UI approval) |
| MCP tool surface (PKB, etc.)       |  full  | partial[^1] |          partial          |
| Headless / non-interactive         |   ✓    |      ✓      |             ✓             |

[^1]: Gemini workers have known boot-time stderr noise — see [[SKILL.md]] "Known Limitations" for the full list. Do not halt on stderr keywords.

`⚠` = works but has caveats (see Known Limitations in SKILL.md).

---

## Cost / Speed Profiles

Subjective 1–5 scale (1 = cheapest/fastest, 5 = most expensive/slowest).
These are working hypotheses, not benchmarks — revise with evidence.

| Worker   | Cost |               Speed (time-to-first-commit)                | Quality on novel reasoning |
| -------- | :--: | :-------------------------------------------------------: | :------------------------: |
| `claude` |  4   |                   2 (typically <2 min)                    |             5              |
| `gemini` |  2   |      5 (15–20+ min before first commit — don't poll)      |             3              |
| `jules`  |  3   | 5 (async; minutes-to-hours; needs human approval to push) |             4              |

**Trade-off summary**:

- `claude` — high quality, fast, expensive. Default for any task that
  requires judgment, methodology, or critic-gated dispatch.
- `gemini` — cheap, slower-to-start, OK for mechanical / bulk work where
  quality variance is tolerable.
- `jules` — runs off-host, survives the local environment dying mid-task,
  but the human-approval gate on jules.google.com makes it unsuitable for
  anything time-sensitive.

---

## Capacity Limits (Max Concurrent)

Hard guidance for parallel dispatch on a single host. Polecat itself does
not enforce these — the supervisor must check before firing the next worker.

| Worker   | Max concurrent (default host) | Limiting factor                                                   |
| -------- | :---------------------------: | ----------------------------------------------------------------- |
| `claude` |               4               | API rate limits + host CPU / context                              |
| `gemini` |               2               | Slower wall-clock per task; CPU-bound boot                        |
| `jules`  |               8               | Off-host; constrained by Jules account quota, not local resources |

Override locally by setting capacity in the epic body's Supervisor State
block if the host can clearly handle more (e.g. a beefy crew machine).

**Counting rule**: count tasks with `assignee == <worker>` AND
`status == in_progress` against the limit. `merge_ready` does not count —
the worker has released the task and exited.

**At-capacity behaviour** (see [[instructions/worker-dispatch#worker-selection]]):

1. Try the fallback worker if task capabilities permit.
2. Otherwise, leave task in `queued` and dispatch on the next ORIENT pass.

---

## Selection Rules

Applied in priority order during DISPATCH (worker-dispatch.md Step 2).

### 1. Complexity Routing

Map `task.complexity` (or `task.effort`) to a default worker. Effort drives
the polecat `--max-turns` budget (XS=40, S=70, M=100, L=150).

| Complexity / Effort | Default worker | Rationale                                                                        |
| ------------------- | -------------- | -------------------------------------------------------------------------------- |
| `XS`                | `gemini`       | Trivial single-file edits — gemini's quality variance is tolerable, cost matters |
| `S`                 | `claude`       | A few files, still want judgment                                                 |
| `M`                 | `claude`       | Typical PR-scoped work                                                           |
| `L`                 | `claude`       | Multi-component / epic-shaped — quality dominates                                |

### 2. Tag Routing

| Tag(s) on task                                           | Worker                                            |
| -------------------------------------------------------- | ------------------------------------------------- |
| `high-risk`, `irreversible`, `production`, `destructive` | `claude` only — and route through the critic gate |
| `methodology`, `academic-integrity`, `published-output`  | `claude` only — never delegate judgment           |
| `bulk`, `mechanical`, `find-replace`, `rename`           | `gemini` preferred                                |
| `async-ok`, `long-running`, `off-host`                   | `jules` preferred                                 |

If a task carries both a high-stakes and a bulk tag, high-stakes wins.

### 3. Heuristic Thresholds

| Signal                                                                        | Action                                                    |
| ----------------------------------------------------------------------------- | --------------------------------------------------------- |
| Files affected > 20                                                           | Prefer `claude` (coordination overhead)                   |
| Estimated effort > 4 hours of agent wall-time                                 | Prefer `jules` (async — survives lid close)               |
| Task body explicitly references methodology, citations, or research integrity | `claude` only                                             |
| Pre-dispatch validation failed once already                                   | Surface to human; do not auto-retry on a different worker |

### 4. Default

If no rule above fires: **`claude`**. Safety-first default — pay more for
quality unless an explicit signal says otherwise.

---

## Recommended Use Cases

**`claude`**:

- Anything critic-gated (high-risk, irreversible, methodology)
- Net-new code with non-trivial design decisions
- Bug fixes that require root-cause analysis
- Decomposition / planning tasks (where judgment IS the deliverable)
- Tasks that touch academic outputs published under the user's name

**`gemini`**:

- Mechanical refactors (rename, move, find-replace at scale)
- Sweep tasks (apply lint rule across many files)
- XS-effort cleanup tasks where cost matters and review will catch errors
- Tasks where the human is happy to discard the worktree if quality is poor

**`jules`**:

- Long-running tasks (>4 h wall-time) where local network is unreliable
- "Try it on Google's box" tasks for cross-checking claude/gemini output
- Tasks where the human approving on the Jules web UI is part of the
  intended review loop, not friction

---

## Failure Modes per Worker

Quick reference — full details in [[SKILL.md]] "Known Limitations".

| Worker   | Common failure                           | Detection                                    | Recovery                                         |
| -------- | ---------------------------------------- | -------------------------------------------- | ------------------------------------------------ |
| `claude` | Turn budget exhausted                    | `Reached max turns` in stderr                | Raise `effort` tag; investigate over-exploration |
| `gemini` | Boot-time stderr noise (cosmetic)        | Loud-looking warnings during startup         | Ignore unless terminal exit-non-zero             |
| `gemini` | Slow first commit (15–20 min)            | No PR after 5 min                            | Don't poll; wait for `polecat finish` or PR URL  |
| `jules`  | Session "Completed" but no PR            | `jules remote list --session` shows complete | User must approve push on jules.google.com       |
| any      | Auto-finish override loop (already-done) | Repeated reset to `queued`                   | Mark task `done` manually (see `aops-fdc9d0e2`)  |
| any      | Stuck `in_progress`, no worktree         | `polecat list` empty                         | `polecat reset-stalled --hours 0 --force`        |

---

## Updating This File

When a worker type is added, removed, or a profile materially changes:

1. Update the relevant table(s) above.
2. Confirm all 4 cross-references in [[instructions/worker-dispatch]]
   still resolve to a section heading (`Worker Types`, `Selection Rules`,
   `Cost / Speed Profiles`, `Capacity Limits`).
3. If selection rules change, log the rationale in the project PKB —
   capacity numbers in particular should be evidence-backed (a dogfood run,
   an outage, observed throughput), not vibes.
