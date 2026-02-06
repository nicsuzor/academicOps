import streamlit as st
import pandas as pd
from typing import Optional
from datetime import datetime
import os
import sys
from pathlib import Path

# Add aOps root to path if not already there (dashboard.py does this, but good for standalone testing)
# We assume this is imported by dashboard.py which sets up sys.path
from lib.task_storage import TaskStorage
from lib.task_model import Task, TaskStatus, TaskType, TaskComplexity
from lib.task_index import TaskIndex
from lib.paths import get_data_root


def _get_storage():
    return TaskStorage()


def _get_index():
    # We can use the cached index file for speed in reading
    index = TaskIndex(get_data_root())
    if not index.load():
        index.rebuild_fast()
    return index


def _get_project_options():
    # Infer projects from directory structure via TaskStorage/Index
    index = _get_index()
    # Get unique projects fro tasks
    projects = set()
    for task in index._tasks.values():
        if task.project:
            projects.add(task.project)

    # Also clean project names
    return sorted(list(projects))


def _get_project_select_options():
    """Get project options including 'Inbox' (None) for dropdowns."""
    projects = _get_project_options()
    # If using string "Inbox" to represent None, we need to handle mapping.
    # Let's just use "Inbox" as the UI label for None/empty
    return ["Inbox"] + projects


def _rebuild_index():
    """Trigger index rebuild after changes."""
    index = TaskIndex(get_data_root())
    index.rebuild()
    st.cache_data.clear()  # Clear streamlit caches if any


def render_task_manager():
    st.title("Manage Tasks")

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Tasks")

    # Project Filter
    projects = _get_project_options()
    selected_project = st.sidebar.selectbox("Project", ["All"] + projects, index=0)

    # Status Filter
    statuses = [s.value for s in TaskStatus]
    selected_status = st.sidebar.multiselect(
        "Status",
        statuses,
        default=["active", "in_progress", "blocked", "waiting", "review"],
    )

    # Search
    search_query = st.sidebar.text_input("Search", "")

    # --- Data Loading ---
    storage = _get_storage()
    index = _get_index()

    # We load from index for speed in list view
    all_tasks = list(index._tasks.values())

    # Filter
    filtered_tasks = []
    for t in all_tasks:
        if selected_project != "All" and t.project != selected_project:
            continue

        if selected_status and t.status not in selected_status:
            continue

        if search_query:
            q = search_query.lower()
            if q not in t.title.lower() and q not in t.id.lower():
                continue

        filtered_tasks.append(t)

    # Sort: Project -> Priority (asc) -> Order -> Title
    filtered_tasks.sort(
        key=lambda t: (t.project or "zzz", t.priority, t.order, t.title)
    )

    # --- Main Layout ---

    # We use a two-column layout: List and Detail
    col_list, col_detail = st.columns([1.5, 1])

    selected_task_id = None

    with col_list:
        st.subheader(f"Task List ({len(filtered_tasks)})")

        # Prepare DataFrame for display
        df_data = []
        for t in filtered_tasks:
            assignee_disp = t.assignee or ""
            df_data.append(
                {
                    "ID": t.id,
                    "Done": t.status in ("done", "cancelled", "completed", "done"),
                    "Pri": f"P{t.priority}",
                    "Title": t.title,
                    "Status": t.status,
                    "Project": t.project,
                    "Parent": t.parent,
                    "Assignee": assignee_disp,
                }
            )

        if not df_data:
            st.info("No tasks found.")
        else:
            df = pd.DataFrame(df_data)

            # Use dataframe with selection
            selection = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Done": st.column_config.CheckboxColumn("Done", width="small"),
                    "Pri": st.column_config.TextColumn("Pri", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Assignee": st.column_config.TextColumn("Owner", width="small"),
                },
                on_select="rerun",  # Rerun to update details
                selection_mode="single-row",
            )

            if selection and selection["selection"]["rows"]:
                row_idx = selection["selection"]["rows"][0]
                selected_task_id = df.iloc[row_idx]["ID"]

    # --- Task Detail / Edit ---
    with col_detail:
        if selected_task_id:
            task = storage.get_task(selected_task_id)
            if task:
                render_task_editor(task, storage)
            else:
                st.error("Task not found in storage (index might be stale).")
        else:
            st.info("Select a task to edit.")

            # Create New Task Form
            with st.expander("Create New Task", expanded=False):
                with st.form("create_task_form"):
                    new_title = st.text_input("Title")
                    new_project = st.selectbox("Project", projects)
                    new_type = st.selectbox(
                        "Type", [t.value for t in TaskType], index=3
                    )  # Default Task
                    new_parent = st.text_input("Parent ID (optional)")

                    if st.form_submit_button("Create"):
                        if new_title:
                            try:
                                t = storage.create_task(
                                    title=new_title,
                                    project=new_project
                                    if new_project != "All"
                                    else None,
                                    type=TaskType(new_type),
                                    parent=new_parent if new_parent else None,
                                )
                                storage.save_task(t)
                                _rebuild_index()
                                st.success(f"Created task {t.id}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")


def render_task_editor(task: Task, storage: TaskStorage):
    st.subheader(f"Edit: {task.id}")

    # Top Actions: Move Up/Down (Rearrange)
    col_actions = st.columns(4)
    if col_actions[0].button("⬆️ Up"):
        move_task(task, "up", storage)
        st.rerun()
    if col_actions[1].button("⬇️ Down"):
        move_task(task, "down", storage)
        st.rerun()

    with st.form(key=f"edit_{task.id}"):
        # Title
        title = st.text_input("Title", value=task.title)

        # Row 1: Status, Priority, Type
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox(
            "Status",
            [s.value for s in TaskStatus],
            index=[s.value for s in TaskStatus].index(task.status.value),
        )
        priority = c2.selectbox("Priority", [0, 1, 2, 3, 4], index=task.priority)
        ttype = c3.selectbox(
            "Type",
            [t.value for t in TaskType],
            index=[t.value for t in TaskType].index(task.type.value),
        )

        # Row 2: Project, Parent
        c4, c5 = st.columns(2)

        # handling project None -> Inbox
        proj_opts = _get_project_select_options()
        current_proj_val = task.project if task.project else "Inbox"

        if current_proj_val not in proj_opts:
            proj_opts.append(current_proj_val)

        try:
            curr_proj_idx = proj_opts.index(current_proj_val)
        except ValueError:
            curr_proj_idx = 0

        selected_project_label = c4.selectbox("Project", proj_opts, index=curr_proj_idx)
        # Convert back to None if Inbox
        project = None if selected_project_label == "Inbox" else selected_project_label

        parent = c5.text_input("Parent ID", value=task.parent or "")

        # Row 3: Order, Estimates
        c6, c7 = st.columns(2)
        order = c6.number_input("Order", value=task.order, step=1)
        # Due date text
        due_str = task.due.strftime("%Y-%m-%d") if task.due else ""
        due = c7.text_input("Due Date (YYYY-MM-DD)", value=due_str)

        # Row 4: Assignee, Complexity, Context, Effort
        c8, c9, c10, c11 = st.columns(4)
        assignee = c8.text_input("Assignee", value=task.assignee or "nic")

        # Safe complexity access/default
        curr_complexity = task.complexity.value if task.complexity else "None"
        complexity_opts = ["None"] + [c.value for c in TaskComplexity]
        complexity_idx = (
            complexity_opts.index(curr_complexity)
            if curr_complexity in complexity_opts
            else 0
        )
        complexity = c9.selectbox("Complexity", complexity_opts, index=complexity_idx)

        context = c10.text_input("Context", value=task.context or "")
        effort = c11.text_input("Effort", value=task.effort or "")

        # Row 5: Tags, Dependencies
        c12, c13 = st.columns(2)
        tags_str = ", ".join(task.tags)
        tags = c12.text_input("Tags (comma separated)", value=tags_str)

        # Dependencies display (simple text for now to avoid complexity of multi-select on 10k items)
        deps_str = ", ".join(task.depends_on)
        depends_on = c13.text_input("Depends On (IDs, comma separated)", value=deps_str)

        # Body
        body = st.text_area("Body", value=task.body, height=150)

        # Actions
        btn_col1, btn_col2 = st.columns([1, 1])
        if btn_col1.form_submit_button("💾 Save Changes", type="primary"):
            # Update task
            task.title = title
            task.status = TaskStatus(status)
            task.priority = priority
            task.type = TaskType(ttype)
            task.project = project if project else None
            task.parent = parent if parent else None
            task.order = int(order)
            task.body = body

            # New fields
            task.assignee = assignee if assignee else None
            task.context = context if context else None
            task.effort = effort if effort else None

            if complexity != "None":
                task.complexity = TaskComplexity(complexity)
            else:
                task.complexity = None

            # Parse list fields
            task.tags = [t.strip() for t in tags.split(",") if t.strip()]
            task.depends_on = [d.strip() for d in depends_on.split(",") if d.strip()]

            if due:
                try:
                    task.due = datetime.strptime(due, "%Y-%m-%d")
                except ValueError:
                    st.warning("Invalid date format, ignoring.")
            else:
                task.due = None

            storage.save_task(task)
            _rebuild_index()
            st.success("Saved!")
            st.rerun()

    # Outside form: Delete
    with st.expander("Danger Zone"):
        if st.button("🗑️ Delete Task", key=f"del_{task.id}"):
            storage.delete_task(task.id)
            _rebuild_index()
            st.warning("Deleted!")
            st.rerun()


def move_task(task: Task, direction: str, storage: TaskStorage):
    """Move task up or down among siblings."""
    # Get siblings
    siblings = []
    if task.parent:
        siblings = storage.get_children(task.parent)
    else:
        # Root tasks in same project
        all_tasks = storage.list_tasks(project=task.project)
        siblings = [t for t in all_tasks if not t.parent]

    # Sort by current order
    siblings.sort(key=lambda t: t.order)

    # Find index
    try:
        idx = next(i for i, t in enumerate(siblings) if t.id == task.id)
    except StopIteration:
        return

    target_idx = idx - 1 if direction == "up" else idx + 1

    if 0 <= target_idx < len(siblings):
        # Swap orders
        other = siblings[target_idx]

        # If orders are strictly sequential, swap values
        # If not, we might need to renounce logic.
        # Simple swap:
        current_order = task.order
        task.order = other.order
        other.order = current_order

        # If orders were identical, force a diff
        if task.order == other.order:
            if direction == "up":
                task.order -= 1
            else:
                task.order += 1

        storage.save_task(task)
        storage.save_task(other)
        _rebuild_index()
