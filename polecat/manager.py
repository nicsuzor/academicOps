#!/usr/bin/env python3
import sys
import os
import fcntl
import subprocess
import shutil
from pathlib import Path

import yaml

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports will fail here but work when moved to academicOps
try:
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
except ImportError:
    pass


# Config file location (private, not in public repo)
POLECAT_CONFIG = Path.home() / ".aops" / "polecat.yaml"


def load_config() -> dict:
    """Load full polecat config from file.

    Returns:
        Dict with projects and crew_names
    """
    if not POLECAT_CONFIG.exists():
        raise FileNotFoundError(
            f"Polecat config not found: {POLECAT_CONFIG}\n"
            f"Create it with your project definitions. See polecat docs for format."
        )

    with open(POLECAT_CONFIG) as f:
        return yaml.safe_load(f)


def load_projects() -> dict:
    """Load project registry from config file.

    Returns:
        Dict mapping project slug to config (path, default_branch)
    """
    config = load_config()

    projects = {}
    for slug, proj in config.get("projects", {}).items():
        path = proj.get("path", "")
        # Expand ~ in paths
        if path.startswith("~"):
            path = Path(path).expanduser()
        else:
            path = Path(path)
        projects[slug] = {
            "path": path,
            "default_branch": proj.get("default_branch", "main"),
        }
    return projects


def load_crew_names() -> list[str]:
    """Load crew names from config file.

    Returns:
        List of crew names for random selection
    """
    config = load_config()
    return config.get("crew_names", ["crew"])

class PolecatManager:
    def __init__(self):
        # Global location for all active agents
        self.polecats_dir = Path.home() / ".aops" / "polecat"
        self.polecats_dir.mkdir(parents=True, exist_ok=True)

        # Hidden directory for bare mirror repos
        self.repos_dir = self.polecats_dir / ".repos"
        self.repos_dir.mkdir(exist_ok=True)

        # Directory for persistent crew workers (consolidated under polecats)
        self.crew_dir = self.polecats_dir / "crew"
        self.crew_dir.mkdir(exist_ok=True)

        # Load project registry from config file
        self.projects = load_projects()

        # Load crew names for random selection
        self.crew_names = load_crew_names()

        # We still need access to the task DB
        self.storage = TaskStorage()

    def generate_crew_name(self) -> str:
        """Generate a random crew name, avoiding active crew names."""
        import random

        active_crew = self.list_crew()
        available = [n for n in self.crew_names if n not in active_crew]

        if not available:
            # All names in use, add a suffix
            base = random.choice(self.crew_names)
            suffix = random.randint(1, 99)
            return f"{base}_{suffix}"

        return random.choice(available)

    def list_crew(self) -> list[str]:
        """List active crew worker names."""
        if not self.crew_dir.exists():
            return []
        return [d.name for d in self.crew_dir.iterdir() if d.is_dir()]

    def setup_crew_worktree(self, name: str, project: str) -> Path:
        """Creates a persistent crew worktree for interactive work.

        Unlike polecat worktrees (task-scoped, ephemeral), crew worktrees
        are named and persist across sessions.

        Uses the local project repo (from polecat.yaml) as source instead of
        cloning from origin. This is faster and works offline.

        Args:
            name: Crew worker name (e.g., "audre", "marsha")
            project: Project slug to work on

        Returns:
            Path to the crew worktree
        """
        if project not in self.projects:
            raise ValueError(f"Unknown project: {project}. Known: {list(self.projects.keys())}")

        # Get project config - use local repo path directly
        project_config = self.projects[project]
        local_repo_path = project_config["path"]
        default_branch = project_config.get("default_branch", "main")

        if not local_repo_path.exists():
            raise FileNotFoundError(f"Local repo not found: {local_repo_path}")

        crew_path = self.crew_dir / name
        crew_path.mkdir(exist_ok=True)

        worktree_path = crew_path / project
        branch_name = f"crew/{name}"

        if worktree_path.exists():
            # Already exists, just return it
            return worktree_path

        print(f"Creating crew worktree at {worktree_path} from local repo {local_repo_path}...")

        # Check if branch already exists in local repo
        if self._branch_exists(local_repo_path, branch_name):
            # Use existing branch
            cmd = ["git", "worktree", "add", str(worktree_path), branch_name]
        else:
            # Create new branch from default branch
            cmd = ["git", "worktree", "add", "-b", branch_name, str(worktree_path), default_branch]

        subprocess.run(cmd, cwd=local_repo_path, check=True)
        return worktree_path

    def nuke_crew(self, name: str, force: bool = False):
        """Remove a crew worker and all their worktrees.

        Args:
            name: Crew worker name
            force: Skip merge verification
        """
        crew_path = self.crew_dir / name
        if not crew_path.exists():
            raise ValueError(f"Crew worker not found: {name}")

        # Remove each project worktree
        for project_dir in crew_path.iterdir():
            if project_dir.is_dir():
                project = project_dir.name
                branch_name = f"crew/{name}"

                # Use local repo path from projects config
                if project in self.projects:
                    repo_path = self.projects[project]["path"]
                else:
                    # Fallback to mirror if project not in config
                    repo_path = self.repos_dir / f"{project}.git"

                if repo_path.exists():
                    # Safety check
                    if not force and self._branch_exists(repo_path, branch_name):
                        if not self._is_branch_merged(repo_path, branch_name):
                            raise RuntimeError(
                                f"Branch {branch_name} has unmerged commits. "
                                f"Use --force to delete anyway."
                            )

                    # Remove worktree
                    subprocess.run(
                        ["git", "worktree", "remove", "--force", str(project_dir)],
                        cwd=repo_path,
                        check=False,
                    )

                    # Delete branch
                    if self._branch_exists(repo_path, branch_name):
                        subprocess.run(
                            ["git", "branch", "-D", branch_name],
                            cwd=repo_path,
                            check=False,
                        )

        # Remove crew directory
        if crew_path.exists():
            shutil.rmtree(crew_path)

        print(f"Nuked crew worker: {name}")

    def get_repo_path(self, task) -> Path:
        """Returns the repository path to use as source for the worktree.

        Prefers bare mirror in ~/.aops/polecat/.repos/ if it exists (for isolation).
        Falls back to local project path from config.
        """
        project = task.project or "aops"

        # Check for bare mirror first
        mirror_path = self.repos_dir / f"{project}.git"
        if mirror_path.exists():
            return mirror_path

        if project in self.projects:
            return self.projects[project]["path"]

        # Default fallback
        return REPO_ROOT

    def _get_remote_url(self, repo_path: Path) -> str:
        """Gets the origin remote URL from a git repository."""
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def ensure_repo_mirror(self, project: str) -> Path:
        """Creates or updates a bare mirror clone for the project.

        Derives the remote URL from the actual repo's git config (not hardcoded).

        Args:
            project: Project slug (must exist in PROJECTS registry)

        Returns:
            Path to the bare mirror repo (.repos/<project>.git)

        Raises:
            ValueError: If project not in registry
            FileNotFoundError: If source repo doesn't exist
            subprocess.CalledProcessError: If git operations fail
        """
        if project not in self.projects:
            raise ValueError(f"Unknown project: {project}. Known: {list(self.projects.keys())}")

        config = self.projects[project]
        source_path = config["path"]
        mirror_path = self.repos_dir / f"{project}.git"

        if not source_path.exists():
            raise FileNotFoundError(f"Source repo not found: {source_path}")

        if mirror_path.exists():
            # Update existing mirror
            print(f"Fetching latest for {project}...")
            subprocess.run(
                ["git", "fetch", "--all", "--prune"],
                cwd=mirror_path,
                check=True,
            )
        else:
            # Derive remote URL from source repo
            remote_url = self._get_remote_url(source_path)
            print(f"Cloning {project} from {remote_url}...")
            subprocess.run(
                ["git", "clone", "--bare", remote_url, str(mirror_path)],
                check=True,
            )
            # Configure fetch refspec to get all branches
            subprocess.run(
                ["git", "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*"],
                cwd=mirror_path,
                check=True,
            )

        return mirror_path

    def safe_sync_mirror(self, project: str) -> bool:
        """Safely syncs a mirror without pruning refs.

        Unlike ensure_repo_mirror() which uses --prune, this method only fetches
        new commits. Safe to run while worktrees are active.

        Args:
            project: Project slug

        Returns:
            True if sync succeeded, False if failed (non-fatal for offline operation)
        """
        mirror_path = self.repos_dir / f"{project}.git"

        if not mirror_path.exists():
            # No mirror to sync - caller should use ensure_repo_mirror() first
            print(f"⚠ No mirror for {project} - skipping sync")
            return False

        try:
            print(f"Syncing {project} mirror (safe mode)...")
            subprocess.run(
                ["git", "fetch", "--all"],  # NO --prune flag
                cwd=mirror_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠ Mirror sync failed for {project}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            # Network errors, etc - non-fatal for offline operation
            print(f"⚠ Mirror sync failed for {project}: {e}", file=sys.stderr)
            return False

    def check_mirror_freshness(self, project: str) -> tuple[bool, str]:
        """Checks if mirror is up-to-date with origin.

        Compares the mirror's main branch HEAD to the local repo's main branch.

        Args:
            project: Project slug

        Returns:
            Tuple of (is_fresh, message) where is_fresh is True if up-to-date
        """
        if project not in self.projects:
            return False, f"Unknown project: {project}"

        mirror_path = self.repos_dir / f"{project}.git"
        if not mirror_path.exists():
            return False, f"No mirror exists for {project}"

        config = self.projects[project]
        local_path = config["path"]
        default_branch = config.get("default_branch", "main")

        if not local_path.exists():
            return False, f"Local repo not found: {local_path}"

        try:
            # Get mirror's HEAD for the default branch
            mirror_result = subprocess.run(
                ["git", "rev-parse", f"refs/heads/{default_branch}"],
                cwd=mirror_path,
                capture_output=True,
                text=True,
            )
            if mirror_result.returncode != 0:
                return False, f"Mirror missing branch {default_branch}"
            mirror_head = mirror_result.stdout.strip()

            # Get local repo's HEAD for the default branch
            local_result = subprocess.run(
                ["git", "rev-parse", f"refs/heads/{default_branch}"],
                cwd=local_path,
                capture_output=True,
                text=True,
            )
            if local_result.returncode != 0:
                return False, f"Local repo missing branch {default_branch}"
            local_head = local_result.stdout.strip()

            if mirror_head == local_head:
                return True, f"Mirror is up-to-date ({default_branch}: {mirror_head[:8]})"

            # Count commits behind
            count_result = subprocess.run(
                ["git", "rev-list", "--count", f"{mirror_head}..{local_head}"],
                cwd=local_path,
                capture_output=True,
                text=True,
            )
            if count_result.returncode == 0:
                commits_behind = count_result.stdout.strip()
                return False, f"Mirror is {commits_behind} commits behind {default_branch}"
            else:
                return False, f"Mirror HEAD ({mirror_head[:8]}) differs from local ({local_head[:8]})"

        except Exception as e:
            return False, f"Freshness check failed: {e}"

    def init_all_mirrors(self) -> dict[str, Path]:
        """Initialize bare mirrors for all registered projects.

        Returns:
            Dict mapping project slug to mirror path
        """
        results = {}
        for project in self.projects:
            try:
                results[project] = self.ensure_repo_mirror(project)
                print(f"✓ {project}")
            except Exception as e:
                print(f"✗ {project}: {e}")
                results[project] = None
        return results

    def sync_all_mirrors(self) -> dict[str, bool]:
        """Fetch latest from origin for all existing mirrors.

        Returns:
            Dict mapping project slug to success status
        """
        results = {}
        for project in self.projects:
            mirror_path = self.repos_dir / f"{project}.git"
            if not mirror_path.exists():
                print(f"⊘ {project}: no mirror (run 'polecat init' first)")
                results[project] = False
                continue
            try:
                subprocess.run(
                    ["git", "fetch", "--all", "--prune"],
                    cwd=mirror_path,
                    check=True,
                    capture_output=True,
                )
                print(f"✓ {project}")
                results[project] = True
            except subprocess.CalledProcessError as e:
                print(f"✗ {project}: {e}")
                results[project] = False
        return results

    def claim_next_task(self, caller: str, project: str = None):
        """Finds and claims the highest priority ready task."""
        tasks = self.storage.get_ready_tasks(project=project)
        
        if not tasks:
            return None

        for task in tasks:
            task_path = self.storage._find_task_path(task.id)
            if task_path is None:
                continue

            lock_path = task_path.with_suffix(".lock")

            try:
                with open(lock_path, "w") as lock_file:
                    try:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue 

                    try:
                        fresh_task = self.storage.get_task(task.id)
                        if fresh_task is None or fresh_task.status != TaskStatus.ACTIVE:
                            continue
                        if fresh_task.assignee and fresh_task.assignee != caller:
                            continue

                        fresh_task.status = TaskStatus.IN_PROGRESS
                        fresh_task.assignee = caller
                        self.storage.save_task(fresh_task)
                        return fresh_task

                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

            except Exception as e:
                print(f"Warning: Failed to claim {task.id}: {e}", file=sys.stderr)
                continue
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
        
        return None

    def setup_worktree(self, task):
        """Creates a git worktree in ~/.aops/polecat linked to the project repo.

        Before creating the worktree, performs a safe sync of the mirror (if used)
        to ensure we have the latest commits from origin. Sync failures are non-fatal
        to support offline operation.
        """
        project = task.project or "aops"

        # Safe sync before worktree creation (non-fatal for offline operation)
        mirror_path = self.repos_dir / f"{project}.git"
        if mirror_path.exists():
            self.safe_sync_mirror(project)

            # Check freshness and warn if stale
            is_fresh, message = self.check_mirror_freshness(project)
            if not is_fresh:
                print(f"⚠ {message}", file=sys.stderr)

        repo_path = self.get_repo_path(task)
        if not repo_path.exists():
            raise FileNotFoundError(f"Project repository not found at {repo_path}")

        worktree_path = self.polecats_dir / task.id
        branch_name = f"polecat/{task.id}"
        default_branch = self.projects.get(task.project or "aops", {}).get("default_branch", "main")

        if worktree_path.exists():
            # Validate it's actually a git worktree (has .git file pointing to parent repo)
            git_file = worktree_path / ".git"
            if git_file.exists():
                # Verify the worktree has valid git state (not orphan/corrupted)
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                )
                if result.returncode == 0:
                    return worktree_path
                # Worktree exists but is broken (orphan branch or corrupted)
                print(f"Worktree at {worktree_path} is corrupted, recreating...", file=sys.stderr)
            else:
                print(f"Directory {worktree_path} exists but is not a git worktree, recreating...", file=sys.stderr)
            # Remove the broken/non-worktree directory
            shutil.rmtree(worktree_path)
            # Prune stale worktree references from git
            subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False)

        print(f"Creating worktree at {worktree_path} from repo {repo_path}...")

        cmd = [
            "git", "worktree", "add",
            "-b", branch_name,
            str(worktree_path),
            default_branch
        ]

        try:
            subprocess.run(cmd, cwd=repo_path, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Worktree creation failed: {e}. Attempting recovery...", file=sys.stderr)
            if self._branch_exists(repo_path, branch_name):
                # Branch exists - delete it if orphan, then recreate
                if self._is_orphan_branch(repo_path, branch_name):
                    print(f"Branch {branch_name} is orphan, deleting...", file=sys.stderr)
                    subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
                    # Recreate with -b flag from default_branch
                    subprocess.run(cmd, cwd=repo_path, check=True)
                else:
                    # Branch exists with commits - use it
                    cmd = ["git", "worktree", "add", str(worktree_path), branch_name]
                    subprocess.run(cmd, cwd=repo_path, check=True)
            else:
                raise e

        # Post-creation validation: ensure worktree has valid history
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
        )
        if result.returncode != 0:
            # Worktree was created but is orphan - this should not happen
            print(f"ERROR: Worktree created with orphan branch at {worktree_path}", file=sys.stderr)
            print(f"Branch: {branch_name}, Default: {default_branch}", file=sys.stderr)
            # Clean up and fail
            shutil.rmtree(worktree_path)
            subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False)
            subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
            raise RuntimeError(f"Failed to create valid worktree - orphan branch detected")

        return worktree_path

    def _branch_exists(self, repo_path, branch_name):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=repo_path,
            capture_output=True
        )
        return res.returncode == 0

    def _is_orphan_branch(self, repo_path, branch_name):
        """Check if a branch exists but has no commits (orphan branch)."""
        # Check if branch exists
        if not self._branch_exists(repo_path, branch_name):
            return False

        # Try to get the commit SHA - will fail for orphan branches
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{branch_name}^{{commit}}"],
            cwd=repo_path,
            capture_output=True,
        )
        return result.returncode != 0

    def _is_branch_merged(self, repo_path: Path, branch_name: str, target: str = "main") -> bool:
        """Check if branch has been merged into target branch."""
        # Check if any commits in branch are NOT in target
        result = subprocess.run(
            ["git", "log", "--oneline", f"{target}..{branch_name}"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        # If output is empty, branch is fully merged
        return result.returncode == 0 and not result.stdout.strip()

    def nuke_worktree(self, task_id, force=False):
        """Removes the worktree and deletes the branch.

        Args:
            task_id: The task ID whose worktree should be removed
            force: If True, skip merge verification check

        Raises:
            RuntimeError: If branch has unmerged commits and force=False
        """
        # We need the task to know which repo it came from, but if we don't have it
        # (e.g. CLI just passed an ID), we might have to guess or search.
        # For simplicity, let's look up the task.
        task = self.storage.get_task(task_id)
        if task:
            repo_path = self.get_repo_path(task)
        else:
            # Fallback: assume academicOps if task deleted
            repo_path = REPO_ROOT

        worktree_path = self.polecats_dir / task_id
        branch_name = f"polecat/{task_id}"

        # Safety check: verify branch is merged before deletion
        if not force and self._branch_exists(repo_path, branch_name):
            if not self._is_branch_merged(repo_path, branch_name):
                raise RuntimeError(
                    f"Branch {branch_name} has unmerged commits. "
                    f"Use --force to delete anyway, or merge first with 'polecat merge'."
                )

        if worktree_path.exists():
            print(f"Removing worktree {worktree_path}...")
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=repo_path,
                check=False 
            )
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
        
        if self._branch_exists(repo_path, branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=repo_path,
                check=False
            )
