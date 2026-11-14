---
trigger: always_on
description: Use verb-led imperative task titles, kebab-case filenames without personal names, concise canonical task bodies, and structured review subtasks or epics.
---

## Task and Filename Naming Standard

Task titles and filenames must be brief, descriptive, and unambiguous:

- **Task titles are verb-led imperatives:** Every task title begins with an active imperative verb describing the concrete outcome to achieve (e.g., `Implement X`, `Verify Y`, `Refactor Z`).
- **No person's name in titles or filenames:** A task title, note title, or filename must **never** contain a person's name or persona prefix (e.g., no `<name>: decision: ...`, `<name>-task-...`, `for-<name>.md`). Assignment belongs exclusively in the `assigned_to` or `assignee` frontmatter field.
- **Filenames are kebab-case and purpose-driven:** All lowercase alphanumeric characters with hyphens, stating what the file contains or does.
- **Task bodies are strictly concise:** Follow the canonical template in [`specs/meta/naming-and-decisions.md`](../../specs/meta/naming-and-decisions.md) (Goal, Deliverable, Scope, Acceptance criteria, Pointers). Never add narrative sections (`Background`, `References`, `Implementation Plan`) or prose task-to-task links.
- **Parent/child is already an edge:** Setting `parent_id` links the hierarchy; do not redundantly wire edges between siblings/descendants of the parent without specific interactions. Tasks requiring review or follow-up must be structured either as a single task with internal subtasks (if single session) or as a dedicated epic with child tasks (if multi-session), never as loose siblings under an external parent.
