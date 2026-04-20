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

Agents must emit a terse terminal summary at the end of a session. This replaces the `## Framework Reflection` prose block.

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

## 2. `release_task` Requirements

The `release_task` tool (and its underlying implementation in `mem` and `aops`) is updated to handle new structured fields.

### New YAML Fields

When a task is released, the following fields are written to its YAML frontmatter:

| Field             | Type          | Description                                                            |
| ----------------- | ------------- | ---------------------------------------------------------------------- |
| `session_id`      | string        | Groups tasks by session. From `$AOPS_SESSION_ID`.                      |
| `issue_url`       | string        | (Optional) GitHub issue URL.                                           |
| `follow_up_tasks` | array[string] | (Optional) Array of task IDs for future work. Must be valid PKB tasks. |
| `release_summary` | string        | One-sentence machine-readable summary (max 500 chars).                 |

**Quality Guideline**: The `release_summary` must be **result-oriented** (e.g., _"Implemented YAML schema extension for task handover"_) rather than **activity-oriented** (e.g., _"I worked on the schema"_). It is the primary signal for the human dashboard.

### Ad-hoc Task Creation

If `release_task` is called without a bound task ID (or for a task that doesn't exist), it must:

1. Create a minimal task file in the `adhoc-sessions/` directory (requires `TAXONOMY.md` update).
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

## 4. `/recap` Command

A new `/recap` command (or tool-assisted prompt) provides a terse in-session view of work done so far.

- **Implementation**: A thin wrapper around `list_tasks(session_id=$AOPS_SESSION_ID)`.
- **Output**: Terminal-friendly list of tasks touched/released in the current session.

## 5. `/dump` Fate

The `/dump` command is **retained** but rescoped. It is no longer the default session-end workflow.

- **Usage**: Emergency handover, machine/environment/project transfers, or resuming an interrupted session.
- **Implementation**: Alias for a "full" capture that includes machine state and environment context, whereas `end_session` (via `release_task`) focuses on the logical work delta.

## 6. Dashboard Integration

The "Recent Sessions" panel in the **Overwhelm Dashboard** becomes the primary human surface for post-break review.

- **Data Source**: Aggregates tasks where `session_id` matches, showing the `release_summary`, PR links, and follow-up chains.
- **Goal**: Allow a human to see "what happened" across multiple sessions without reading individual transcripts or reflection blocks.

## 7. Giving Effect

| Component            | Implementation File              | Status |
| -------------------- | -------------------------------- | ------ |
| `mem` YAML Schema    | `pkb/schemas/task.py`            | 📋     |
| `release_task` logic | `pkb/tools/task_tools.py`        | 📋     |
| `end_session` skill  | `aops-core/skills/dump/SKILL.md` | 📋     |
| `/recap` definition  | `aops-core/commands/recap.toml`  | 📋     |
| Dashboard Panel      | `scripts/synthesize_dashboard.py` | 📋     |

## 8. Backwards Compatibility

- **No shims**: Existing `## Framework Reflection` blocks are not migrated.
- **Deprecation**: Agents should be prompted to stop using the old format immediately upon implementation of this spec.
- **Breaking**: Parsers relying on regex-extraction from `## Framework Reflection` will be retired once the dashboard is fully functional. This includes `aops-core/lib/reflection_detector.py`, which should be explicitly deprecated at implementation time.
