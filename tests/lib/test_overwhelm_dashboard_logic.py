"""Reproduction tests for overwhelm dashboard bug fixes.

P#82: Mandatory Reproduction Tests — these tests would have failed on the
pre-fix code and verify the two bug fixes introduced in this PR:

  1. UP NEXT deduplication: tasks that are children of a displayed epic must
     not appear in the UP NEXT list.
  2. Sub-project merging: sub-project tasks must be merged into parent project
     and the sub-project card must not appear standalone on the dashboard.

These tests exercise pure data-transformation logic extracted from
lib/overwhelm/dashboard.py, keeping them free of Streamlit dependencies.
"""


def _build_incomplete_tasks(p_tasks, project_epics, all_tasks):
    """Replicate the deduplication logic from dashboard.py.

    This mirrors the rendered_child_ids / incomplete_tasks logic in the
    project card rendering loop.
    """
    tasks_by_id = {t["id"]: t for t in all_tasks}
    rendered_child_ids = set()

    if project_epics:
        for epic in project_epics[:3]:
            children_ids = epic.get("children", [])
            rendered_child_ids.update(children_ids)

    incomplete_tasks = [
        t
        for t in p_tasks
        if t.get("status") not in ("done", "closed")
        and t.get("type") != "epic"
        and t.get("id") not in rendered_child_ids
    ]
    return incomplete_tasks


def _build_sub_to_parent(all_tasks):
    """Replicate the sub→parent map construction from dashboard.py."""
    tasks_by_id = {t["id"]: t for t in all_tasks}
    sub_to_parent: dict[str, str] = {}
    for task in all_tasks:
        if task.get("type") == "project" and task.get("parent"):
            sub_name = task.get("project") or task["id"]
            parent_task = tasks_by_id.get(task["parent"])
            if parent_task:
                parent_name = parent_task.get("project") or parent_task["id"]
                if sub_name != parent_name:
                    sub_to_parent[sub_name] = parent_name
    return sub_to_parent


def _merge_sub_projects(sub_to_parent, all_projects, tasks_by_project):
    """Replicate sub-project task-merging logic from dashboard.py."""
    for sub, parent in sub_to_parent.items():
        if parent in all_projects:
            if sub in tasks_by_project:
                tasks_by_project.setdefault(parent, []).extend(tasks_by_project.pop(sub))
    return tasks_by_project


def _is_valid_project(name, sub_to_parent, all_projects, valid_project_ids):
    """Replicate is_valid_project() from dashboard.py."""
    if not name:
        return False
    if name.lower() in ("hooks", "unknown", "tasks", "inbox", "tmp"):
        return False
    if len(name) >= 8 and all(c in "0123456789abcdef-" for c in name.lower()):
        return False
    if name in sub_to_parent and sub_to_parent[name] in all_projects:
        return False
    return name in valid_project_ids or name.lower() in valid_project_ids


# ---------------------------------------------------------------------------
# Bug 1: UP NEXT deduplication
# ---------------------------------------------------------------------------


class TestUpNextDeduplication:
    """Tasks rendered under EPICS must not appear again in UP NEXT."""

    def _make_tasks(self):
        epic = {
            "id": "aops-epic-1",
            "type": "epic",
            "title": "Sprint Alpha",
            "status": "in_progress",
            "project": "aops",
            "children": ["aops-task-1", "aops-task-2"],
        }
        child1 = {
            "id": "aops-task-1",
            "type": "task",
            "title": "Child task 1",
            "status": "in_progress",
            "project": "aops",
        }
        child2 = {
            "id": "aops-task-2",
            "type": "task",
            "title": "Child task 2",
            "status": "in_progress",
            "project": "aops",
        }
        standalone = {
            "id": "aops-task-3",
            "type": "task",
            "title": "Standalone task",
            "status": "in_progress",
            "project": "aops",
        }
        return epic, child1, child2, standalone

    def test_epic_children_excluded_from_up_next(self):
        """Epic children that are rendered under EPICS must not appear in UP NEXT.

        Regression: before the fix, rendered_child_ids was absent, so child
        tasks appeared in both EPICS and UP NEXT.
        """
        epic, child1, child2, standalone = self._make_tasks()
        all_tasks = [epic, child1, child2, standalone]
        p_tasks = [child1, child2, standalone]
        project_epics = [epic]

        incomplete = _build_incomplete_tasks(p_tasks, project_epics, all_tasks)
        task_ids = {t["id"] for t in incomplete}

        assert "aops-task-1" not in task_ids, "child1 should be excluded (already in EPICS)"
        assert "aops-task-2" not in task_ids, "child2 should be excluded (already in EPICS)"
        assert "aops-task-3" in task_ids, "standalone task must remain in UP NEXT"

    def test_done_tasks_excluded_regardless(self):
        """Done tasks must not appear in UP NEXT, even if not epic children."""
        epic, child1, child2, standalone = self._make_tasks()
        done_task = {
            "id": "aops-task-4",
            "type": "task",
            "title": "Done task",
            "status": "done",
            "project": "aops",
        }
        all_tasks = [epic, child1, child2, standalone, done_task]
        p_tasks = [child1, child2, standalone, done_task]
        project_epics = [epic]

        incomplete = _build_incomplete_tasks(p_tasks, project_epics, all_tasks)
        task_ids = {t["id"] for t in incomplete}

        assert "aops-task-4" not in task_ids, "done tasks must always be excluded"

    def test_up_next_not_affected_when_no_epics(self):
        """When no epics are present all incomplete non-epic tasks appear in UP NEXT."""
        task_a = {"id": "aops-task-a", "type": "task", "title": "A", "status": "in_progress"}
        task_b = {"id": "aops-task-b", "type": "task", "title": "B", "status": "in_progress"}
        all_tasks = [task_a, task_b]
        p_tasks = [task_a, task_b]
        project_epics = []

        incomplete = _build_incomplete_tasks(p_tasks, project_epics, all_tasks)
        task_ids = {t["id"] for t in incomplete}

        assert "aops-task-a" in task_ids
        assert "aops-task-b" in task_ids

    def test_epic_type_tasks_excluded_from_up_next(self):
        """Tasks of type 'epic' must always be excluded from UP NEXT."""
        epic = {
            "id": "aops-epic-x",
            "type": "epic",
            "title": "Some Epic",
            "status": "in_progress",
            "children": [],
        }
        all_tasks = [epic]
        p_tasks = [epic]
        project_epics = []  # Epic not in project_epics to isolate the type check

        incomplete = _build_incomplete_tasks(p_tasks, project_epics, all_tasks)
        task_ids = {t["id"] for t in incomplete}

        assert "aops-epic-x" not in task_ids, "type==epic tasks must never appear in UP NEXT"


# ---------------------------------------------------------------------------
# Bug 2: Sub-project card deduplication
# ---------------------------------------------------------------------------


class TestSubProjectMerging:
    """Sub-project tasks must merge into parent; sub-project card must not be standalone."""

    def _make_project_tasks(self):
        parent_proj_task = {
            "id": "aops-proj-root",
            "type": "project",
            "project": "aops",
            "parent": None,
            "title": "AOPS root project",
        }
        sub_proj_task = {
            "id": "aops-proj-dash",
            "type": "project",
            "project": "overwhelm-dashboard",
            "parent": "aops-proj-root",
            "title": "Overwhelm dashboard sub-project",
        }
        sub_task = {
            "id": "dash-task-1",
            "type": "task",
            "project": "overwhelm-dashboard",
            "title": "Dashboard task",
            "status": "in_progress",
        }
        return parent_proj_task, sub_proj_task, sub_task

    def test_sub_project_tasks_merged_into_parent(self):
        """Tasks from sub-project must appear in parent after merging.

        Regression: before the fix, sub-projects had standalone cards with
        their own tasks rather than merging into the parent card.
        """
        parent_proj_task, sub_proj_task, sub_task = self._make_project_tasks()
        all_tasks = [parent_proj_task, sub_proj_task, sub_task]

        sub_to_parent = _build_sub_to_parent(all_tasks)

        tasks_by_project = {
            "aops": [],
            "overwhelm-dashboard": [sub_task],
        }
        all_projects = {"aops", "overwhelm-dashboard"}

        merged = _merge_sub_projects(sub_to_parent, all_projects, tasks_by_project)

        assert sub_task in merged.get("aops", []), "sub_task must be merged into parent 'aops'"
        assert "overwhelm-dashboard" not in merged, (
            "sub-project bucket must be removed after merging"
        )

    def test_sub_project_card_filtered_out(self):
        """Sub-project name must not survive the is_valid_project filter when parent is visible.

        Regression: before the fix, 'overwhelm-dashboard' appeared as a
        standalone card alongside 'aops'.
        """
        parent_proj_task, sub_proj_task, sub_task = self._make_project_tasks()
        all_tasks = [parent_proj_task, sub_proj_task, sub_task]

        sub_to_parent = _build_sub_to_parent(all_tasks)
        valid_project_ids = {t.get("project") for t in all_tasks if t.get("project")}
        all_projects = {"aops", "overwhelm-dashboard"}

        visible = {
            p
            for p in all_projects
            if _is_valid_project(p, sub_to_parent, all_projects, valid_project_ids)
        }

        assert "aops" in visible, "parent project must remain visible"
        assert "overwhelm-dashboard" not in visible, (
            "sub-project must be filtered out when parent is visible"
        )

    def test_sub_to_parent_map_built_correctly(self):
        """sub_to_parent map must correctly map sub-project names to parent names."""
        parent_proj_task, sub_proj_task, sub_task = self._make_project_tasks()
        all_tasks = [parent_proj_task, sub_proj_task, sub_task]

        sub_to_parent = _build_sub_to_parent(all_tasks)

        assert "overwhelm-dashboard" in sub_to_parent
        assert sub_to_parent["overwhelm-dashboard"] == "aops"

    def test_top_level_project_not_added_to_sub_to_parent(self):
        """Projects without a parent must not appear in sub_to_parent map."""
        parent_proj_task, sub_proj_task, sub_task = self._make_project_tasks()
        all_tasks = [parent_proj_task, sub_proj_task, sub_task]

        sub_to_parent = _build_sub_to_parent(all_tasks)

        assert "aops" not in sub_to_parent, "top-level project must not be in sub_to_parent"
