#!/usr/bin/env python3
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from observability import metrics
from validation import validate_task_id_or_raise

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports will fail here but work when moved to academicOps
try:
    from lib.task_model import TaskStatus
    from lib.task_storage import TaskStorage
except ImportError:
    pass


def get_polecat_home() -> Path:
    """Get the polecat home directory.

    Checks in order:
    1. POLECAT_HOME environment variable
    2. Default: ~/.aops

    Returns:
        Path to the polecat home directory
    """
    env_home = os.environ.get("POLECAT_HOME")
    if env_home:
        if env_home.startswith("~"):
            return Path(env_home).expanduser()
        return Path(env_home)
    return Path.home() / ".aops"


def get_config_path(home_dir: Path | None = None) -> Path:
    """Get the polecat config file path.

    Args:
        home_dir: Optional home directory override

    Returns:
        Path to polecat.yaml config file
    """
    if home_dir is None:
        home_dir = get_polecat_home()
    return home_dir / "polecat.yaml"


# Config file location (private, not in public repo)
# This is the default, but load_config() should use get_config_path() for flexibility
POLECAT_CONFIG = get_config_path()


def load_config(config_path: Path | None = None) -> dict:
    """Load full polecat config from file.

    Args:
        config_path: Optional path to config file. Defaults to get_config_path().

    Returns:
        Dict with projects and crew_names
    """
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Polecat config not found: {config_path}\n"
            f"Create it with your project definitions. See polecat docs for format."
        )

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_projects(config_path: Path | None = None) -> dict:
    """Load project registry from config file.

    Args:
        config_path: Optional path to config file.

    Returns:
        Dict mapping project slug to config (path, default_branch)
    """
    config = load_config(config_path)

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


def load_project_aliases(config_path: Path | None = None) -> dict[str, str]:
    """Load shorthand aliases that map to project slugs.

    Aliases are defined in polecat.yaml under project_aliases, e.g.:
        project_aliases:
            bm: buttermilk

    Built-in aliases: project slugs always resolve to themselves.

    Args:
        config_path: Optional path to config file.

    Returns:
        Dict mapping alias -> project slug
    """
    config = load_config(config_path)
    aliases = dict(config.get("project_aliases", {}))
    # Every project slug is also a valid alias for itself
    for slug in config.get("projects", {}):
        aliases.setdefault(slug, slug)
    return aliases


def load_crew_names(config_path: Path | None = None) -> list[str]:
    """Load crew names from config file.

    Args:
        config_path: Optional path to config file.

    Returns:
        List of crew names for random selection
    """
    config = load_config(config_path)
    return config.get("crew_names", ["crew"])


def configure_git_credentials(repo_path: Path):
    """Configure git to use AOPS_BOT_GH_TOKEN for HTTPS authentication.

    Sets up a POSIX-compatible credential helper that provides the token
    from the AOPS_BOT_GH_TOKEN environment variable for git operations.

    Git invokes credential helpers via /bin/sh (often dash, not bash),
    so the helper must avoid bash-specific syntax like function definitions.

    Args:
        repo_path: Path to git repository or worktree
    """
    token = os.environ.get("AOPS_BOT_GH_TOKEN")
    if not token:
        return

    # POSIX-compatible: no function syntax, just a simple conditional printf.
    # Git passes the operation (get/store/erase) as the first argument.
    helper_cmd = (
        '!test "$1" = get '
        '&& printf "username=x-access-token\\npassword=%s\\n" "$AOPS_BOT_GH_TOKEN"'
    )

    subprocess.run(
        ["git", "config", "--local", "credential.helper", helper_cmd],
        cwd=repo_path,
        check=True,
    )


class PolecatManager:
    def __init__(self, home_dir: Path | None = None):
        """Initialize the polecat manager.

        Args:
            home_dir: Optional home directory override. If not specified,
                      uses POLECAT_HOME env var or defaults to ~/.aops
        """
        # Determine home directory
        if home_dir is not None:
            if isinstance(home_dir, str):
                home_dir = Path(home_dir)
            if str(home_dir).startswith("~"):
                home_dir = home_dir.expanduser()
            self.home_dir = home_dir
        else:
            self.home_dir = get_polecat_home()

        # Config file location
        self.config_path = self.home_dir / "polecat.yaml"

        # Ensure home directory exists
        self.home_dir.mkdir(parents=True, exist_ok=True)

        # Global location for all active agents (directly in home_dir)
        self.polecats_dir = self.home_dir

        # Hidden directory for bare mirror repos
        self.repos_dir = self.polecats_dir / ".repos"
        self.repos_dir.mkdir(exist_ok=True)

        # Directory for persistent crew workers
        self.crew_dir = self.polecats_dir / "crew"
        self.crew_dir.mkdir(exist_ok=True)

        # Load project registry from config file
        self.config = load_config(self.config_path)
        self.projects = load_projects(self.config_path)

        # Load crew names for random selection
        self.crew_names = load_crew_names(self.config_path)

        # Load project aliases (shorthand -> slug mapping)
        self.project_aliases = load_project_aliases(self.config_path)

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

    def resolve_project_alias(self, alias: str) -> str:
        """Resolve a project alias to its canonical slug.

        Args:
            alias: Shorthand alias (e.g., 'bm') or full slug (e.g., 'buttermilk')

        Returns:
            Canonical project slug

        Raises:
            ValueError: If alias is not recognized
        """
        if alias in self.project_aliases:
            return self.project_aliases[alias]
        # Check if it's already a valid project slug
        if alias in self.projects:
            return alias
        raise ValueError(
            f"Unknown project alias: '{alias}'. "
            f"Known aliases: {list(self.project_aliases.keys())}, "
            f"Known projects: {list(self.projects.keys())}"
        )

    def register_adhoc_project(self, repo_path: Path) -> str:
        """Register an ad-hoc project from an arbitrary repo path.

        Creates a temporary project entry so crew can work on repos
        not in polecat.yaml. The slug is derived from the directory name.

        Args:
            repo_path: Absolute path to a git repository

        Returns:
            Project slug for the ad-hoc project

        Raises:
            FileNotFoundError: If repo_path doesn't exist
            ValueError: If repo_path is not a git repository
        """
        repo_path = Path(repo_path).resolve()
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository not found: {repo_path}")
        if not (repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")

        # Derive slug from directory name
        slug = repo_path.name.lower().replace(" ", "-")

        # Detect default branch
        default_branch = "main"
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()
            default_branch = ref.rsplit("/", 1)[-1]

        self.projects[slug] = {
            "path": repo_path,
            "default_branch": default_branch,
        }
        return slug

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
            cmd = [
                "git",
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                default_branch,
            ]

        subprocess.run(cmd, cwd=local_repo_path, check=True)

        # Configure git credentials for HTTPS push
        configure_git_credentials(worktree_path)

        # Set upstream tracking to the feature branch (not main).
        # This allows 'git push' to work without requiring manual 'git push -u',
        # while preventing accidental push to main.
        print(f"🔗 Setting upstream tracking for {branch_name}...")
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", f"{branch_name}:{branch_name}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if push_result.returncode == 0:
            print(f"  ✅ Upstream set: origin/{branch_name}")
        else:
            print(
                f"  ⚠ Could not set upstream (offline?): {push_result.stderr.strip()}",
                file=sys.stderr,
            )

        # Apply sandbox settings to isolate the worker to this worktree
        self.create_sandbox_settings(worktree_path)

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

        Fetches from both origin (remote) and local repo to ensure mirror has
        all commits, including unpushed local changes.

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

        if project not in self.projects:
            print(f"⚠ Unknown project {project} - skipping sync")
            return False

        local_path = self.projects[project]["path"]

        try:
            print(f"Syncing {project} mirror (safe mode)...")
            with metrics.time_operation("sync", project=project, mode="safe"):
                # Prune stale worktree refs first - prevents "refusing to fetch into
                # branch checked out" errors when worktree dirs were deleted externally
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=mirror_path,
                    check=True,
                    capture_output=True,
                )

                # Ensure 'local' remote exists pointing to local repo
                # This allows fetching unpushed commits from local working copy
                self._ensure_local_remote(mirror_path, local_path)

                # Fetch from origin (may fail if offline - that's OK)
                origin_result = subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=mirror_path,
                    capture_output=True,
                )
                if origin_result.returncode != 0:
                    print("  ⚠ Origin fetch failed (offline?) - continuing with local")

                # Fetch from local repo (should always succeed)
                subprocess.run(
                    ["git", "fetch", "local"],
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

    def _ensure_local_remote(self, mirror_path: Path, local_path: Path) -> None:
        """Ensure mirror has a 'local' remote pointing to local repo.

        This allows the mirror to fetch unpushed commits from the local working copy,
        ensuring worktrees are created from the latest local state.

        Args:
            mirror_path: Path to bare mirror repo
            local_path: Path to local repo
        """
        # Check if 'local' remote already exists
        result = subprocess.run(
            ["git", "remote", "get-url", "local"],
            cwd=mirror_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Remote exists - check if URL matches
            current_url = result.stdout.strip()
            if current_url != str(local_path):
                # URL changed - update it
                subprocess.run(
                    ["git", "remote", "set-url", "local", str(local_path)],
                    cwd=mirror_path,
                    check=True,
                    capture_output=True,
                )
        else:
            # Remote doesn't exist - add it
            subprocess.run(
                ["git", "remote", "add", "local", str(local_path)],
                cwd=mirror_path,
                check=True,
                capture_output=True,
            )
            # Configure fetch refspec to get all branches from local
            subprocess.run(
                [
                    "git",
                    "config",
                    "remote.local.fetch",
                    "+refs/heads/*:refs/remotes/local/*",
                ],
                cwd=mirror_path,
                check=True,
                capture_output=True,
            )

    def check_mirror_freshness(self, project: str) -> tuple[bool, str]:
        """Checks if mirror is up-to-date with local repo, attempting fast-forward if stale.

        Compares the mirror's main branch HEAD to the local repo's main branch.
        If stale, attempts to fast-forward the mirror before returning.

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
        default_branch = config["default_branch"]  # Set at load time, always exists

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
                return (
                    True,
                    f"Mirror is up-to-date ({default_branch}: {mirror_head[:8]})",
                )

            # Mirror is stale - attempt fast-forward before warning
            ff_success, ff_msg = self._try_fast_forward_mirror(
                mirror_path, local_path, default_branch, mirror_head, local_head
            )
            if ff_success:
                return True, ff_msg

            # Fast-forward failed - return staleness warning
            count_result = subprocess.run(
                ["git", "rev-list", "--count", f"{mirror_head}..{local_head}"],
                cwd=local_path,
                capture_output=True,
                text=True,
            )
            if count_result.returncode == 0:
                commits_behind = count_result.stdout.strip()
                return (
                    False,
                    f"Mirror is {commits_behind} commits behind {default_branch} (fast-forward failed: {ff_msg})",
                )
            else:
                return (
                    False,
                    f"Mirror HEAD ({mirror_head[:8]}) differs from local ({local_head[:8]})",
                )

        except Exception as e:
            return False, f"Freshness check failed: {e}"

    def _try_fast_forward_mirror(
        self,
        mirror_path: Path,
        local_path: Path,
        branch: str,
        mirror_head: str,
        local_head: str,
    ) -> tuple[bool, str]:
        """Update mirror's branch to match local repo.

        Prefers fast-forward when possible, but force-updates if histories have
        diverged. Local repo is always treated as source of truth - polecat workers
        should work on the same code the user has locally.

        Args:
            mirror_path: Path to bare mirror repo
            local_path: Path to local repo
            branch: Branch name to update
            mirror_head: Current mirror HEAD SHA
            local_head: Target local HEAD SHA

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if fast-forward is possible (mirror_head is ancestor of local_head)
            merge_base_result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", mirror_head, local_head],
                cwd=local_path,
                capture_output=True,
            )

            is_fast_forward = merge_base_result.returncode == 0

            if is_fast_forward:
                print(f"  Fast-forwarding mirror {branch} to {local_head[:8]}...")
            else:
                # Histories diverged - force update to match local
                # This is safe: local is source of truth, mirror is just a cache
                print(
                    f"  Force-updating mirror {branch} to {local_head[:8]} (diverged from {mirror_head[:8]})..."
                )

            # Update mirror's branch ref to match local
            subprocess.run(
                ["git", "update-ref", f"refs/heads/{branch}", local_head],
                cwd=mirror_path,
                check=True,
                capture_output=True,
            )

            if is_fast_forward:
                return True, f"Mirror fast-forwarded to {local_head[:8]}"
            else:
                return True, f"Mirror force-updated to {local_head[:8]} (was diverged)"

        except subprocess.CalledProcessError as e:
            return False, f"git error: {e}"
        except Exception as e:
            return False, str(e)

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
                with metrics.time_operation("sync", project=project, mode="full"):
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

    def claim_next_task(self, caller: str, project: str | None = None):
        """Finds and claims the highest priority ready task."""
        tasks = self.storage.get_ready_tasks(project=project)

        # Record queue depth of ready tasks
        metrics.record_queue_depth("ready", count=len(tasks), project=project)

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
                        # Lock contention - another worker has this task
                        metrics.record_lock_wait(
                            "task_claim",
                            wait_time_ms=0,  # Non-blocking, so no wait
                            acquired=False,
                            caller=caller,
                        )
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

            except OSError as e:
                print(f"Warning: Failed to claim {task.id}: {e}", file=sys.stderr)
                continue
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    # Lock file cleanup is best-effort; may fail if already removed
                    pass

        return None

    def setup_worktree(self, task, lock_timeout: float = 30.0):
        """Creates a git worktree in ~/.aops/polecat linked to the project repo.

        Before creating the worktree, performs a safe sync of the mirror (if used)
        to ensure we have the latest commits from origin. Sync failures are non-fatal
        to support offline operation.

        Uses fcntl locking to prevent TOCTOU race conditions when multiple polecats
        try to create worktrees simultaneously.

        Args:
            task: Task object with id and project attributes
            lock_timeout: Seconds to wait for lock acquisition (default: 30)

        Raises:
            TaskIDValidationError: If task.id contains invalid characters
            TimeoutError: If lock cannot be acquired within timeout
        """
        # Validate task ID before using in filesystem path and git branch name
        validate_task_id_or_raise(task.id)

        return self._setup_worktree_locked(task, lock_timeout)

    def _setup_worktree_locked(self, task, lock_timeout: float):
        """Internal worktree setup with lock protection."""
        import time

        lock_path = self.polecats_dir / ".worktree_creation.lock"
        start_time = time.monotonic()

        # Ensure lock file exists
        lock_path.touch(exist_ok=True)

        with open(lock_path, "w") as lock_file:
            # Try to acquire lock with timeout
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break  # Lock acquired
                except BlockingIOError:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= lock_timeout:
                        # Record lock timeout metric
                        metrics.record_lock_timeout(
                            "worktree_creation",
                            timeout_seconds=lock_timeout,
                            caller=task.id,
                        )
                        raise TimeoutError(
                            f"Could not acquire worktree creation lock within {lock_timeout}s. "
                            f"Another polecat may be creating a worktree."
                        ) from None
                    time.sleep(0.1)  # Brief sleep before retry

            # Record lock wait time (time from start to acquisition)
            wait_time_ms = (time.monotonic() - start_time) * 1000
            if wait_time_ms > 10:  # Only record if there was meaningful contention
                metrics.record_lock_wait(
                    "worktree_creation",
                    wait_time_ms=wait_time_ms,
                    acquired=True,
                    caller=task.id,
                )

            try:
                return self._do_setup_worktree(task)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _do_setup_worktree(self, task):
        """Actual worktree creation logic (called under lock).

        Containerization-aware: Assumes fresh clone/worktree each time.
        Always syncs before work to handle stateless environments.
        """

        project = task.project if task.project else "aops"

        # --- SYNC BEFORE WORK ---
        # Critical for containerized/stateless environments where workers start fresh.
        # Even for persistent environments, ensures we have latest code.
        mirror_path = self.repos_dir / f"{project}.git"
        if mirror_path.exists():
            print(f"🔄 Syncing {project} mirror before worktree setup...")
            self.safe_sync_mirror(project)

            # Check freshness and warn if stale
            is_fresh, message = self.check_mirror_freshness(project)
            if not is_fresh:
                print(f"⚠ {message}", file=sys.stderr)
            else:
                print("  ✅ Mirror is fresh")

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
                print(
                    f"Worktree at {worktree_path} is corrupted, recreating...",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Directory {worktree_path} exists but is not a git worktree, recreating...",
                    file=sys.stderr,
                )
            # Remove the broken/non-worktree directory
            shutil.rmtree(worktree_path)
            # Prune stale worktree references from git
            subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False)

        print(f"Creating worktree at {worktree_path} from repo {repo_path}...")

        cmd = [
            "git",
            "worktree",
            "add",
            "-b",
            branch_name,
            str(worktree_path),
            default_branch,
        ]

        try:
            subprocess.run(cmd, cwd=repo_path, check=True)
        except subprocess.CalledProcessError as e:
            print(
                f"Worktree creation failed: {e}. Attempting recovery...",
                file=sys.stderr,
            )
            if self._branch_exists(repo_path, branch_name):
                # Branch exists from a previous run - delete and recreate fresh from main.
                # Polecat branches are disposable work branches; reusing stale branches
                # leads to worktrees that are many commits behind main.
                print(
                    f"Branch {branch_name} exists from previous run, deleting and recreating fresh...",
                    file=sys.stderr,
                )
                subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
                subprocess.run(cmd, cwd=repo_path, check=True)
            else:
                raise e

        # Configure git credentials for HTTPS push
        configure_git_credentials(worktree_path)

        # Set upstream tracking to the feature branch (not main).
        # This allows 'git push' to work without requiring manual 'git push -u',
        # while preventing accidental push to main.
        print(f"🔗 Setting upstream tracking for {branch_name}...")
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", f"{branch_name}:{branch_name}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if push_result.returncode == 0:
            print(f"  ✅ Upstream set: origin/{branch_name}")
        else:
            print(
                f"  ⚠ Could not set upstream (offline?): {push_result.stderr.strip()}",
                file=sys.stderr,
            )

        # Post-creation validation: ensure worktree has valid history
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
        )
        if result.returncode != 0:
            # Worktree was created but is orphan - this should not happen
            print(
                f"ERROR: Worktree created with orphan branch at {worktree_path}",
                file=sys.stderr,
            )
            print(f"Branch: {branch_name}, Default: {default_branch}", file=sys.stderr)
            # Clean up and fail
            shutil.rmtree(worktree_path)
            subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False)
            subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
            raise RuntimeError("Failed to create valid worktree - orphan branch detected")

        # Configure git identity if specified in config
        identity = self.config.get("git_identity", {})
        if identity:
            user_name = identity.get("name")
            user_email = identity.get("email")

            if user_name:
                subprocess.run(
                    ["git", "config", "user.name", user_name],
                    cwd=worktree_path,
                    check=True,
                )
            if user_email:
                subprocess.run(
                    ["git", "config", "user.email", user_email],
                    cwd=worktree_path,
                    check=True,
                )


        # Configure HTTPS credential helper for AOPS_BOT_GH_TOKEN if available
        # Override the bash-style credential helper from mirror with POSIX-compatible version
        if os.environ.get("AOPS_BOT_GH_TOKEN"):
            # Git credential helpers communicate via stdin/stdout, not positional args
            # Use sh -c to read stdin and emit credentials when protocol=https is seen
            # This overrides any broken credential.helper from the mirror repo config
            credential_cmd = (
                "sh -c '"
                "while read line; do "
                "case \"$line\" in "
                "protocol=https*) "
                "printf \"username=x-access-token\\n\"; "
                "printf \"password=%s\\n\" \"$AOPS_BOT_GH_TOKEN\"; "
                "break;; "
                "esac; "
                "done'"
            )
            subprocess.run(
                ["git", "config", "credential.helper", f"!{credential_cmd}"],
                cwd=worktree_path,
                check=True,
            )

        # --- SANDBOX SETTINGS ---
        # Write .claude/settings.json to restrict file writes to this worktree only.
        # Loaded via --setting-sources=user,project when spawning the worker.
        self.create_sandbox_settings(worktree_path)

        # --- WORKTREE VERIFICATION ---
        # Verify the worktree is correctly set up for PR workflow
        self._verify_worktree_setup(worktree_path, branch_name, default_branch)

        return worktree_path

    def create_sandbox_settings(self, worktree_path: Path) -> Path:
        """Write .claude/settings.json to a worktree to sandbox file access.

        The settings restrict Write and Edit operations to the worktree directory
        only. When Claude Code loads this file via --setting-sources=user,project,
        it will deny any attempt to write or edit files outside the worktree.

        The allow rules take precedence over deny rules in Claude Code's permission
        system, so worktree paths are explicitly allowed and everything else is
        blocked by the wildcard deny.

        Args:
            worktree_path: Absolute path to the worktree root directory

        Returns:
            Path to the created settings file
        """
        import json

        worktree_str = str(worktree_path.resolve())
        claude_dir = worktree_path / ".claude"
        claude_dir.mkdir(exist_ok=True)

        settings = {
            "permissions": {
                "allow": [
                    f"Write({worktree_str}/**)",
                    f"Edit({worktree_str}/**)",
                    f"Bash(cd {worktree_str}:*)",
                ],
                "deny": [
                    "Write(**)",
                    "Edit(**)",
                ],
            }
        }

        settings_path = claude_dir / "settings.json"
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        return settings_path

    def _verify_worktree_setup(self, worktree_path: Path, branch_name: str, default_branch: str):
        """Verify worktree is correctly set up for the PR workflow.

        Checks:
        1. Branch exists and has valid history
        2. Branch is based on current main (not stale)
        3. Remote tracking is configured correctly

        Args:
            worktree_path: Path to the worktree
            branch_name: Expected branch name (e.g., 'polecat/task-id')
            default_branch: The main branch name (e.g., 'main')
        """
        # 1. Verify branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or result.stdout.strip() != branch_name:
            print(
                f"⚠ Branch verification: expected {branch_name}, "
                f"got {result.stdout.strip() if result.returncode == 0 else 'error'}",
                file=sys.stderr,
            )

        # 2. Verify branch is based on recent main
        # Get the merge-base between our branch and origin/main (if available)
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", f"origin/{default_branch}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if merge_base_result.returncode == 0:
            # Check how many commits behind origin/main we are
            commits_behind = subprocess.run(
                [
                    "git",
                    "rev-list",
                    "--count",
                    f"{merge_base_result.stdout.strip()}..origin/{default_branch}",
                ],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )
            if commits_behind.returncode == 0 and int(commits_behind.stdout.strip()) > 10:
                print(
                    f"⚠ Worktree is {commits_behind.stdout.strip()} commits behind "
                    f"origin/{default_branch}. Consider rebasing.",
                    file=sys.stderr,
                )

        # Note: Worktrees inherit the mirror's remotes, which already have
        # the correct origin push URL (git@github.com:...). No need to
        # reconfigure here. (A previous attempt to set-url --push here
        # had a bug that corrupted the push URL to the literal string "origin".)

    def _branch_exists(self, repo_path, branch_name):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=repo_path,
            capture_output=True,
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
            text=True,
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
            TaskIDValidationError: If task_id contains invalid characters
        """
        # Validate task ID before using in filesystem path and git branch name
        validate_task_id_or_raise(task_id)

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

        # Safety check: verify worktree has no uncommitted changes
        # This prevents data loss when agent forgets to commit before marking task complete
        if not force and worktree_path.exists() and (worktree_path / ".git").exists():
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                raise RuntimeError(
                    f"Worktree {worktree_path} has uncommitted changes. "
                    f"Use --force to delete anyway."
                )

        if worktree_path.exists():
            print(f"Removing worktree {worktree_path}...")
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=repo_path,
                check=False,
            )
            if worktree_path.exists():
                shutil.rmtree(worktree_path)

        if self._branch_exists(repo_path, branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
