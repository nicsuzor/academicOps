---
title: "Spec: Session Handover YAML Frontmatter"
type: spec
status: draft
tier: backend
parent: task-168a84c9
tags: [spec, mem, yaml-schema, handover, sessions]
---

# Spec: Session Handover YAML Frontmatter

## Overview

This specification defines the structured YAML frontmatter fields added to PKB task documents to support automated session handover. These fields allow the `overwhelm-dashboard` and other tools to reconstruct session narratives, track follow-up work, and link tasks to external issues without requiring agents to write free-form "Framework Reflection" blocks.

## Field Definitions

All new fields are added to the task frontmatter. They are primarily populated via the `release_task` MCP tool at the end of an agent session.

| Field             | Type            | Optionality | Description                                                                                                                                     |
| ----------------- | --------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `session_id`      | `string`        | Optional    | Unique identifier for the session. If omitted during `release_task`, it falls back to the value of the `$AOPS_SESSION_ID` environment variable. |
| `issue_url`       | `string`        | Optional    | Full URL to a GitHub issue (e.g., `https://github.com/org/repo/issues/1`). Must be a valid URL, not just an issue number.                       |
| `pr_url`          | `string`        | Optional    | Full URL to the Pull Request. (Existing field, now part of handover).                                                                           |
| `branch`          | `string`        | Optional    | Git branch name. (Existing field, now part of handover).                                                                                        |
| `follow_up_tasks` | `array<string>` | Optional    | List of Task IDs representing work identified during the session that remains to be done.                                                       |
| `release_summary` | `string`        | Optional    | A concise summary of the work performed during the session. (Narrative for dashboard).                                                          |

## Validation Rules

The following rules are enforced by `mem` (specifically in `GraphStore` and document update logic) when writing these fields:

1. **`follow_up_tasks` Existence**: Every ID in the `follow_up_tasks` array must be resolvable via `GraphStore::resolve`. If any ID is invalid, the write operation must return an error.
2. **`release_summary` Length**: A soft warning is issued if the `release_summary` exceeds 500 characters. There is no hard limit, but agents are encouraged to keep it terse.
3. **`issue_url` Format**: If provided, must be a valid HTTPS URL pointing to a GitHub issue.

## Tool Update: `release_task`

The `release_task` MCP tool signature will be updated to support the new fields and ad-hoc task creation.

### Parameters

- `id` (**Optional**): The ID of the task to release. If omitted, ad-hoc mode is triggered.
- `status`: The completion status (e.g., `done`, `merge_ready`).
- `summary`: The text to append to the task body. For ad-hoc tasks, this is also used as the basis for the title.
- `session_id` (Optional): Explicit session ID.
- `issue_url` (Optional): GitHub issue URL.
- `pr_url` (Optional): Pull Request URL (existing field).
- `branch` (Optional): Git branch name (existing field).
- `follow_up_tasks` (Optional): Array of Task IDs.
- `release_summary` (Optional): Terse summary for the frontmatter field.

### Ad-hoc Session Tasks

- **Trigger**: `release_task` called without an `id` argument.
- **Parent**: Ad-hoc tasks are created under a named root node: `adhoc-sessions`.
- **Auto-creation**: If the `adhoc-sessions` root node does not exist in the PKB, it is automatically created.
- **Attributes**: Ad-hoc tasks receive the tags `[adhoc, session-release]` and populate the session handover fields defined above.
- **Response**: The tool returns the ID of the newly created task: `{"created_id": "task-..."}`.

## Dashboard Integration

The `overwhelm-dashboard` consumes these fields to populate the "Recent Sessions" and "Dropped Threads" views.

- **Grouping**: Tasks are grouped by session using the `session_id`.
- **Querying**: The dashboard (via `synthesize_dashboard.py` or direct MCP calls) retrieves session tasks using `list_tasks(session_id="...")`.
- **Narrative Reconstruction**: The `release_summary` field is used as the primary narrative source for the session story.

## Backfill Strategy

**Explicit NO backfill.**

Historical tasks and sessions created before the implementation of this schema will not be updated. They simply will not appear in the structured session panels of the dashboard. The system is designed to be forward-looking from the point of deployment.

## Implementation Notes (mem)

- `src/mcp_server.rs`:
  - Update `release_task` tool registration to make `id` optional and add new optional parameters.
  - Update `handle_release_task` to dispatch ad-hoc creation if `id` is missing.
- `src/document_crud.rs`:
  - Implement `follow_up_tasks` validation logic.
  - Implement ad-hoc task creation helper.
- `src/graph_store.rs`:
  - Ensure `session_id` is indexed for fast querying in `list_tasks`.
  - Ensure `adhoc-sessions` root node is properly handled/indexed.
