#!/usr/bin/env python3
import fcntl
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from observability import metrics
from validation import validate_task_id_or_raise

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# lib.task_storage and lib.task_model are deprecated and removed.
# Task management has migrated to the PKB MCP server (nicsuzor/mem).
_TaskStatus: Any = None
_TaskStorage: Any = None
try:
    from lib.task_model import TaskStatus as _TaskStatus  # pyright: ignore[reportMissingImports]
    from lib.task_storage import (  # pyright: ignore[reportMissingImports]
        TaskStorage as _TaskStorage,
    )
except ImportError:
    pass


def get_polecat_home() -> Path:
    """Get the polecat home directory.

    Checks in order:
    1. POLECAT_HOME environment variable
    2. Default: ~/.polecat

    Returns:
        Path to the polecat home directory
    """
    env_home = os.environ.get("POLECAT_HOME")
    if env_home:
        if env_home.startswith("~"):
            return Path(env_home).expanduser()
        return Path(env_home)
    return Path.home() / ".polecat"


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
        '!test "$1" = get && printf "username=x-access-token\\npassword=%s\\n" "$AOPS_BOT_GH_TOKEN"'
    )

    subprocess.run(
        ["git", "config", "--local", "credential.helper", helper_cmd],
        cwd=repo_path,
        check=True,
    )


def _to_https_url(url: str) -> str:
    """Converts a GitHub SSH URL to an HTTPS URL for bot compatibility.

    Example: git@github.com:owner/repo.git -> https://github.com/owner/repo.git
    """
    if url.startswith("git@github.com:"):
        return url.replace("git@github.com:", "https://github.com/")
    return url


class PolecatManager:
    def __init__(self, home_dir: Path | None = None):
        """Initialize the polecat manager.

        Args:
            home_dir: Optional home directory override. If not specified,
                      uses POLECAT_HOME env var or defaults to ~/.polecat
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

        # lib.task_storage is deprecated; None when running against PKB MCP server
        self.storage: Any = _TaskStorage() if _TaskStorage is not None else None
        self.task_status: Any = _TaskStatus

    def get_task(self, task_id: str) -> Any:
        """Retrieve a task by ID, routing to storage or PKB bridge."""
        if self.storage is not None:
            return self.storage.get_task(task_id)
        from polecat.pkb_bridge import get_task as pkb_get_task

        return pkb_get_task(task_id)

    def save_task(self, task: Any) -> None:
        """Save a task, routing to storage or PKB bridge."""
        if self.storage is not None:
            self.storage.save_task(task)
            return
        from polecat.pkb_bridge import save_task as pkb_save_task

        pkb_save_task(task)

    def update_task(self, task_id: str, **kwargs: Any) -> bool:
        """Update task fields, routing to storage or PKB bridge.

        When using legacy storage, mutates the task object and saves it.
        String status values are converted to TaskStatus enums automatically.
        When using PKB bridge, calls update_task directly.
        """
        if self.storage is not None:
            task = self.storage.get_task(task_id)
            if task is None:
                return False
            for key, value in kwargs.items():
                # Convert string status values to TaskStatus enums for legacy storage
                if key == "status" and isinstance(value, str) and _TaskStatus is not None:
                    value = _TaskStatus(value)
                setattr(task, key, value)
            self.storage.save_task(task)
            return True
        from polecat.pkb_bridge import update_task as pkb_update_task

        return pkb_update_task(task_id, **kwargs)

    def generate_crew_name(self) -> str:
        """Generate a unique crew name, avoiding names already in use.

        Picks from the configured name pool when possible.  If the pool is
        exhausted (all base names have an existing crew directory), falls back
        to appending a short random hex suffix (e.g. ``weasel_3f7a``) so that
        stale directories never block new crew creation.
        """
        import random
        import secrets

        active_crew = set(self.list_crew())
        available = [n for n in self.crew_names if n not in active_crew]

        if available:
            return random.choice(available)

        # Pool exhausted: generate name_XXXX until we find a free slot.
        # With 4 hex chars (65 536 combinations per base name) collisions are
        # extremely unlikely, but we retry up to 200 times to be safe.
        for _ in range(200):
            base = random.choice(self.crew_names)
            suffix = secrets.token_hex(2)  # 4 hex chars
            name = f"{base}_{suffix}"
            if name not in active_crew:
                return name

        # Should never happen in practice — only if 200 random draws all
        # collide with existing names.
        raise RuntimeError(
            "Unable to generate a unique crew name after 200 attempts. "
            "Run 'polecat nuke <name>' to clean up stale crew directories."
        )

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
        """List crew worker directories.

        Returns all crew directories, including ones whose sessions have ended
        but were preserved (e.g. via --keep or because they had unmerged work).
        Skips empty directories that are clearly the result of a failed cleanup.
        """
        if not self.crew_dir.exists():
            return []
        result = []
        for d in self.crew_dir.iterdir():
            if not d.is_dir():
                continue
            # Skip empty dirs — these are partially-cleaned remnants, not real crews.
            # Guard against the setup window: setup_crew_worktree() creates the dir
            # before populating it; a lock file signals that work is in progress.
            if self._crew_lock_path(d.name).exists() or any(d.iterdir()):
                result.append(d.name)
            else:
                # Best-effort removal of the empty husk so it doesn't pile up.
                try:
                    d.rmdir()
                except OSError:
                    pass
        return result

    def _crew_branch_open_pr(self, repo_path: Path, branch_name: str) -> str | None:
        """Return PR URL if branch has an open PR on GitHub, else None."""
        import json as _json

        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch_name,
                    "--state",
                    "open",
                    "--json",
                    "number,url",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                prs = _json.loads(result.stdout)
                if prs:
                    return prs[0].get("url") or f"#{prs[0].get('number')}"
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        return None

    def _classify_crew_branch(
        self, repo_path: Path, branch_name: str, default_branch: str = "main"
    ) -> tuple[str, dict]:
        """Classify a crew branch as merged/open_pr/unmerged_wip/gone.

        Fetches origin/<branch_name> and origin/<default_branch> best-effort
        so the classification reflects remote state, not stale local refs.

        Returns:
            (state, info) where state is one of 'merged', 'open_pr',
            'unmerged_wip', 'gone'. info may include 'pr_url',
            'unmerged_log'.
        """
        info: dict = {}

        subprocess.run(
            ["git", "fetch", "origin", branch_name],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "fetch", "origin", default_branch],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )

        def _ref_exists(ref: str) -> bool:
            return (
                subprocess.run(
                    ["git", "rev-parse", "--verify", "--quiet", ref],
                    cwd=repo_path,
                    capture_output=True,
                ).returncode
                == 0
            )

        remote_ref = f"refs/remotes/origin/{branch_name}"
        local_ref = f"refs/heads/{branch_name}"
        tip = None
        if _ref_exists(remote_ref):
            tip = remote_ref
        elif _ref_exists(local_ref):
            tip = local_ref

        if tip is None:
            return "gone", info

        pr_url = self._crew_branch_open_pr(repo_path, branch_name)
        if pr_url:
            info["pr_url"] = pr_url
            return "open_pr", info

        default_ref = (
            f"refs/remotes/origin/{default_branch}"
            if _ref_exists(f"refs/remotes/origin/{default_branch}")
            else default_branch
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", tip, default_ref],
            cwd=repo_path,
            capture_output=True,
        )
        if ancestor.returncode == 0:
            return "merged", info

        log = subprocess.run(
            ["git", "log", "--oneline", f"{default_ref}..{tip}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        info["unmerged_log"] = log.stdout.strip() if log.returncode == 0 else ""
        return "unmerged_wip", info

    def _crew_lock_path(self, name: str) -> Path:
        self.crew_dir.mkdir(parents=True, exist_ok=True)
        return self.crew_dir / f".{name}.lock"

    def _delete_crew_branch_remote(self, repo_path: Path, branch_name: str) -> None:
        """Best-effort delete of remote crew branch."""
        subprocess.run(
            ["git", "push", "origin", "--delete", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

    def _delete_crew_branch_mirror(self, project: str, branch_name: str) -> None:
        """Best-effort delete of branch ref from bare mirror."""
        mirror_path = self.repos_dir / f"{project}.git"
        if not mirror_path.exists():
            return
        subprocess.run(
            ["git", "update-ref", "-d", f"refs/heads/{branch_name}"],
            cwd=mirror_path,
            capture_output=True,
            check=False,
        )

    def setup_crew_worktree(self, name: str, project: str) -> Path:
        """Creates a persistent crew worktree for interactive work.

        Unlike polecat worktrees (task-scoped, ephemeral), crew worktrees
        are named and persist across sessions.

        Uses the same bare mirror as polecat task worktrees — synced before
        clone, fast (local hardlinks), and no stale local branch state.
        After clone, forcibly refreshes the default branch from origin so
        new crew branches never start from stale mirror state.

        Args:
            name: Crew worker name (e.g., "audre", "marsha")
            project: Project slug to work on

        Returns:
            Path to the crew worktree
        """
        if project not in self.projects:
            raise ValueError(f"Unknown project: {project}. Known: {list(self.projects.keys())}")

        project_config = self.projects[project]
        local_repo_path = project_config["path"]
        default_branch = project_config.get("default_branch", "main")

        crew_path = self.crew_dir / name
        worktree_path = crew_path / project
        branch_name = f"crew/{name}"

        if worktree_path.exists():
            raise FileExistsError(
                f"Crew worktree already exists at {worktree_path}. "
                f"Use 'polecat crew -r {name}' to resume, or 'polecat nuke {name}' to start fresh."
            )

        # Acquire the lock BEFORE creating crew_path so that list_crew()'s
        # lock-file guard closes the race window completely: without this
        # ordering, list_crew() could see an empty, lock-free dir and delete it
        # before the lock file is created.
        lock_path = self._crew_lock_path(name)
        with open(lock_path, "w") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    f"Another crew operation is in progress for '{name}'. "
                    f"Wait for it to finish, or remove {lock_path} if stale."
                ) from exc

            crew_path.mkdir(exist_ok=True)

            # Check residual remote crew branch before we clone anything.
            # Classify against the local source repo (has github auth + gh CLI).
            if local_repo_path.exists():
                state, info = self._classify_crew_branch(
                    local_repo_path, branch_name, default_branch
                )
                if state == "open_pr":
                    raise FileExistsError(
                        f"Open PR exists for {branch_name} ({info.get('pr_url')}). "
                        f"Use 'polecat crew -r {name}' to resume, or close the PR first."
                    )
                if state == "unmerged_wip":
                    log = info.get("unmerged_log") or "(log unavailable)"
                    raise FileExistsError(
                        f"origin/{branch_name} has unmerged commits:\n{log}\n"
                        f"Use 'polecat crew -r {name}' to resume, "
                        f"or 'polecat nuke -f {name}' to discard."
                    )
                if state == "merged":
                    print(f"🧹 Flushing merged residue of {branch_name}...")
                    self._delete_crew_branch_remote(local_repo_path, branch_name)
                    subprocess.run(
                        ["git", "branch", "-D", branch_name],
                        cwd=local_repo_path,
                        capture_output=True,
                        check=False,
                    )
                    self._delete_crew_branch_mirror(project, branch_name)

            # Sync bare mirror before cloning (same as polecat task worktrees)
            mirror_path = self.repos_dir / f"{project}.git"
            if mirror_path.exists():
                print(f"🔄 Syncing {project} mirror...")
                self.safe_sync_mirror(project)
            else:
                print(f"📦 Creating mirror for {project}...")
                self.ensure_repo_mirror(project)

            # Clone from bare mirror (fast hardlinks, no stale local branches).
            # Fall back to local repo if mirror somehow doesn't exist.
            repo_path = mirror_path if mirror_path.exists() else local_repo_path
            if not repo_path.exists():
                raise FileNotFoundError(f"No repo source found for {project}")

            print(f"Creating crew clone at {worktree_path} from {repo_path}...")
            subprocess.run(
                ["git", "clone", str(repo_path), str(worktree_path)],
                check=True,
            )

            # Propagate git identity from source repo (clone doesn't copy local config)
            if local_repo_path.exists():
                self._propagate_git_identity(local_repo_path, worktree_path)

            # Re-point origin to the actual remote (bare mirror sets origin to itself)
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=local_repo_path,
                capture_output=True,
                text=True,
            )
            origin_url = _to_https_url(result.stdout.strip())
            if origin_url:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", origin_url],
                    cwd=worktree_path,
                    check=True,
                )

            # Refresh default branch from origin. The bare mirror is synced
            # from the local working repo (which may be behind origin), so we
            # cannot trust its default_branch tip. Offline-tolerant.
            fetch_default = subprocess.run(
                ["git", "fetch", "origin", default_branch],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if fetch_default.returncode == 0:
                subprocess.run(
                    ["git", "checkout", "-B", default_branch, f"origin/{default_branch}"],
                    cwd=worktree_path,
                    check=True,
                )
            else:
                print(
                    f"  ⚠ Offline fetch failed for origin/{default_branch}; "
                    f"using mirror state. {fetch_default.stderr.strip()}",
                    file=sys.stderr,
                )

            # Check if crew branch exists remotely (we already classified
            # it above as gone/merged, so this should normally be empty,
            # but re-check defensively in case of races).
            branch_exists_result = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", branch_name],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )

            if branch_exists_result.stdout.strip():
                # Residual after our flush (race or offline classification).
                # Adopt it — the classifier already ruled out open PR / WIP.
                subprocess.run(
                    ["git", "fetch", "origin", branch_name],
                    cwd=worktree_path,
                    capture_output=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                    cwd=worktree_path,
                    check=True,
                )
            else:
                # Create new branch from the fresh default branch
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=worktree_path,
                    check=True,
                )

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

            # Install pre-commit hooks
            self._install_precommit_hooks(worktree_path)

            # Apply sandbox settings to isolate the worker to this worktree
            self.create_sandbox_settings(worktree_path)

            return worktree_path

    def nuke_crew(self, name: str, force: bool = False):
        """Remove a crew worker and flush all associated branch state.

        Aggressive cleanup: local clone, local branch in source repo,
        remote crew branch on origin, and the ref in the bare mirror.
        Refuses to delete a branch with an open PR or unmerged commits
        unless force=True.

        Args:
            name: Crew worker name
            force: Skip safety checks (open PR, unmerged commits)
        """
        crew_path = self.crew_dir / name
        if not crew_path.exists():
            raise ValueError(f"Crew worker not found: {name}")

        lock_path = self._crew_lock_path(name)
        with open(lock_path, "w") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    f"Another crew operation is in progress for '{name}'. "
                    f"Wait for it to finish, or remove {lock_path} if stale."
                ) from exc

            for project_dir in list(crew_path.iterdir()):
                if not project_dir.is_dir():
                    continue
                project = project_dir.name
                branch_name = f"crew/{name}"

                if project in self.projects:
                    repo_path = self.projects[project]["path"]
                    default_branch = self.projects[project].get("default_branch", "main")
                else:
                    repo_path = self.repos_dir / f"{project}.git"
                    default_branch = "main"

                if repo_path.exists():
                    state, info = self._classify_crew_branch(repo_path, branch_name, default_branch)
                    if not force and state == "open_pr":
                        raise RuntimeError(
                            f"Branch {branch_name} has an open PR "
                            f"({info.get('pr_url')}). Close/merge the PR, "
                            f"or use --force to delete anyway."
                        )
                    if not force and state == "unmerged_wip":
                        log = info.get("unmerged_log") or "(log unavailable)"
                        raise RuntimeError(
                            f"Branch {branch_name} has unmerged commits:\n{log}\n"
                            f"Use --force to delete anyway."
                        )

                    if project_dir.exists():
                        shutil.rmtree(project_dir, ignore_errors=True)

                    if self._branch_exists(repo_path, branch_name):
                        subprocess.run(
                            ["git", "branch", "-D", branch_name],
                            cwd=repo_path,
                            capture_output=True,
                            check=False,
                        )
                    if state == "open_pr":
                        print(
                            f"Preserving remote branch {branch_name} — open PR: "
                            f"{info.get('pr_url')}"
                        )
                    else:
                        self._delete_crew_branch_remote(repo_path, branch_name)
                        self._delete_crew_branch_mirror(project, branch_name)

            if crew_path.exists():
                shutil.rmtree(crew_path)

        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass

        print(f"Nuked crew worker: {name}")

    def get_repo_path(self, task) -> Path:
        """Returns the repository path to use as source for the worktree.

        Prefers bare mirror in $POLECAT_HOME/polecat/.repos/ if it exists (for isolation).
        Falls back to local project path from config.

        Fails fast if ``task.project`` is missing or unknown — silent defaults
        to the academicOps repo were causing tasks to operate against the wrong
        repository.
        """
        if not task.project:
            raise ValueError(
                f"Task {task.id} has no project set — cannot resolve repo path. "
                f"Set task.project explicitly; silent fallbacks are disabled."
            )

        project = task.project

        # Check for bare mirror first
        mirror_path = self.repos_dir / f"{project}.git"
        if mirror_path.exists():
            return mirror_path

        if project in self.projects:
            return self.projects[project]["path"]

        raise ValueError(
            f"Task {task.id} references unknown project {project!r} — "
            f"not in polecat.yaml and no bare mirror at {mirror_path}. "
            f"Known projects: {sorted(self.projects.keys())}"
        )

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
            # Ensure the origin URL is HTTPS for bot compatibility
            remote_url = self._get_remote_url(source_path)
            remote_url = _to_https_url(remote_url)
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=mirror_path,
                check=True,
            )
            subprocess.run(
                ["git", "fetch", "--all", "--prune"],
                cwd=mirror_path,
                check=True,
            )
        else:
            # Derive remote URL from source repo and force HTTPS
            remote_url = self._get_remote_url(source_path)
            remote_url = _to_https_url(remote_url)
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
        """Safely syncs a mirror from origin without pruning refs.

        Origin is the source of truth. The mirror is a local cache of origin;
        we never pull from the local working repo, because a local checkout
        can easily lag behind origin (e.g. user hasn't pulled today) and
        contaminating the mirror with stale local state was the root cause of
        the crew stale-repo bug. If a user needs unpushed local commits in a
        worktree, they should push them first.

        Safe to run while worktrees are active (no --prune).

        Args:
            project: Project slug

        Returns:
            True if origin fetch succeeded, False if offline or failed.
        """
        mirror_path = self.repos_dir / f"{project}.git"

        if not mirror_path.exists():
            print(f"⚠ No mirror for {project} - skipping sync", file=sys.stderr)
            return False

        if project not in self.projects:
            print(f"⚠ Unknown project {project} - skipping sync", file=sys.stderr)
            return False

        try:
            print(f"Syncing {project} mirror from origin...")
            with metrics.time_operation("sync", project=project, mode="safe"):
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=mirror_path,
                    check=True,
                    capture_output=True,
                )

                exclude_refspecs = self._worktree_exclude_refspecs(mirror_path)
                if exclude_refspecs:
                    branches = [r.removeprefix("^refs/heads/") for r in exclude_refspecs]
                    print(f"  Skipping worktree branches during fetch: {', '.join(branches)}")

                origin_result = subprocess.run(
                    ["git", "fetch", "origin", *exclude_refspecs],
                    cwd=mirror_path,
                    capture_output=True,
                    text=True,
                )
                if origin_result.returncode != 0:
                    print(
                        f"  ⚠ Origin fetch failed for {project} (offline?): "
                        f"{origin_result.stderr.strip()}",
                        file=sys.stderr,
                    )
                    return False
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠ Mirror sync failed for {project}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠ Mirror sync failed for {project}: {e}", file=sys.stderr)
            return False

    def _worktree_exclude_refspecs(self, mirror_path: Path) -> list[str]:
        """Return negative refspecs to exclude branches checked out in worktrees.

        Git refuses to fetch into a branch that is checked out in any worktree.
        This method returns refspecs like '^refs/heads/branch' so that fetch
        silently skips those branches instead of failing.
        """
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=mirror_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        branches: set[str] = set()
        for line in result.stdout.splitlines():
            if line.startswith("branch refs/heads/"):
                raw_branch = line[len("branch refs/heads/") :]
                branch = raw_branch.strip()
                if branch:
                    branches.add(branch)

        return [f"^refs/heads/{branch}" for branch in sorted(branches)]

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
        default_branch = config["default_branch"]

        try:
            # Origin is source of truth. Compare the mirror's local ref to
            # what origin reports via ls-remote. No mutation — mutation is
            # the job of safe_sync_mirror, which fetches from origin only.
            mirror_result = subprocess.run(
                ["git", "rev-parse", f"refs/heads/{default_branch}"],
                cwd=mirror_path,
                capture_output=True,
                text=True,
            )
            if mirror_result.returncode != 0:
                return False, f"Mirror missing branch {default_branch}"
            mirror_head = mirror_result.stdout.strip()

            remote_result = subprocess.run(
                ["git", "ls-remote", "origin", f"refs/heads/{default_branch}"],
                cwd=mirror_path,
                capture_output=True,
                text=True,
            )
            if remote_result.returncode != 0 or not remote_result.stdout.strip():
                # Offline or origin unreachable — can't prove stale; assume OK.
                return True, f"Mirror {default_branch} at {mirror_head[:8]} (origin unreachable)"
            origin_head = remote_result.stdout.split()[0]

            if mirror_head == origin_head:
                return True, f"Mirror is up-to-date ({default_branch}: {mirror_head[:8]})"
            return (
                False,
                f"Mirror {default_branch} at {mirror_head[:8]} is stale vs "
                f"origin {origin_head[:8]} — run 'pc sync' to refresh",
            )
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

            success = self.safe_sync_mirror(project)
            if success:
                print(f"✓ {project}")
            else:
                print(f"✗ {project}")
            results[project] = success
        return results

    def claim_next_task(self, caller: str, project: str | None = None):
        """Finds and claims the highest priority ready task."""
        if self.storage is not None:
            return self._claim_next_task_legacy(caller, project)
        return self._claim_next_task_pkb(caller, project)

    def _claim_next_task_legacy(self, caller: str, project: str | None = None):
        """Claim via legacy TaskStorage with file locking."""
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
                        if fresh_task is None or fresh_task.status != self.task_status.ACTIVE:
                            continue
                        if fresh_task.assignee and fresh_task.assignee != caller:
                            continue
                        # Defense in depth: skip tasks that already have an open PR,
                        # even if their status somehow reverted to ACTIVE.
                        if fresh_task.pr_url or fresh_task.pr:
                            print(
                                f"[claim] Skipping {fresh_task.id}: locked by existing PR "
                                f"({fresh_task.pr_url or f'#{fresh_task.pr}'})",
                                file=sys.stderr,
                            )
                            continue

                        fresh_task.status = self.task_status.IN_PROGRESS
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

    def _claim_next_task_pkb(self, caller: str, project: str | None = None):
        """Claim via PKB MCP server."""
        from polecat.pkb_bridge import get_ready_tasks, get_task, update_task

        tasks = get_ready_tasks(project=project)
        metrics.record_queue_depth("ready", count=len(tasks), project=project)

        if not tasks:
            return None

        for task in tasks:
            # Re-fetch to get fresh status (avoid race)
            fresh = get_task(task.id)
            if fresh is None or fresh.status != "active":
                continue
            if fresh.assignee and fresh.assignee != caller:
                continue
            if fresh.pr_url or fresh.pr:
                print(
                    f"[claim] Skipping {fresh.id}: locked by existing PR "
                    f"({fresh.pr_url or f'#{fresh.pr}'})",
                    file=sys.stderr,
                )
                continue

            # Claim via MCP update_task (atomic at server level)
            update_task(fresh.id, status="in_progress", assignee=caller)
            fresh.status = "in_progress"
            fresh.assignee = caller
            return fresh

        return None

        return None

    def setup_worktree(self, task, lock_timeout: float = 30.0):
        """Creates a local git clone in $POLECAT_HOME/polecat linked to the project repo.

        Before creating the clone, performs a safe sync of the mirror (if used)
        to ensure we have the latest commits from origin. Sync failures are non-fatal
        to support offline operation.

        Uses fcntl locking to prevent TOCTOU race conditions when multiple polecats
        try to create clones simultaneously.

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

        # Fail fast on missing project — no silent fallback. get_repo_path()
        # below will raise with a clearer message if project is invalid, but
        # we also need ``project`` here for mirror/sync lookups.
        if not task.project:
            raise ValueError(
                f"Task {task.id} has no project set — cannot set up worktree. "
                f"Set task.project explicitly; silent fallbacks are disabled."
            )
        project = task.project

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
        default_branch = self.projects.get(project, {}).get("default_branch", "main")

        if worktree_path.exists():
            # Validate it's actually a git repo
            git_dir = worktree_path / ".git"
            if git_dir.exists():
                # Verify the repo has valid git state (not orphan/corrupted)
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                )
                if result.returncode == 0:
                    return worktree_path
                # Worktree exists but is broken (orphan branch or corrupted)
                print(
                    f"Clone at {worktree_path} is corrupted, recreating...",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Directory {worktree_path} exists but is not a git repo, recreating...",
                    file=sys.stderr,
                )
            # Remove the broken/non-repo directory
            shutil.rmtree(worktree_path)

        print(f"Creating local clone at {worktree_path} from repo {repo_path}...")

        cmd = [
            "git",
            "clone",
            str(repo_path),
            str(worktree_path),
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(
                f"Clone creation failed: {e}",
                file=sys.stderr,
            )
            raise e

        # Propagate git identity from source repo (clone doesn't copy local config)
        self._propagate_git_identity(repo_path, worktree_path)

        # Re-point origin to the actual remote instead of the local repo
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        origin_url = _to_https_url(result.stdout.strip())
        if origin_url:
            subprocess.run(
                ["git", "remote", "set-url", "origin", origin_url], cwd=worktree_path, check=True
            )

        # Check if the branch exists on remote, if so check it out, else create fresh from default
        branch_exists_result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        branch_exists = False
        if branch_exists_result.stdout.strip():
            # Exists remotely — check if it is already merged into the default branch.
            # If so, we want to start fresh from the current tip of the default branch.
            remote_sha = branch_exists_result.stdout.split()[0]
            is_merged_result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", remote_sha, f"origin/{default_branch}"],
                cwd=worktree_path,
                capture_output=True,
            )
            if is_merged_result.returncode == 0:
                print(
                    f"  Branch {branch_name} (at {remote_sha[:8]}) is already merged into {default_branch}."
                )
                print(f"  Deleting stale remote branch and starting fresh from {default_branch}...")
                subprocess.run(
                    ["git", "push", "origin", "--delete", branch_name],
                    cwd=worktree_path,
                    capture_output=True,
                    check=True,
                )
                branch_exists = False
            else:
                branch_exists = True

        if branch_exists:
            # Exists remotely and not merged — fetch then checkout and track
            subprocess.run(
                ["git", "fetch", "origin", branch_name],
                cwd=worktree_path,
                capture_output=True,
                check=True,
            )

            # --- FIX: Avoid reusing stale merged branches ---
            # If the branch is already merged into origin/{default_branch}, it's stale.
            # Start fresh from the default branch instead.

            # Fetch default branch to ensure origin/{default_branch} is up to date
            subprocess.run(
                ["git", "fetch", "origin", default_branch],
                cwd=worktree_path,
                capture_output=True,
                check=True,
            )

            # Check if origin/{branch_name} is merged into origin/{default_branch}
            is_merged = (
                subprocess.run(
                    [
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        f"origin/{branch_name}",
                        f"origin/{default_branch}",
                    ],
                    cwd=worktree_path,
                ).returncode
                == 0
            )

            if is_merged:
                print(
                    f"  🗑 Branch {branch_name} is already merged into {default_branch}. "
                    f"Starting fresh from {default_branch}."
                )
                # Try to delete the remote branch to avoid later push collisions
                delete_result = subprocess.run(
                    ["git", "push", "origin", "--delete", branch_name],
                    cwd=worktree_path,
                    capture_output=True,
                )
                if delete_result.returncode == 0:
                    print(f"  ✅ Deleted stale remote branch {branch_name}")
                else:
                    stderr = delete_result.stderr.decode(errors="replace").strip()
                    print(f"  ⚠ Could not delete remote branch {branch_name}: {stderr}")

                # Create fresh from default branch
                subprocess.run(["git", "checkout", default_branch], cwd=worktree_path, check=True)
                subprocess.run(
                    ["git", "checkout", "-b", branch_name], cwd=worktree_path, check=True
                )
            else:
                # SAFEGUARD: Hard-fail if target branch is too far behind origin/main
                # and not merged. This prevents agents from burning turns on massive rebase/merge noise.
                _rev_list_result = subprocess.run(
                    [
                        "git",
                        "rev-list",
                        "--count",
                        f"origin/{branch_name}..origin/{default_branch}",
                    ],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commits_behind = int(_rev_list_result.stdout.strip())

                if commits_behind > 100:
                    raise RuntimeError(
                        f"Target branch {branch_name} is {commits_behind} commits behind {default_branch}. "
                        "This looks like a stale unmerged branch from a previous run. "
                        "Please delete the remote branch or merge manually before re-dispatching."
                    )

                subprocess.run(
                    ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                    cwd=worktree_path,
                    check=True,
                )
        else:
            # Create fresh from default branch. Note: clone usually checks out default branch.
            subprocess.run(["git", "checkout", default_branch], cwd=worktree_path, check=False)
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=worktree_path, check=True)

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
            # Clone was created but is orphan - this should not happen
            print(
                f"ERROR: Clone created with orphan branch at {worktree_path}",
                file=sys.stderr,
            )
            print(f"Branch: {branch_name}, Default: {default_branch}", file=sys.stderr)
            # Clean up and fail
            shutil.rmtree(worktree_path)
            raise RuntimeError("Failed to create valid clone - orphan branch detected")

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
                'case "$line" in '
                "protocol=https*) "
                'printf "username=x-access-token\\n"; '
                'printf "password=%s\\n" "$AOPS_BOT_GH_TOKEN"; '
                "break;; "
                "esac; "
                "done'"
            )
            subprocess.run(
                ["git", "config", "credential.helper", f"!{credential_cmd}"],
                cwd=worktree_path,
                check=True,
            )

        # Install pre-commit hooks
        self._install_precommit_hooks(worktree_path)

        # --- SANDBOX SETTINGS ---
        # Write .claude/settings.json to restrict file writes to this worktree only.
        # Loaded via --setting-sources=user,project when spawning the worker.
        self.create_sandbox_settings(worktree_path)

        # --- WORKTREE VERIFICATION ---
        # Verify the worktree is correctly set up for PR workflow
        self._verify_worktree_setup(worktree_path, branch_name, default_branch)

        return worktree_path

    def _install_precommit_hooks(self, worktree_path: Path):
        """Install pre-commit hooks in a worktree if .pre-commit-config.yaml exists.

        We deploy a stable hook template (scripts/hooks/pre-commit) that uses `uv run`
        at runtime, rather than running `pre-commit install` which hardcodes the current
        venv path. All polecat worktrees share the main repo's .git/hooks/ directory —
        hardcoding a worker's venv path would break all other worktrees when that venv
        is cleaned up.
        """
        config_file = worktree_path / ".pre-commit-config.yaml"
        if not config_file.exists():
            return

        hook_template = worktree_path / "scripts" / "hooks" / "pre-commit"
        if not hook_template.exists():
            print(
                "  ⚠ Hook template scripts/hooks/pre-commit not found; skipping hook install.",
                file=sys.stderr,
            )
            return

        print("🪝 Installing pre-commit hooks...")
        try:
            # Resolve the shared hooks directory (works from main repo and any worktree)
            result = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True,
            )
            git_common_dir = result.stdout.strip()
            if not Path(git_common_dir).is_absolute():
                git_common_dir = str((worktree_path / git_common_dir).resolve())
            hooks_dir = Path(git_common_dir) / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(hook_template, hooks_dir / "pre-commit")
            (hooks_dir / "pre-commit").chmod(0o755)
            print("  ✅ Pre-commit hooks installed")
        except subprocess.CalledProcessError as e:
            print(
                f"  ⚠ Could not install pre-commit hooks: {e.stderr.strip()}",
                file=sys.stderr,
            )
        except OSError as e:
            print(
                f"  ⚠ Could not install pre-commit hooks: {e}",
                file=sys.stderr,
            )

    def create_sandbox_settings(self, worktree_path: Path) -> None:
        """Write .claude/settings.json and .gemini/policies/sandbox.toml to sandbox access.

        The settings permit Write and Edit operations within the worktree directory.
        Claude Code's default sandbox already restricts file operations to the
        project directory, so we only need allow rules -- no blanket deny rules.

        For Gemini CLI, we use the Policy Engine to restrict file operations.
        Priority semantics: higher number wins. sandbox.toml uses allow=50 and
        deny=10 so that allow beats deny inside the worktree. deny-extension-writes
        uses deny=100 which beats sandbox allow=50, preserving extension protection.
        See: https://cloud.google.com/gemini/docs/codeassist/policy-engine

        Args:
            worktree_path: Absolute path to the worktree root directory
        """
        import json

        worktree_str = str(worktree_path.resolve())
        claude_dir = worktree_path / ".claude"
        claude_dir.mkdir(exist_ok=True)

        # 1. Claude Settings
        settings = {
            "permissions": {
                "allow": [
                    f"Write({worktree_str}/**)",
                    f"Edit({worktree_str}/**)",
                ],
            }
        }

        settings_path = claude_dir / "settings.json"
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        # 2. Gemini Policy
        gemini_policies_dir = worktree_path / ".gemini" / "policies"
        gemini_policies_dir.mkdir(parents=True, exist_ok=True)

        # Use re.escape() to handle all regex metacharacters in the path robustly.
        worktree_regex = re.escape(worktree_str)
        policy_content = f"""# academicOps: Sandbox agent to this worktree
[[rule]]
toolName = "Write"
argsPattern = "^{worktree_regex}.*"
decision = "allow"
priority = 50

[[rule]]
toolName = "Edit"
argsPattern = "^{worktree_regex}.*"
decision = "allow"
priority = 50

[[rule]]
toolName = "Write"
decision = "deny"
priority = 10
denyMessage = "File writes are restricted to the worktree: {worktree_str}"

[[rule]]
toolName = "Edit"
decision = "deny"
priority = 10
denyMessage = "File edits are restricted to the worktree: {worktree_str}"
"""
        policy_path = gemini_policies_dir / "sandbox.toml"
        policy_path.write_text(policy_content)

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
            commits_behind_res = subprocess.run(
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
            if commits_behind_res.returncode == 0:
                count = int(commits_behind_res.stdout.strip())
                if count > 0:
                    # Threshold for silent rebase
                    threshold = 5
                    if count > threshold:
                        print(
                            f"🔄 Worktree is {count} commits behind origin/{default_branch}. "
                            f"Attempting auto-rebase...",
                            file=sys.stderr,
                        )

                    # Guard: dirty working tree causes rebase to fail immediately
                    dirty_check = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True,
                    )
                    if dirty_check.stdout.strip():
                        raise RuntimeError(
                            f"Worktree at {worktree_path} has uncommitted changes; "
                            f"cannot auto-rebase. Commit or stash changes first."
                        )

                    rebase_result = subprocess.run(
                        ["git", "rebase", f"origin/{default_branch}"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True,
                    )

                    if rebase_result.returncode != 0:
                        # Rebase failed: abort and surface error
                        subprocess.run(
                            ["git", "rebase", "--abort"],
                            cwd=worktree_path,
                            capture_output=True,
                        )
                        print(
                            f"❌ Auto-rebase failed. "
                            f"Worktree is {count} commits behind origin/{default_branch}. "
                            f"Please resolve manually in {worktree_path}.\n"
                            f"{rebase_result.stderr.strip()}",
                            file=sys.stderr,
                        )
                        raise RuntimeError(
                            f"Worktree at {worktree_path} could not be cleanly rebased "
                            f"onto origin/{default_branch}. Rebase failed: {rebase_result.stderr.strip()}"
                        )

                    if count > threshold:
                        print("  ✅ Rebase successful.", file=sys.stderr)

        # Note: Worktrees inherit the mirror's remotes, which already have
        # the correct origin push URL (git@github.com:...). No need to
        # reconfigure here. (A previous attempt to set-url --push here
        # had a bug that corrupted the push URL to the literal string "origin".)

    @staticmethod
    def _propagate_git_identity(source_repo: Path, target_repo: Path):
        """Copy user.name and user.email from source repo to target if not already set."""
        for key in ("user.name", "user.email"):
            # Check if already set in target
            check = subprocess.run(
                ["git", "config", key], cwd=target_repo, capture_output=True, text=True
            )
            if check.returncode == 0 and check.stdout.strip():
                continue
            # Read from source
            result = subprocess.run(
                ["git", "config", key], cwd=source_repo, capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                subprocess.run(
                    ["git", "config", key, result.stdout.strip()],
                    cwd=target_repo,
                    check=False,
                )

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
        if self.storage is not None:
            task = self.storage.get_task(task_id)
        else:
            try:
                from polecat.pkb_bridge import get_task as pkb_get_task

                task = pkb_get_task(task_id)
            except Exception:
                # Network/transient error — treat as "task not found" so the
                # worktree URL-recovery path below can run rather than
                # propagating an exception that bypasses cleanup entirely.
                task = None
        worktree_path = self.polecats_dir / task_id

        if task:
            repo_path = self.get_repo_path(task)
        else:
            # Task lookup failed (e.g. task deleted). Try to recover from the
            # worktree's own origin URL rather than silently falling back to
            # REPO_ROOT — falling back to academicOps could delete branches
            # from the wrong repo on a task_id collision.
            repo_path = None
            if worktree_path.exists() and (worktree_path / ".git").exists():
                try:
                    remote_url = self._get_remote_url(worktree_path)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    remote_url = None
                if remote_url:
                    for name, cfg in self.projects.items():
                        candidate = cfg.get("path")
                        if candidate is None:
                            continue
                        try:
                            candidate_url = self._get_remote_url(Path(candidate))
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                        if candidate_url == remote_url:
                            repo_path = Path(candidate)
                            break
                        mirror = self.repos_dir / f"{name}.git"
                        if mirror.exists() and str(mirror) == remote_url:
                            repo_path = mirror
                            break
            if repo_path is None:
                raise ValueError(
                    f"Cannot nuke worktree for task {task_id}: task lookup "
                    f"failed and the worktree's origin URL could not be "
                    f"matched against any configured project. Refusing to "
                    f"fall back to REPO_ROOT (would risk operating on the "
                    f"wrong repository)."
                )
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
            print(f"Removing clone {worktree_path}...")
            shutil.rmtree(worktree_path, ignore_errors=True)

        if self._branch_exists(repo_path, branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
