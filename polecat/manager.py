#!/usr/bin/env python3
import fcntl
import os
import shutil
import subprocess
import sys
import urllib.error
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


def get_config_path() -> Path:
    """Get the unified config path: $AOPS_SESSIONS/polecat.yaml.

    This file holds both project registry (projects, project_aliases,
    crew_names — read here via ``load_config``) and operational config
    (gates, hooks_enabled, model, docker, external_agents — read by
    ``aops-core/lib/polecat_config.py``). Single SSoT, two consumers.
    """
    if env_path := os.environ.get("AOPS_POLECAT_CONFIG"):
        return Path(env_path).expanduser()
    sessions = os.environ.get("AOPS_SESSIONS")
    if sessions:
        sessions_path = Path(sessions).expanduser()
    else:
        sessions_path = get_polecat_home() / "sessions"
    return sessions_path / "polecat.yaml"


def get_local_overlay_path() -> Path:
    """Get the machine-local overlay path: $POLECAT_HOME/local.yaml."""
    return get_polecat_home() / "local.yaml"


def load_config(config_path: Path | None = None) -> dict:
    """Load the unified config from $AOPS_SESSIONS/polecat.yaml."""
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Polecat config not found: {config_path}\n"
            f"Set $AOPS_SESSIONS to your sessions repo and ensure polecat.yaml exists. "
            f"See polecat/defaults/polecat.yaml.example for the canonical schema."
        )

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def load_local_overlay(overlay_path: Path | None = None) -> dict:
    """Load the per-machine overlay (paths only). Empty if file missing."""
    if overlay_path is None:
        overlay_path = get_local_overlay_path()
    if not overlay_path.exists():
        return {}
    with open(overlay_path) as f:
        return yaml.safe_load(f) or {}


def _expand_env(value: str) -> str:
    """Expand ${VAR} and ~ in a string value."""
    return os.path.expandvars(os.path.expanduser(value))


def resolve_project_path(
    slug: str,
    repo: str | None = None,
    overlay_path: Path | None = None,
    overlay: dict | None = None,
) -> Path | None:
    """Resolve a project slug to an on-disk path.

    Order:
    1. `sessions` slug always resolves via $AOPS_SESSIONS (the same env var the
       rest of the framework uses, via lib.paths.get_sessions_repo). Bypasses
       overlay/convention so the registry path and the runtime path can't drift.
    2. $POLECAT_HOME/local.yaml `paths.<slug>` (with ${VAR} interpolation)
    3. $AOPS_SRC_DIR/<repo> if it has .git
    4. Legacy fallbacks: ~/src/<repo>, ~/<repo>, /opt/$USER/<repo>

    Pass `overlay` to skip re-reading local.yaml when batch-resolving.
    Returns None if no candidate has a .git directory.
    """
    repo_name = repo or slug

    if slug == "sessions":
        sessions_env = os.environ.get("AOPS_SESSIONS")
        if sessions_env:
            candidate = Path(_expand_env(sessions_env))
            return candidate if candidate.exists() else None

    if overlay is None:
        overlay = load_local_overlay(overlay_path)
    overlay_paths = overlay.get("paths", {}) or {}
    if slug in overlay_paths:
        candidate = Path(_expand_env(str(overlay_paths[slug])))
        return candidate if candidate.exists() else None

    src_dir = os.environ.get("AOPS_SRC_DIR")
    search_dirs = []
    if src_dir:
        search_dirs.append(Path(_expand_env(src_dir)))
    search_dirs.extend(
        [
            Path.home() / "src",
            Path.home(),
            Path("/opt") / os.environ.get("USER", "user"),
        ]
    )

    for base in search_dirs:
        candidate = base / repo_name
        if candidate.exists() and (candidate / ".git").exists():
            return candidate
    return None


def load_projects(
    config_path: Path | None = None,
    overlay_path: Path | None = None,
    config: dict | None = None,
) -> dict:
    """Load project registry. Returns dict slug -> {path: Path|None, default_branch, repo, ...}.

    Pass `config` to skip re-reading polecat.yaml when callers already loaded it.

    NOTE: `path` may be None when the repo isn't found via overlay or convention.
    Callers must check `if entry["path"] is None` before using it.
    """
    if config is None:
        config = load_config(config_path)
    overlay = load_local_overlay(overlay_path)

    projects = {}
    for slug, proj in (config.get("projects") or {}).items():
        proj = proj or {}
        repo = proj.get("repo", slug)
        # Per-project aliases: optional list of shorthand names accepted in
        # place of the canonical slug (e.g. ['academicOps', 'acaops']).
        aliases_raw = proj.get("aliases") or []
        if not isinstance(aliases_raw, list):
            aliases_raw = [aliases_raw]
        aliases = [str(a) for a in aliases_raw]
        entry = {
            "path": resolve_project_path(slug, repo, overlay=overlay),
            "default_branch": proj.get("default_branch", "main"),
            "repo": repo,
            "aliases": aliases,
        }
        for key in ("auto_commit", "merge_strategy"):
            if key in proj:
                entry[key] = proj[key]
        projects[slug] = entry
    return projects


def load_project_aliases(config_path: Path | None = None) -> dict[str, str]:
    """Load shorthand aliases that map to project slugs.

    Aliases come from three sources, merged in priority order (first wins):
        1. Top-level ``project_aliases:`` block in polecat.yaml::

               project_aliases:
                   bm: buttermilk

        2. Per-project ``aliases:`` list under each project entry::

               projects:
                 aops:
                   aliases: [academicOps, acaops]

        3. Each project's ``repo:`` field (so the GitHub repo name resolves
           to its project slug).

    Built-in: every project slug resolves to itself.
    """
    config = load_config(config_path)
    aliases: dict[str, str] = {}

    # 1. Top-level project_aliases (highest priority)
    for alias, slug in (config.get("project_aliases") or {}).items():
        aliases[str(alias)] = str(slug)

    projects_block = config.get("projects") or {}

    # 2. Per-project aliases lists
    for slug, proj in projects_block.items():
        proj = proj or {}
        for alias in proj.get("aliases") or []:
            aliases.setdefault(str(alias), slug)

    # 3. Repo name (only if not already mapped)
    for slug, proj in projects_block.items():
        proj = proj or {}
        repo = proj.get("repo")
        if repo:
            aliases.setdefault(str(repo), slug)

    # Canonical slugs always resolve to themselves
    for slug in projects_block:
        aliases.setdefault(slug, slug)

    return aliases


def load_crew_names(config_path: Path | None = None) -> list[str]:
    """Load crew names from the project registry."""
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

        # Project registry path ($AOPS_SESSIONS/polecat.yaml)
        self.config_path = get_config_path()

        # Ensure home directory exists
        self.home_dir.mkdir(parents=True, exist_ok=True)

        # Location for active polecat worktrees. A dedicated subdirectory so
        # stale-cleanup loops have a bounded namespace to iterate — the home
        # dir also holds sessions/, local.yaml, and other non-worktree state
        # that must never be treated as deletion candidates.
        self.polecats_dir = self.home_dir / "worktrees"
        self.polecats_dir.mkdir(parents=True, exist_ok=True)

        # Hidden directory for bare mirror repos (at home_dir, not under
        # polecats_dir, so it's excluded from worktree iteration).
        self.repos_dir = self.home_dir / ".repos"
        self.repos_dir.mkdir(exist_ok=True)

        # Directory for persistent crew workers (at home_dir, distinct from
        # per-task worktrees).
        self.crew_dir = self.home_dir / "crew"
        self.crew_dir.mkdir(exist_ok=True)

        # Load project registry from $AOPS_SESSIONS/polecat.yaml
        self.overlay_path = self.home_dir / "local.yaml"
        self.config = load_config(self.config_path)
        self.projects = load_projects(
            self.config_path, overlay_path=self.overlay_path, config=self.config
        )

        # Unresolved projects are warned (not raised) so partial-checkout
        # workflows like `polecat sync` and the daily skill can gracefully skip
        # repos that aren't present locally. Consumers that actually need a
        # missing path (e.g. get_repo_path) raise on demand.
        unresolved = [slug for slug, p in self.projects.items() if p["path"] is None]
        if unresolved:
            print(
                f"polecat: {len(unresolved)} project(s) not found locally: "
                f"{sorted(unresolved)}. Add to {self.overlay_path} under `paths:` to override.",
                file=sys.stderr,
            )

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

        Tries in order:
            1. canonical project slug
            2. ``project_aliases`` map (top-level + per-project + repo names)
            3. fall back to the project whose ``repo`` field matches

        Args:
            alias: Shorthand alias (e.g., 'bm'), repo name (e.g., 'academicOps'),
                or canonical slug (e.g., 'aops').

        Returns:
            Canonical project slug

        Raises:
            ValueError: If the value is not recognized.
        """
        # 1. Already a canonical slug
        if alias in self.projects:
            return alias
        # 2. Top-level / per-project alias map (also includes repo names)
        if alias in self.project_aliases:
            return self.project_aliases[alias]
        # 3. Repo-field fallback (defence in depth — load_project_aliases
        #    already folds repo names in, but cover hand-built managers).
        for slug, proj in self.projects.items():
            if proj.get("repo") == alias:
                return slug
        raise ValueError(self._format_unknown_project_error(alias))

    def _format_unknown_project_error(self, value: str) -> str:
        """Build an error message listing canonical projects and their aliases."""
        # Group aliases by canonical slug for a readable display.
        aliases_for: dict[str, list[str]] = {slug: [] for slug in self.projects}
        for alias, slug in self.project_aliases.items():
            if alias == slug:
                continue  # self-reference, not informative
            aliases_for.setdefault(slug, []).append(alias)
        # Also surface the repo: field as an alias if not already listed.
        for slug, proj in self.projects.items():
            repo = proj.get("repo")
            if repo and repo != slug and repo not in aliases_for[slug]:
                aliases_for[slug].append(repo)

        parts = []
        for slug in sorted(self.projects):
            extras = sorted(set(aliases_for.get(slug, [])))
            if extras:
                parts.append(f"{slug} (aliases: {', '.join(extras)})")
            else:
                parts.append(slug)
        return f"unknown project {value!r}. Known: {', '.join(parts)}"

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

    def _branch_has_merged_pr(self, repo_path: Path, branch_name: str) -> str | None:
        """Return PR URL if branch has a merged PR on GitHub, else None.

        Catches squash-merged and rebase-merged branches where the branch tip
        is NOT an ancestor of default_branch — so the ``merge-base --is-ancestor``
        check returns false even though the branch's work has landed.

        gh unavailable or network failure returns None (best-effort — callers
        should combine with other staleness signals).
        """
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
                    "merged",
                    "--limit",
                    "1",
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

        # Accept canonical slugs, aliases, and repo names. Canonicalise so
        # downstream mirror/path lookups always use the project key.
        try:
            project = self.resolve_project_alias(task.project)
        except ValueError as e:
            mirror_path = self.repos_dir / f"{task.project}.git"
            if mirror_path.exists():
                # Bare mirror present even though slug isn't in polecat.yaml —
                # honour it (matches prior behaviour).
                return mirror_path
            raise ValueError(
                f"Task {task.id} references {e} (also no bare mirror at {mirror_path})"
            ) from None

        # Persist canonical slug back on the task so subsequent steps
        # (sync_mirror, default_branch lookup) use the registry key.
        task.project = project

        # Check for bare mirror first
        mirror_path = self.repos_dir / f"{project}.git"
        if mirror_path.exists():
            return mirror_path

        return self.projects[project]["path"]

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
            True if mirror is fresh after sync, False if sync failed or remains stale.
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

                # Get default refspecs from git config to ensure we fetch everything
                # even when some branches are excluded.
                config_result = subprocess.run(
                    ["git", "config", "--get-all", "remote.origin.fetch"],
                    cwd=mirror_path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                default_refspecs = config_result.stdout.splitlines()
                if not default_refspecs:
                    default_refspecs = ["+refs/heads/*:refs/heads/*"]

                exclude_refspecs = self._worktree_exclude_refspecs(mirror_path)
                if exclude_refspecs:
                    branches = [r.removeprefix("^refs/heads/") for r in exclude_refspecs]
                    print(f"  Skipping worktree branches during bulk fetch: {', '.join(branches)}")

                # Bulk fetch all branches except those checked out.
                # Must include default_refspecs otherwise git skips them when exclude_refspecs is present.
                origin_result = subprocess.run(
                    ["git", "fetch", "origin", *default_refspecs, *exclude_refspecs],
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

                # Branches checked out in worktrees were excluded from the
                # normal origin fetch above. Update them by fetching by SHA
                # (bypasses git's "branch is checked out" guard) and then
                # updating the branch ref.

                # Single ls-remote call for all branches: avoids per-branch network
                # round-trips and eliminates prefix-match false positives
                # (ls-remote for "feat" would otherwise also match "feat-fix").
                ls_result = subprocess.run(
                    ["git", "ls-remote", "origin", "refs/heads/*"],
                    cwd=mirror_path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                remote_refs: dict[str, str] = {}
                if ls_result.returncode == 0:
                    for line in ls_result.stdout.splitlines():
                        parts = line.split()
                        if len(parts) == 2:
                            remote_refs[parts[1]] = parts[0]

                for excl_refspec in exclude_refspecs:
                    branch = excl_refspec.removeprefix("^refs/heads/")
                    remote_sha = remote_refs.get(f"refs/heads/{branch}")
                    if not remote_sha:
                        continue

                    # Instrumentation: check SHA before update
                    local_sha_result = subprocess.run(
                        ["git", "rev-parse", f"refs/heads/{branch}"],
                        cwd=mirror_path,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    local_sha = local_sha_result.stdout.strip()

                    if local_sha == remote_sha:
                        continue

                    print(
                        f"  🔄 Branch {branch} is checked out and stale: {local_sha[:8]} -> {remote_sha[:8]}"
                    )

                    # Fetch by SHA (doesn't trigger checked-out guard)
                    fetch_result = subprocess.run(
                        ["git", "fetch", "origin", remote_sha],
                        cwd=mirror_path,
                        capture_output=True,
                        check=False,
                    )
                    if fetch_result.returncode == 0:
                        # update-ref is allowed on checked-out branches in bare repos
                        update_result = subprocess.run(
                            ["git", "update-ref", f"refs/heads/{branch}", remote_sha],
                            cwd=mirror_path,
                            check=False,
                            capture_output=True,
                        )
                        if update_result.returncode == 0:
                            print(f"  ✅ Updated checked-out branch {branch} to {remote_sha[:8]}")
                        else:
                            print(
                                f"  ⚠ Failed to update checked-out branch {branch}: {update_result.stderr.decode().strip()}",
                                file=sys.stderr,
                            )
                    else:
                        print(
                            f"  ⚠ Failed to fetch SHA {remote_sha[:8]} for branch {branch}",
                            file=sys.stderr,
                        )

                # Final verification: is the mirror now fresh?
                is_fresh, message = self.check_mirror_freshness(project)
                if not is_fresh:
                    print(f"  ⚠ Mirror remains stale after sync: {message}", file=sys.stderr)
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
        """Checks if the mirror's default branch is in sync with origin. Read-only.

        Compares the mirror's refs/heads/{default_branch} SHA against what
        origin reports via ls-remote. Makes no mutations — sync is the job
        of safe_sync_mirror.

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

                        # Capture prior status for rollback if downstream setup
                        # (e.g. worktree creation) fails. Stored on the returned
                        # object so the caller can restore the canonical value
                        # rather than guessing.
                        prior_status = fresh_task.status
                        prior_status_value = (
                            prior_status.value
                            if hasattr(prior_status, "value")
                            else str(prior_status)
                        )
                        fresh_task.status = self.task_status.IN_PROGRESS
                        fresh_task.assignee = caller
                        self.storage.save_task(fresh_task)
                        # Annotate for rollback. Use a leading underscore so it
                        # isn't mistaken for a persisted field.
                        try:
                            fresh_task._prior_status = prior_status_value
                        except AttributeError:
                            # Some task models forbid arbitrary attrs; rollback
                            # will fall back to the canonical default.
                            pass
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

        # Canonical statuses agents may pull from. `ready` is the standard
        # decomposed-and-unblocked state; `queued` is the human-promoted gate.
        # See aops-core/skills/remember/references/TAXONOMY.md.
        _CLAIMABLE_STATUSES = ("ready", "queued")

        for task in tasks:
            # Re-fetch to get fresh status (avoid race)
            fresh = get_task(task.id)
            if fresh is None or fresh.status not in _CLAIMABLE_STATUSES:
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

            # Capture prior canonical status before claiming so a downstream
            # failure (e.g. worktree setup) can restore it. Annotated on the
            # returned object via a leading-underscore attribute to avoid
            # being mistaken for a persisted field.
            prior_status = fresh.status

            # Claim via MCP update_task (atomic at server level)
            try:
                success = update_task(fresh.id, status="in_progress", assignee=caller)
                if not success:
                    # Server returned an error (already logged to stderr in call_tool)
                    continue
            except (TimeoutError, urllib.error.URLError) as e:
                # Timeout/Network error: we don't know if it succeeded on server.
                # Verify state before bailing.
                print(f"⚠️  PKB claim timeout for {fresh.id}: {e}", file=sys.stderr)
                print("   Verifying if claim succeeded despite timeout...", file=sys.stderr)
                try:
                    verified = get_task(fresh.id)
                    if (
                        verified
                        and verified.status == "in_progress"
                        and verified.assignee == caller
                    ):
                        print("   ✅ Verified: claim succeeded. Proceeding.", file=sys.stderr)
                        try:
                            verified._prior_status = prior_status
                        except AttributeError:
                            pass
                        return verified
                except Exception as ve:
                    print(f"   ❌ Verification failed: {ve}", file=sys.stderr)

                print(f"   Task {fresh.id} may be stranded in_progress.", file=sys.stderr)
                print(
                    f"   Recovery: polecat reset-stalled --hours 0 --project {fresh.project or 'aops'}",
                    file=sys.stderr,
                )
                raise

            fresh.status = "in_progress"
            fresh.assignee = caller
            try:
                fresh._prior_status = prior_status
            except AttributeError:
                pass
            return fresh

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
            is_fresh = self.safe_sync_mirror(project)
            if not is_fresh:
                print("⚠ Mirror may be stale after sync", file=sys.stderr)
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
                    # Existing valid worktree - still verify it's based on recent main
                    self._verify_worktree_setup(worktree_path, branch_name, default_branch)
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

        # Check if the branch exists on remote. Three outcomes:
        #   1. Does not exist → create fresh from default branch
        #   2. Exists and is stale (merged / squash-merged / abandoned) → delete remote + fresh
        #   3. Exists and is legitimately in-flight → fetch + checkout tracking
        #
        # "Stale" covers several failure modes that all produce the same bug —
        # polecat resumes from a branch whose work has already landed, or which
        # has diverged so far from main that rebasing is a rathole:
        #   a. Merge-commit merged: branch tip is an ancestor of origin/main
        #   b. Squash/rebase merged: branch tip is NOT an ancestor, but GitHub
        #      reports a merged PR on the branch — the canonical re-dispatch case
        #   c. Abandoned: not merged, far behind main, no open PR — rebasing is
        #      not worth the turns, start fresh
        branch_exists_result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        create_fresh = not branch_exists_result.stdout.strip()

        if not create_fresh:
            # Fetch both refs so is-ancestor and rev-list have accurate data.
            subprocess.run(
                ["git", "fetch", "origin", branch_name],
                cwd=worktree_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "fetch", "origin", default_branch],
                cwd=worktree_path,
                capture_output=True,
                check=True,
            )

            stale_reason: str | None = None

            # (a) Merge-commit merged — branch is an ancestor of default.
            is_ancestor = (
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
            if is_ancestor:
                stale_reason = f"already merged into {default_branch}"

            # (b) Squash/rebase merged — gh reports a merged PR on this branch.
            if stale_reason is None:
                merged_pr_url = self._branch_has_merged_pr(worktree_path, branch_name)
                if merged_pr_url:
                    stale_reason = f"merged PR exists ({merged_pr_url})"

            # (c) Far behind with no open PR — likely abandoned.
            if stale_reason is None:
                rev_list = subprocess.run(
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
                commits_behind = int(rev_list.stdout.strip())
                if commits_behind > 100:
                    open_pr_url = self._crew_branch_open_pr(worktree_path, branch_name)
                    if open_pr_url:
                        # Open PR exists — don't destroy the work. Fail loudly so
                        # whoever revived the task can decide how to handle it.
                        raise RuntimeError(
                            f"Target branch {branch_name} is {commits_behind} commits "
                            f"behind {default_branch} and has an open PR ({open_pr_url}). "
                            "Refusing to discard in-flight work — rebase or close the PR "
                            "before re-dispatching."
                        )
                    stale_reason = (
                        f"{commits_behind} commits behind {default_branch} with no open PR"
                    )

            if stale_reason is not None:
                print(f"  🗑 Branch {branch_name} is stale: {stale_reason}.")
                print(f"  Deleting remote branch and starting fresh from {default_branch}...")
                delete_result = subprocess.run(
                    ["git", "push", "origin", "--delete", branch_name],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                )
                if delete_result.returncode != 0:
                    # Already-deleted is fine; a real push failure is not.
                    stderr = delete_result.stderr.strip()
                    if "remote ref does not exist" not in stderr:
                        print(f"  ⚠ Could not delete remote branch {branch_name}: {stderr}")
                else:
                    print(f"  ✅ Deleted stale remote branch {branch_name}")
                create_fresh = True

        if create_fresh:
            # Create fresh from default branch. Clone usually already has it checked out.
            subprocess.run(["git", "checkout", default_branch], cwd=worktree_path, check=False)
            subprocess.run(
                ["git", "checkout", "-B", branch_name, f"origin/{default_branch}"],
                cwd=worktree_path,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
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
        # Ensure we have the latest origin/main for comparison
        fetch_result = subprocess.run(
            ["git", "fetch", "origin", default_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if fetch_result.returncode != 0:
            raise RuntimeError(
                f"Failed to fetch origin/{default_branch} in {worktree_path}: "
                f"{fetch_result.stderr.strip()}"
            )

        # Get the merge-base between our branch and origin/main
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", f"origin/{default_branch}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if merge_base_result.returncode == 0:
            merge_base = merge_base_result.stdout.strip()
            # Check how many commits behind origin/main we are
            commits_behind_res = subprocess.run(
                [
                    "git",
                    "rev-list",
                    "--count",
                    f"{merge_base}..origin/{default_branch}",
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

    def _count_unpushed_commits(
        self,
        repo_path: Path,
        branch_name: str,
        worktree_path: Path | None = None,
        base: str = "main",
    ) -> tuple[int, str]:
        """Count local commits on branch_name that are not on origin.

        Returns (count, detail). ``count == 0`` means "safe to delete"; a
        positive count means commits would be lost if the worktree/branch is
        destroyed.

        Comparison strategy (in order):
        1. If ``refs/remotes/origin/<branch_name>`` exists: compare against it
           (catches the "pushed earlier then added more commits" case).
        2. Otherwise: compare against ``origin/<base>`` (branch never pushed).

        If the worktree is still on disk we prefer to read commits from there
        so that a detached local branch in the shared repo (whose ref may be
        stale) does not produce false negatives.
        """
        # Prefer the worktree as the source of truth for HEAD of the branch,
        # since polecat worktrees can commit without the shared repo's branch
        # ref being updated.
        query_cwd = worktree_path if (worktree_path and worktree_path.exists()) else repo_path

        # Does origin/<branch> exist?
        remote_ref = f"refs/remotes/origin/{branch_name}"
        check_remote = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)", remote_ref],
            cwd=query_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        has_remote = bool(check_remote.returncode == 0 and check_remote.stdout.strip())

        # Resolve the HEAD of the branch in our query repo.
        head_rev = subprocess.run(
            ["git", "rev-parse", "HEAD" if query_cwd == worktree_path else branch_name],
            cwd=query_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if head_rev.returncode != 0:
            # Can't resolve — nothing to lose.
            return 0, "branch HEAD could not be resolved"

        compare_ref = f"origin/{branch_name}" if has_remote else f"origin/{base}"
        rev_list = subprocess.run(
            ["git", "rev-list", "--count", f"{compare_ref}..{head_rev.stdout.strip()}"],
            cwd=query_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_list.returncode != 0:
            # Base ref missing (e.g., no origin/main). Be conservative: if the
            # branch has any commits at all, treat as unpushed.
            any_commits = subprocess.run(
                ["git", "rev-list", "--count", head_rev.stdout.strip()],
                cwd=query_cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            try:
                n = int(any_commits.stdout.strip() or 0)
            except ValueError:
                return 0, "could not determine commit count"
            if n > 0:
                return n, f"{compare_ref} not found; {n} commit(s) on branch with no remote base"
            return 0, ""

        try:
            count = int(rev_list.stdout.strip() or 0)
        except ValueError:
            return 0, "could not parse rev-list output"
        if count == 0:
            return 0, ""
        if has_remote:
            return count, f"{count} commit(s) ahead of origin/{branch_name}"
        return count, f"{count} commit(s) on {branch_name} have never been pushed to origin"

    def nuke_worktree(self, task_id, force=False, allow_unpushed=False):
        """Removes the worktree and deletes the branch.

        Args:
            task_id: The task ID whose worktree should be removed
            force: If True, skip merge verification + uncommitted-changes checks
                (the "WIP is fine, destroy it" override).
            allow_unpushed: If True, skip the unpushed-commits integrity gate.
                Separate from ``force`` on purpose: unpushed commits are an
                integrity problem (A3/A8) — destroying them irrecoverably loses
                work. Callers must opt in explicitly rather than inheriting the
                bypass from ``force``.

        Raises:
            RuntimeError: If branch has unmerged commits and force=False, OR
                the branch has commits that were never pushed to origin and
                ``allow_unpushed`` is False.
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

        if task and task.project:
            repo_path = self.get_repo_path(task)
        else:
            # Task has no project, or task lookup failed (e.g. task deleted).  Try to recover from the
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

        # A3/A8 integrity gate: refuse to destroy unpushed commits.
        # Separate from force=/--force because this is about losing committed
        # work, not about unmerged WIP. Bypass only via explicit
        # ``allow_unpushed=True`` (CLI: ``--allow-unpushed``). See
        # task-0e4d20a8 / cheryl 2026-04-18 for the incident that motivated
        # this gate.
        if not allow_unpushed and self._branch_exists(repo_path, branch_name):
            count, detail = self._count_unpushed_commits(
                repo_path, branch_name, worktree_path=worktree_path
            )
            if count > 0:
                raise RuntimeError(
                    f"Refusing to nuke worktree for task {task_id}: {detail}. "
                    f"Push the branch ('git push -u origin {branch_name}') or "
                    f"pass --allow-unpushed to discard the commits. "
                    f"(This gate exists because an ephemeral container being "
                    f"torn down with unpushed commits is unrecoverable.)"
                )

        if worktree_path.exists():
            print(f"Removing clone {worktree_path}...")
            shutil.rmtree(worktree_path, ignore_errors=True)

        if self._branch_exists(repo_path, branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=False)
