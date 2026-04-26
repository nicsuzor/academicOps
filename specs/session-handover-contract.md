---
status: draft
tier: 2
type: spec
title: Session Handover Contract (replacing Framework Reflection)
depends_on:
  - work-management.md
  - pr-pipeline.md
  - session-naming-convention.md
modified: 2026-04-20
---

# Session Handover Contract

This specification defines the new contract for end-of-session knowledge capture. It retires the unstructured "Framework Reflection" text block in favour of structured YAML frontmatter in PKB tasks and a terse terminal-friendly summary.

## Context & Rationale

Currently, "Framework Reflection" blocks are used to capture what happened in a session. This is brittle for programmatic consumers and often too verbose for quick human review. By moving structured data into task frontmatter, we enable robust dashboard visualisations while keeping terminal output clean.

## 1. Terminal Output (The Handover Block)

Agents must emit a terminal summary at the end of a session. This replaces the `## Framework Reflection` prose block.

### Full-form (Standard)

**Format**: 5–10 lines of markdown.
**Fields**:

- **Session ID**: `$AOPS_SESSION_ID`
- **Primary Task**: The main task ID being released.
- **Other Tasks**: (Optional) List of other tasks released or touched.
- **PR**: URL (if filed).
- **Branch**: name.
- **Issue**: URL (if bound).
- **Follow-ups**: List of task IDs created for future work.
- **Summary**: One-sentence result-oriented summary (the `release_summary` value, max 500 chars).

**Example**:

```markdown
### Session Handover

- **Session ID**: `a1b2c3d4`
- **Primary Task**: `task-efe468c0` (Retire Framework Reflection)
- **PR**: https://github.com/nicsuzor/academicOps/pull/123
- **Branch**: `feat/handover-contract`
- **Follow-ups**: `task-98face0b`, `task-228e2d6e`
- **Summary**: Implemented YAML schema extension and terminal output spec for session handover
```

### Short-form (Interactive only)

**Format**: 1–2 lines of prose.
**Usage**: For minor edits in interactive sessions where the user is still steering.
**Example**:

> Next: verify config change with user.

## 2. Structured Data Requirements

### Full-form: `release_task`

The `release_task` tool (and its underlying implementation in `mem` and `aops`) is updated to handle new structured fields. When a task is released, the following fields are written to its YAML frontmatter:

| Field             | Type          | Description                                                            |
| ----------------- | ------------- | ---------------------------------------------------------------------- |
| `session_id`      | string        | Groups tasks by session. From `$AOPS_SESSION_ID`.                      |
| `issue_url`       | string        | (Optional) GitHub issue URL.                                           |
| `follow_up_tasks` | array[string] | (Optional) Array of task IDs for future work. Must be valid PKB tasks. |
| `release_summary` | string        | One-sentence machine-readable summary (max 500 chars).                 |

**Quality Guideline**: The `release_summary` must be **result-oriented** (e.g., _"Implemented YAML schema extension for task handover"_) rather than **activity-oriented** (e.g., _"I worked on the schema"_). It is the primary signal for the human dashboard.

### Short-form: `update_task`

In the short-form branch, the agent uses `update_task` to write the latest delta (what was done, what's left) to the task body. This ensures state is captured without the overhead of a full release.

### Ad-hoc Task Creation

If `release_task` is called without a bound task ID (or for a task that doesn't exist), it must:

1. Create a minimal task file in the `adhoc-sessions/` directory (requires `aops-core/skills/remember/references/TAXONOMY.md` update).
2. Parent it to the root `adhoc-sessions` node.
3. Apply the provided fields and summary.

## 3. Session ID Model (`AOPS_SESSION_ID`)

The `session_id` is the primary join key for all session artifacts and tasks.

- **Source**: Harness `AOPS_SESSION_ID` environment variable.
- **Minting**:
  - For **Polecat** sessions: Derived from the task ID (8-char hash portion).
  - For **Manual** sessions: 8-character alphanumeric hash (e.g., from Claude/Gemini session UUID).
- **Propagation**: Must be available to all hooks and tools throughout the session.
- **Override/Fallback**: If the env var is missing, the `mem` implementation is the Source of Truth for minting a stable ID to prevent ID fragmentation across tools.

## 6. Dashboard Integration

The "Recent Sessions" panel in the **Overwhelm Dashboard** becomes the primary human surface for post-break review. Sessions are the dashboard's Source of Truth for "what happened" — the dashboard reads session data directly, with no synthesis intermediary.

### Data Surface

The dashboard assembles each session row from two sources, both keyed by `session_id`:

| Source                                       | Contents                                                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| PKB task frontmatter (keyed by `session_id`) | `release_summary`, `pr_url`, `issue_url`, `follow_up_tasks`, `branch`, task title and status               |
| `$AOPS_SESSIONS/summaries/*.json`            | Insights JSON produced by the session summary pipeline — outcome, accomplishments, friction, token metrics |

No intermediary aggregation file is written. The dashboard reads `$AOPS_SESSIONS/summaries/*.json` directly at render time and joins it against PKB task frontmatter on `session_id`.

### Aggregation Rule

The "Recent Sessions" panel unions two sets of sessions:

1. **Bound sessions**: PKB tasks grouped by `session_id`. Primary human-readable signal is `release_summary`; insights JSON from `summaries/` enriches the row when present.
2. **Unbound sessions**: Sessions present in `$AOPS_SESSIONS/summaries/` that have no PKB task referencing their `session_id` (e.g. exploratory sessions, sessions that ended without a `release_task` call). These are surfaced from the insights JSON alone.

### Deprecated: `synthesis.json`

An earlier design routed session data through a `synthesis.json` file in the brain. That file was inaccessible to the dashboard (which reads sessions, not the brain) and has been removed. The direct-read model in this section replaces it — do not reintroduce a synthesis intermediary.

## 7. Giving Effect

| Component                  | Implementation File              | Status |
| -------------------------- | -------------------------------- | ------ |
| `mem` YAML Schema          | `pkb/schemas/task.py`            | 📋     |
| `release_task` logic       | `pkb/tools/task_tools.py`        | 📋     |
| `dump` (end_session) skill | `aops-core/skills/dump/SKILL.md` | 📋     |
| `/recap` definition        | `aops-core/commands/recap.toml`  | 📋     |

## 8. Backwards Compatibility

- **No shims**: Existing `## Framework Reflection` blocks are not migrated.
- **Deprecation**: Agents should be prompted to stop using the old format immediately upon implementation of this spec.
- **Breaking**: Parsers relying on regex-extraction from `## Framework Reflection` will be retired once the dashboard is fully functional. This includes `aops-core/lib/reflection_detector.py`, which should be explicitly deprecated at implementation time.
