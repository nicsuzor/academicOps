# Hierarchy Quality Rules (P#73)

To prevent task map fragmentation and orphan tasks, all task creation MUST adhere to these structural rules.

## Rule 1: Mandatory Parent Linkage

Every task created with a `project` MUST have a `parent` set.

- If the task is part of an epic, set `parent: <epic-id>`.
- If the task is a new workstream, set `parent: <project-id>`.
- **Never** set `parent: null` when a project is known.

## Rule 2: The WHY Test

Every task MUST answer: **"Why does this exist in the context of its parent?"**
If you can't articulate the purpose in terms of the parent's goals, the task is either misplaced or missing an intermediate epic.

## Rule 3: Match Type to Scale

- **EPIC**: Multi-session work toward a milestone.
- **TASK**: Discrete deliverable (1-4 hours).
- **ACTION**: Single work session step (< 30 minutes).

## Rule 4: Star Pattern Prevention

Avoid nodes with > 5 direct children. If a project or epic has too many children, group related tasks under new intermediate epics.
