# Reconcile: GH ↔ PKB Close-the-Loop Design

_Design-only artefact. Implementation is downstream (PR1–PR3). Filed 2026-05-13 against task aops-ea3eaa53._

---

## Problem Summary

The closure loop between GitHub (issues, PRs) and the PKB task graph is partial and duplicated. `/daily`, `/sleep`, and `/supervisor` each contain ad-hoc closure logic. Matching is done by whole-word title match and branch name — shitty NLP (AXIOMS.md § 235 / A7 Edge 3). Four gap types: (1) GH issue close → PKB `gates_on` update, (2) closed-not-merged PRs excluded unconditionally, (3) manual `gh issue close` with `state_reason` not reconciled, (4) PKB task done → GH comment/close absent.

---

## File Layout

```
aops-core/lib/reconcile/        ← canonical owner (algorithm + I/O)
    __init__.py
    match.py                    ← matching logic (mechanical + semantic dispatch)
    sync.py                     ← read/write: PKB MCP, gh-pkb-deltas.json
    backfill.py                 ← one-time migration agent
    schema.py                   ← artefact schema (dataclasses)

aops-core/skills/reconcile/
    DESIGN.md                   ← this file
    SKILL.md                    ← agent-facing triage surface (on-demand only)

scripts/
    reconcile.py                ← CLI entrypoint (--full | --forward | --reverse | --backfill)
```

**Callsites (three, no others)**:

1. `repo-sync-cron.sh` → `reconcile.py --forward` (after updating `pr-state.json`)
2. `pkb__complete_task` hook → `reconcile.py --reverse <task-id>`
3. `/reconcile` skill → `reconcile.py --full` (on-demand, user-triggered)

---

## Frontmatter Marker Spec

Two new PKB task frontmatter fields:

### `closes_issues: [N, M]`

- **Semantics**: this task's completion directly resolves GH issues N and M. On PKB task completion (reverse hook fires), all listed issues get a GH comment + conditional close.
- **Auto-close condition**: only for issues in framework-owned repos (defined in `polecat.yaml`). All other repos: comment only.
- **Validation**: integer values only. PKB lint warns if listed issue is already closed at write time.

### `gates_on: [N, M]`

- **Semantics**: this task's progress is blocked/monitored by GH issues N and M. When any listed issue closes (forward cron detects it), the task receives a `needs_user_call` event unless the task has already been completed.
- **Does not auto-close**: detecting a `gates_on` event never auto-closes the PKB task. User decides disposition.
- **Both fields present**: legal and distinct. `closes_issues` governs the reverse direction. `gates_on` governs the forward direction (unblocking events). A task may own both — e.g., "I am blocked on #123 and will resolve #123 when I complete."
- **Lint rule (PR1)**: any task where the same issue number appears in both `closes_issues` and `gates_on` simultaneously emits a warning (probable data entry error, not a hard block).

---

## Artefact Schema: `gh-pkb-deltas.json`

Path: `$AOPS_SESSIONS/state/gh-pkb-deltas.json`
Contract: append-only event log. Events older than 48h are pruned on write. Concurrency primitive: file lock via `sync.py` (same pattern as `pr-state.json`).

```json
{
  "schema_version": 1,
  "events": [
    {
      "id": "<uuid4>",
      "ts": "<ISO8601>",
      "direction": "forward | reverse",
      "trigger": "pr_merged | issue_closed | task_completed | full_sweep",
      "source": {
        "type": "pr | issue | task",
        "repo": "owner/repo",
        "ref": "<PR number, issue number, or task-ID>"
      },
      "matched_by": "pr_url | closes_issues | gates_on | task_id_in_body | agent_semantic | unmatched",
      "action_taken": "task_completed | task_needs_user_call | gh_issue_closed | gh_comment_added | none",
      "target": {
        "type": "task | issue",
        "ref": "<task-ID or issue number>"
      },
      "notes": "<optional string>"
    }
  ]
}
```

### `needs_user_call` Rendering Contract

Consumer: `/daily` Step 7 (Task Completion Sweep) — the only consumer. On each `/daily` run, `sync.py` is queried for events with `action_taken == "task_needs_user_call"` and `ts` within last 48h. These render under **"What Needs Attention → Needs your call"** as: `[task-ID] <task title> — <notes field>` with the source GH link. No other consumer renders this flag. Writing `needs_user_call` events without `/daily` as consumer is an A8 violation.

---

## Three Matching Surfaces

### (a) Guaranteed structured → mechanical (no agent)

| Signal               | Source           | Lookup                                                                     |
| -------------------- | ---------------- | -------------------------------------------------------------------------- |
| `pr_url` frontmatter | task frontmatter | exact string match against `pr-state.json` PR URL                          |
| `closes_issues: [N]` | task frontmatter | `gh issue view N --json state` → `state == "CLOSED"`                       |
| `gates_on: [N]`      | task frontmatter | same issue state check                                                     |
| Task ID in PR body   | PR body text     | regex `[a-z]+-[0-9a-f]{8}` (matches `task-*`, `aops-*`, etc.; regex on structured string field, not prose) |
| `Closes #N` trailers | GitHub API       | `closingIssuesReferences` field (structured API response — not prose)      |

### (b) Semantic → agent invocation (never mechanical)

Each semantic question is a single Claude call. Input is a structured prompt with named fields. Output is a typed JSON answer (match bool, confidence enum, reason string).

| Question                                                  | Inputs                                                 | Output shape                                                                 |
| --------------------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Does this PR correspond to this task?                     | PR title, task title, task body excerpt                | `{match: bool, confidence: high/low, reason: str}`                           |
| Is this closed-not-merged PR superseded?                  | PR body, PR timeline, linked issues                    | `{superseded_by: int\|null, task_disposition: close\|hold\|needs_user_call}` |
| Does this manually closed issue correspond to a PKB task? | issue title, body, labels; top-5 PKB search candidates | `{task_id: str\|null, confidence: high/low, reason: str}`                    |

Confidence `low` always routes to surface (c). Confidence `high` with `match: true` routes to auto-action only for `pr_merged` trigger; all other triggers route to (c) regardless of confidence (user retains final judgment).

### (c) Ambiguous → `needs_user_call`

Written to `gh-pkb-deltas.json` with `action_taken: "task_needs_user_call"` when:

- Agent returns `confidence: low`
- `state_reason: not_planned` or `state_reason: duplicate` on manual issue close
- Closed-not-merged PR with no superseding PR identified by agent
- `gates_on` event fires but task has multiple blocking issues (user decides whether to unblock)

---

## PR Phasing Plan

- **PR0 (Backfill)**: Agent-driven one-time migration: reads all open issue bodies and task bodies for prose patterns, dispatches Claude for each to classify relationship type, injects `closes_issues:` or `gates_on:` frontmatter via PKB MCP, writes ambiguous cases to `gh-pkb-deltas.json` for `/daily` surfacing. Runs after PR1 lands.
- **PR1 (Library + thin skill + `--full` only)**: `aops-core/lib/reconcile/` module, `scripts/reconcile.py --full`, `SKILL.md`, PKB lint for new frontmatter fields, this DESIGN.md. No cron wiring, no hook wiring.
- **PR2 (Forward cron + issue-state.json)**: Wire `repo-sync-cron.sh` to call `reconcile.py --forward`; add `issue-state.json` (GH issue open/closed per repo, same 24h TTL contract); implement issue-closed → `gates_on` and PR-merged → `closes_issues` handlers; `/daily` reads `gh-pkb-deltas.json` for `needs_user_call` rendering.
- **PR3 (Reverse hook)**: Wire `pkb__complete_task` hook to `reconcile.py --reverse <task-id>`; implement reverse direction (GH comment always, GH close conditionally); restrict auto-close to framework-owned repos with explicit `closes_issues:` marker.

---

## DRY Verification Grep

After each PR merges, run:

```bash
grep -rn "auto-close\|merged PR\|Closes #\|gates_on" \
  --include="*.md" --include="*.py" --include="*.sh" \
  aops-core/skills/daily/ aops-core/skills/sleep/ \
  aops-core/skills/supervisor/ aops-core/hooks/
```

Expected: zero matches. Any match is a revert trigger. The grep is a pre-merge gate on PR2 and PR3.

---

## Legacy Backfill Story

**Who**: human-dispatched agent session, not automated cron.
**When**: after PR1 (frontmatter fields + lint exist), before PR2 (so cron has clean data on first run).
**What it does**: `backfill.py` iterates all open GH issues and all non-done PKB tasks. Before dispatching Claude, a structural pre-filter (`#\d+` present in body) reduces the candidate set to items that mention any GH reference at all — this is not prose classification, just candidate gating. For each candidate, a Claude call classifies the relationship type (`closes_issues` vs `gates_on` vs no relationship). The agent writes `closes_issues:` or `gates_on:` to task frontmatter via PKB MCP. It does not use regex on prose — the agent reads the prose.
**Ambiguous surfacing**: where the agent cannot determine relationship type (e.g., bare `#123` with no verb), an event is written to `gh-pkb-deltas.json` with `action_taken: "task_needs_user_call"` and a note quoting the ambiguous phrase. These surface in the next `/daily` "Needs your call" block.
**Backfill scope**: 282 open issues + PKB tasks in `queued`, `in_progress`, `review`, `merge_ready` status only. Closed/done records are read-only.
