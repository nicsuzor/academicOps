from pathlib import Path

from manager import PolecatManager

manager = PolecatManager()
exclude = {".repos", "crew"}
for d in manager.polecats_dir.iterdir():
    if d.is_dir() and not d.name.startswith(".") and d.name not in exclude:
        print("Worktree:", d.name)
        task_id = d.name
        task = manager.storage.get_task(task_id)
        repo_path = manager.get_repo_path(task) if task else Path(".")
        branch_name = f"polecat/{task_id}"
        print(manager._is_branch_merged(repo_path, branch_name))

for c in manager.crew_dir.iterdir():
    if c.is_dir():
        name = c.name
        print("Crew:", name)
        # we can just nuke_crew if all branches are merged
