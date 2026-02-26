import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from lib.task_model import Task, TaskComplexity, TaskStatus, TaskType
from lib.task_storage import TaskStorage


def _rebuild_index():
    """Trigger rebuild of index/embeddings if needed."""
    # For now, just a placeholder.
    # In real impl, might call storage.reindex()
    pass


DEFAULT_PROJECT = "aops"


def _get_repo_url_from_project(project: str) -> str | None:
    """Get GitHub repo URL from project name via polecat.yaml."""
    config_path = Path.home() / ".aops" / "polecat.yaml"
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        projects = config.get("projects", {})
        if project not in projects:
            return None

        repo_path = Path(projects[project]["path"]).expanduser()
        if not repo_path.exists():
            return None

        # Get git remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            url = result.stdout.strip()
            # Convert git@github.com:owner/repo.git to owner/repo
            if url.startswith("git@github.com:"):
                return url.replace("git@github.com:", "").replace(".git", "")
            elif "github.com/" in url:
                # HTTPS URL
                return url.split("github.com/")[-1].replace(".git", "")

        return None
    except Exception:
        return None


def launch_polecat_agent(task: Task):
    """Launch a polecat worker for this task in background."""
    try:
        subprocess.Popen(
            ["polecat", "run", "-t", task.id],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        st.success(f"✅ Launched polecat for {task.id}")
    except FileNotFoundError:
        st.error("❌ 'polecat' command not found. Please ensure it is installed and in your PATH.")
    except Exception as e:
        st.error(f"❌ Failed to launch polecat: {e}")


def launch_jules_agent(task: Task):
    """Launch a jules agent for this task in background."""
    repo = _get_repo_url_from_project(task.project or DEFAULT_PROJECT)
    if not repo:
        st.error(f"❌ Could not find repo for project: {task.project}")
        return

    try:
        # Construct prompt: task title + body
        prompt = f"{task.title}\n\n{task.body or ''}"

        # Launch jules in background: echo "prompt" | jules new --repo owner/repo
        process = subprocess.Popen(
            ["jules", "new", "--repo", repo],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        if process.stdin:
            process.stdin.write(prompt)
            process.stdin.close()
        st.success(f"✅ Launched jules for {task.id} on {repo}")
    except FileNotFoundError:
        st.error("❌ 'jules' command not found. Please ensure it is installed and in your PATH.")
    except Exception as e:
        st.error(f"❌ Failed to launch jules: {e}")


def launch_github_agent(task: Task):
    """Launch a polecat worker in GitHub issue mode."""
    # Try to extract GitHub issue URL from task body
    import re

    issue_pattern = r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)"
    match = re.search(issue_pattern, task.body or "")

    if not match:
        st.error("❌ No GitHub issue URL found in task body")
        return

    owner, repo, issue_num = match.groups()
    issue_ref = f"{owner}/{repo}#{issue_num}"

    try:
        subprocess.Popen(
            ["polecat", "run", "--issue", issue_ref],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        st.success(f"✅ Launched polecat for issue {issue_ref}")
    except FileNotFoundError:
        st.error("❌ 'polecat' command not found. Please ensure it is installed and in your PATH.")
    except Exception as e:
        st.error(f"❌ Failed to launch github agent: {e}")


def _get_project_select_options():
    """Get list of projects for dropdown."""
    # In a real app, this would query storage for distinct projects.
    # Hardcoded for demo simplicity.
    return [
        "Inbox",
        "aops-core",
        "aops-tools",
        "aops-agent",
        "personal",
        "work",
        "learning",
    ]


def run_task_manager_ui(storage: TaskStorage):
    st.header("Task Manager UI")

    # --- Sidebar Filters ---
    with st.sidebar:
        st.subheader("Filters")
        projects = ["All"] + _get_project_select_options()
        selected_project = st.selectbox("Project", projects)

        status_options = ["All"] + [s.value for s in TaskStatus]
        selected_status = st.selectbox("Status", status_options, index=1)  # Default: Active

        search_query = st.text_input("Search (Title/Body)", "")

        show_done = st.checkbox("Show Completed", value=False)

    # --- Main Content ---
    col_list, col_detail = st.columns([1, 1])

    # Filter Logic
    all_tasks = storage.list_tasks()
    filtered_tasks = []

    for t in all_tasks:
        # Project Filter
        if selected_project != "All":
            if selected_project == "Inbox":
                if t.project:
                    continue
            elif t.project != selected_project:
                continue

        # Status Filter
        if selected_status != "All":
            if t.status.value != selected_status:
                continue

        # Show Done Filter (override status filter if needed?)
        if not show_done and t.status in (
            TaskStatus.DONE,
            TaskStatus.CANCELLED,
            TaskStatus.COMPLETED,
        ):
            continue

        # Search Filter
        if search_query:
            q = search_query.lower()
            if q not in t.title.lower() and (not t.body or q not in t.body.lower()):
                continue

        filtered_tasks.append(t)

    # Sort tasks: Priority desc, then Order asc
    filtered_tasks.sort(key=lambda x: (x.priority, x.order))

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
                    "Done": t.status in ("done", "cancelled", "completed"),
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

            if selection and selection.get("selection", {}).get("rows"):  # type: ignore[union-attr]
                row_idx = selection["selection"]["rows"][0]  # type: ignore[index]
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
                                    project=new_project if new_project != "All" else None,
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

    # Agent Launch Actions
    st.markdown("### 🤖 Launch Agent")
    agent_cols = st.columns(3)

    # Polecat Launch
    with agent_cols[0]:
        if st.button("🐱 Polecat", key=f"polecat_{task.id}", help="Launch polecat worker"):
            launch_polecat_agent(task)

    # Jules Launch
    with agent_cols[1]:
        if st.button("🔮 Jules", key=f"jules_{task.id}", help="Launch Jules agent (Google)"):
            launch_jules_agent(task)

    # GitHub Launch
    with agent_cols[2]:
        if st.button("🐙 GitHub", key=f"github_{task.id}", help="Launch as GitHub issue"):
            launch_github_agent(task)

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
            complexity_opts.index(curr_complexity) if curr_complexity in complexity_opts else 0
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
