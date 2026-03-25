with open("polecat/cli.py", "r") as f:
    content = f.read()

cleanup_code = """    # Target not provided, run stale cleanup
    print("No target provided. Cleaning up stale branches...")

    # 1. Cleanup stale worktrees
    if manager.polecats_dir.exists():
        exclude = {".repos", "crew"}
        for d in manager.polecats_dir.iterdir():
            if d.is_dir() and not d.name.startswith(".") and d.name not in exclude:
                task_id = d.name
                task = manager.storage.get_task(task_id) if manager.storage else None
                repo_path = manager.get_repo_path(task) if task else Path(".")
                branch_name = f"polecat/{task_id}"

                # Check if branch is merged or deleted
                is_stale = False
                if not manager._branch_exists(repo_path, branch_name):
                    is_stale = True
                elif manager._is_branch_merged(repo_path, branch_name):
                    is_stale = True

                if is_stale:
                    print(f"Nuking stale worktree: {task_id}")
                    try:
                        manager.nuke_worktree(task_id, force=True)
                    except (RuntimeError, ValueError) as e:
                        print(f"Warning: Failed to nuke {task_id}: {e}", file=sys.stderr)

    # 2. Cleanup stale crew clones
    if manager.crew_dir.exists():
        for c in manager.crew_dir.iterdir():
            if c.is_dir():
                crew_name = c.name
                branch_name = f"crew/{crew_name}"
                is_stale = False

                # We need to check if ANY of the project clones in the crew dir are stale
                # A crew is stale if all of its branches are merged or deleted
                projects = [d.name for d in c.iterdir() if d.is_dir()]
                if not projects:
                    continue

                all_stale = True
                for project in projects:
                    repo_path = manager.projects.get(project, {}).get("path")
                    if not repo_path:
                        repo_path = manager.repos_dir / f"{project}.git"

                    if not repo_path.exists():
                        continue

                    if manager._branch_exists(repo_path, branch_name):
                        if not manager._is_branch_merged(repo_path, branch_name):
                            all_stale = False
                            break

                if all_stale:
                    print(f"Nuking stale crew: {crew_name}")
                    try:
                        manager.nuke_crew(crew_name, force=True)
                    except (RuntimeError, ValueError) as e:
                        print(f"Warning: Failed to nuke crew {crew_name}: {e}", file=sys.stderr)"""

content = content.replace("    # Target not provided, run stale cleanup\n    print(\"No target provided. Cleaning up stale branches...\")", cleanup_code)

with open("polecat/cli.py", "w") as f:
    f.write(content)
