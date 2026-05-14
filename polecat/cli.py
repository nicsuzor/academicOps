#!/usr/bin/env python3
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

# Issue #521: Gemini workers have no Stop hook; polecat must poll PKB and
# kill the container after the task transitions to a terminal status.
TERMINAL_PKB_STATUSES = frozenset({"done", "merge_ready", "blocked", "cancelled"})
DEFAULT_TERMINATION_GRACE_SECONDS = 60
TERMINATION_SIGKILL_DELAY_SECONDS = 30
TERMINATION_POLL_INTERVAL_SECONDS = 10

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import click
from lib.agent_env import apply_env_mappings, get_container_env_forwards
from lib.polecat_config import CONFIG_PATH_ENV, PolecatConfig, load_polecat_config
from lib.session_naming import derive_polecat_session_id

from polecat.manager import PolecatManager
from polecat.observability import metrics
from polecat.validation import TaskIDValidationError, validate_task_id_or_raise

# In-container path for the staged polecat.yaml. Hooks running inside the
# container read AOPS_POLECAT_CONFIG (set by ``_build_docker_cmd``) to resolve
# this same file.
_CONTAINER_POLECAT_YAML = "/home/worker/.aops/polecat.yaml"

# Turn budget for headless Claude runs.
#
# Claude SDK semantics: one "turn" = one full agentic loop iteration.
# An iteration starts when the model generates a response (which may contain
# multiple tool_use blocks) and ends when all tool results are returned.
# Calling 10 tools in a single response still counts as ONE turn.
#
# Tiered defaults by task effort (XS/S/M/L from task frontmatter):
#   XS  →  40  (trivial, single-file edits)
#   S   →  70  (small, a few files)
#   M   → 100  (typical PR-scoped work — the new default)
#   L   → 150  (large, multi-component or epic-decomposition-shaped)
#   (no effort field) → 100
#
# Hook overhead: each session fires ~2-4 hook turns (hydration gate,
# enforcer compliance check). These count against the budget.
_EFFORT_TO_MAX_TURNS: dict[str, int] = {
    "xs": 40,
    "s": 70,
    "m": 100,
    "l": 150,
}
_DEFAULT_MAX_TURNS = 100


# Canonical PKB status used as a rollback fallback when the task object does
# not carry a captured prior status. `queued` is the human-promoted dispatch
# gate per aops-core/skills/remember/references/TAXONOMY.md; restoring there
# keeps the task eligible for a future polecat run without re-triage.
# NEVER use the historical legacy "active" — PKB rejects it as Invalid status.
_ROLLBACK_FALLBACK_STATUS = "queued"


def _rollback_status_for(task) -> str:
    """Return the canonical PKB status to restore on worktree-setup failure.

    Prefers the prior status captured by ``PolecatManager.claim_next_task``
    (annotated as ``_prior_status``). Falls back to ``queued`` when absent.
    Coerces enum-valued statuses to their string ``.value``.
    """
    prior = getattr(task, "_prior_status", None)
    if prior is None:
        return _ROLLBACK_FALLBACK_STATUS
    if hasattr(prior, "value"):
        prior = prior.value
    prior_str = str(prior)
    # Defensive: never write the non-canonical legacy "active" back to PKB.
    if prior_str in ("", "active", "in_progress"):
        return _ROLLBACK_FALLBACK_STATUS
    return prior_str


def _compute_max_turns(task) -> str:
    """Return the --max-turns value for a headless Claude run.

    Derives the budget from the task's ``effort`` field (XS/S/M/L).
    Falls back to _DEFAULT_MAX_TURNS when the field is absent or unrecognised.
    Returns a string because subprocess args must be strings.
    """
    effort = getattr(task, "effort", None)
    turns = _DEFAULT_MAX_TURNS
    if isinstance(effort, str) and effort:
        turns = _EFFORT_TO_MAX_TURNS.get(effort.lower())
        if turns is None:
            print(
                f"⚠️  Unrecognised effort value '{effort}' — "
                f"expected XS/S/M/L. Using default {_DEFAULT_MAX_TURNS} turns.",
                file=sys.stderr,
            )
            turns = _DEFAULT_MAX_TURNS
    return str(turns)


def _emit_budget_hit_diagnostic(stdout: str, stderr: str, max_turns: str) -> None:
    """Detect and log a turn-budget exhaustion event.

    Scans agent output for Claude's "Reached max turns" message.
    When found, extracts the last tool call name from the output so
    supervisors can see where the agent was when the budget ran out,
    without having to dig through the full transcript.
    """
    combined = (stdout or "") + (stderr or "")
    if "Reached max turns" not in combined:
        return

    print(
        f"\n⛔ Turn budget exhausted (--max-turns {max_turns}).",
        file=sys.stderr,
    )
    print(
        "   Claude SDK semantics: one 'turn' = one assistant response + all tool results.\n"
        "   Multiple tool calls within one response count as a single turn.",
        file=sys.stderr,
    )

    # Find the last tool call name in the output.
    # Claude prints tool use as "Tool: <name>" or similar patterns.
    # We also look for JSON "tool_use" blocks and the CLI's "● <ToolName>" spinner lines.
    last_tool: str | None = None

    # Pattern: CLI spinner output "● ToolName(..." or "✓ ToolName(" or "✗ ToolName("
    spinner_pattern = re.compile(r"[●✓✗⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s+([A-Za-z][A-Za-z0-9_]*)\s*\(")
    for m in spinner_pattern.finditer(combined):
        last_tool = m.group(1)

    if last_tool:
        print(f"   Last tool call observed: {last_tool}", file=sys.stderr)
    else:
        # Fall back: scan for any line containing a known tool-call pattern
        tool_line_pattern = re.compile(
            r"(?:Tool|tool_use|tool_name)[^\n]*?\b([A-Za-z][A-Za-z0-9_]*)\b"
        )
        for m in tool_line_pattern.finditer(combined):
            last_tool = m.group(1)
        if last_tool:
            print(f"   Last tool call observed: {last_tool}", file=sys.stderr)
        else:
            print("   Last tool call: (could not parse — check transcript)", file=sys.stderr)

    print(
        "   Supervisor action: raise effort tag (e.g. effort: L) or investigate over-exploration.",
        file=sys.stderr,
    )


# --- GitHub helpers (inlined from deleted polecat/github.py) ---


def _check_gh_installed() -> bool:
    """Check if GitHub CLI (gh) is installed and authenticated."""
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
        result = subprocess.run(["gh", "auth", "status"], capture_output=True)
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _generate_pr_body(task, transcript_path: Path | None = None) -> str:
    """Generate a Pull Request body from a task object.

    When ``transcript_path`` is provided (and the task body does not already
    contain a transcript header from a previous run), a ``<details>`` block
    pointing to the real Claude Code session transcript is appended at the
    end. Idempotency is guaranteed because the description is stripped of
    any prior block before the new one is added.
    """
    body = task.body

    body = re.sub(r"\n*## Relationships\n[\s\S]*?(?=\n\n## |\Z)", "", body)
    title_pattern = re.compile(f"^# {re.escape(task.title)}\\s*\n", re.MULTILINE)
    body = title_pattern.sub("", body)

    # Strip any previously-appended transcript section/block so we re-emit
    # exactly one copy. This makes the PR body re-emit idempotent.
    body = re.sub(
        rf"\n*{re.escape(TRANSCRIPT_TASK_BODY_HEADER)}\n[\s\S]*?(?=\n##\s|\Z)",
        "",
        body,
    )
    body = re.sub(
        rf"\n*<details>\n{re.escape(TRANSCRIPT_PR_DETAILS_SUMMARY)}[\s\S]*?</details>\s*",
        "",
        body,
    )

    ac_match = re.search(
        r"(?i)^##\s+Acceptance Criteria\s*\n(.*?)(?=\n^## |\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )

    acceptance_criteria = []
    description = body

    if ac_match:
        ac_text = ac_match.group(1)
        description = body.replace(ac_match.group(0), "").strip()
        for line in ac_text.splitlines():
            line = line.strip()
            if re.match(r"^[-*]\s*\[[ xX]\]", line):
                acceptance_criteria.append(re.sub(r"^[-*]\s*\[[ xX]\]", "- [ ]", line))
            elif line:
                acceptance_criteria.append(line)
    else:
        checklist_items = re.findall(r"^[-*]\s*\[[ xX]\].*$", body, re.MULTILINE)
        if checklist_items:
            description = body.strip()
            for item in checklist_items:
                acceptance_criteria.append(re.sub(r"^[-*]\s*\[[ xX]\]", "- [ ]", item))

    parts = []
    if description:
        parts.append(description)
        parts.append("\n")
    if acceptance_criteria:
        parts.append("## Acceptance Criteria")
        parts.append("\n".join(acceptance_criteria))
        parts.append("\n")
    parts.append("---")
    parts.append(f"Closes {task.id}")
    parts.append(f"*Generated by Polecat for task {task.id}*")
    if transcript_path is not None:
        parts.append(_format_transcript_pr_details_block(transcript_path).strip())
    return "\n".join(parts)


def _node_version_key(p: Path) -> tuple[int, ...]:
    """Sort key for NVM node version directories using semver comparison.

    Lexicographic sorting gets v9.x.x > v20.x.x wrong because '9' > '2'.
    This extracts numeric components for correct ordering.
    """
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", p.name)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _resolve_session_config(
    mode: str,
    *,
    client: str,
    hooks_enabled: bool | None = None,
    model: str | None = None,
    debug: bool | None = None,
    set_overrides: tuple[str, ...] = (),
) -> tuple[PolecatConfig, "SessionDefaults"]:  # type: ignore[name-defined]  # noqa: F821
    """Load polecat.yaml, apply per-mode overlay + CLI overrides, return both.

    The full ``PolecatConfig`` is returned alongside the resolved session
    defaults so callers can also reach ``cfg.docker`` etc.

    ``client`` is "claude", "gemini", or "shell" — used to route a CLI
    ``--model`` override to the matching client field. ``--model`` with
    ``client="shell"`` is rejected (interactive shell sessions don't run an
    agent CLI).
    """
    cfg = load_polecat_config()
    overrides: dict[str, object] = {}
    if hooks_enabled is not None:
        overrides["hooks_enabled"] = hooks_enabled
    if model is not None:
        if client == "claude":
            overrides["claude_model"] = model
        elif client == "gemini":
            overrides["gemini_model"] = model
        else:
            raise click.UsageError(
                f"--model has no effect for client={client!r}; drop the flag or pick claude/gemini"
            )
    if debug is not None:
        overrides["debug"] = debug
    for entry in set_overrides:
        if "=" not in entry:
            raise click.UsageError(f"--set expects KEY=VALUE, got {entry!r}")
        key, _, value = entry.partition("=")
        overrides[key.strip()] = _coerce_set_value(value.strip())
    resolved = cfg.with_overrides(mode, overrides) if overrides else cfg.for_mode(mode)
    return cfg, resolved


def _coerce_set_value(raw: str) -> object:
    """Coerce a ``--set`` value to bool / int / str."""
    lowered = raw.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def _make_worker_env(interactive: bool = False, work_dir: Path | None = None) -> dict[str, str]:
    """Create a sanitized environment for polecat/crew worker subprocesses.

    Strips SSH credentials and maps git auth to the bot token, ensuring
    workers can ONLY authenticate via the provided AOPS_BOT_GH_TOKEN.
    This runs agent-env-map.conf mappings eagerly (before subprocess launch)
    rather than relying on the SessionStart hook inside the child process.
    It also ensures 'uv' and other critical binaries are in the PATH.
    It also enables 24-bit color mode if interactive is True.
    """
    env = os.environ.copy()
    apply_env_mappings(env)

    # Strip ACA_DATA access unless the agent is specifically working in that repo.
    aca_data = env.get("ACA_DATA")
    if aca_data and work_dir:
        try:
            aca_path = Path(aca_data).resolve()
            if not work_dir.resolve().is_relative_to(aca_path):
                env.pop("ACA_DATA", None)
        except OSError:
            env.pop("ACA_DATA", None)
    elif aca_data:
        env.pop("ACA_DATA", None)

    if interactive:
        # Enable 24-bit color (TrueColor) for interactive sessions
        env["COLORTERM"] = "truecolor"
        env["FORCE_COLOR"] = "3"  # 3 = 24-bit color for Node.js chalk and others
    else:
        # Non-interactive workers: suppress color codes that confuse log parsers
        # and downstream tooling that doesn't consume ANSI escapes.
        env["FORCE_COLOR"] = "0"
        env["NO_COLOR"] = "1"

    # Standard non-interactive signals so CLIs default to scriptable behaviour
    # (no prompts, no pagers, no progress spinners). Set unconditionally — even
    # interactive polecat shells should not pop confirmation prompts at workers.
    env["CI"] = "true"
    env["NONINTERACTIVE"] = "1"

    # Ensure uv is in PATH for hooks and agent tools
    current_path = env.get("PATH", "")
    path_segments = [s for s in current_path.split(os.pathsep) if s]

    # Prepend common user-level bin paths if they exist and are not already in PATH.
    # Include nvm-managed node bin (for gemini/claude CLIs installed via npm).
    nvm_dir = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
    nvm_bin = os.environ.get("NVM_BIN", "")
    user_bin_paths = [
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / "bin"),
    ]
    # Add NVM bin if set, otherwise scan for nvm node versions
    if nvm_bin:
        user_bin_paths.append(nvm_bin)
    elif os.path.isdir(nvm_dir):
        versions_dir = Path(nvm_dir) / "versions" / "node"
        if versions_dir.is_dir():
            # Use the most recent node version's bin (semver sort, not lexicographic)
            node_versions = sorted(versions_dir.iterdir(), key=_node_version_key, reverse=True)
            if node_versions:
                user_bin_paths.append(str(node_versions[0] / "bin"))
    for p in reversed(user_bin_paths):
        if os.path.isdir(p) and p not in path_segments:
            path_segments.insert(0, p)

    env["PATH"] = os.pathsep.join(path_segments)

    # Prevent gh CLI from launching interactive prompts in non-TTY environments.
    # Workers run headless — any prompt would hang indefinitely.
    env["GH_PROMPT_DISABLED"] = "1"
    return env


def set_terminal_title(title: str) -> None:
    """Set terminal/tmux window title for session identification.

    Uses OSC 0 escape sequence (same as dotfiles set-tab-title function).
    In tmux, also sets the window name via rename-window so it appears
    in set-titles-string (#W) and the window list.
    """
    # OSC 0: Set window title — works in Terminal.app, iTerm2, most terminals
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()

    # If inside tmux, also rename the window for #W in set-titles-string
    if os.environ.get("TMUX"):
        tmux = shutil.which("tmux")
        if tmux:
            subprocess.run([tmux, "rename-window", title], capture_output=True)


def reset_terminal_title() -> None:
    """Reset terminal title to automatic naming after session ends."""
    if os.environ.get("TMUX"):
        tmux = shutil.which("tmux")
        if tmux:
            # Re-enable automatic window renaming
            subprocess.run(
                [tmux, "set-window-option", "automatic-rename", "on"],
                capture_output=True,
            )
    # Clear terminal title (let shell/terminal manage it)
    sys.stdout.write("\033]0;\007")
    sys.stdout.flush()


def _find_real_transcript(run_session_dir: Path | None) -> Path | None:
    """Find the real Claude Code session transcript under the run session dir.

    Globs ``<run_session_dir>/-workspace/*.jsonl`` and returns the newest by
    mtime, or ``None`` if nothing is found.
    """
    if run_session_dir is None:
        return None
    workspace = run_session_dir / "-workspace"
    if not workspace.is_dir():
        return None
    jsonls = list(workspace.glob("*.jsonl"))
    if not jsonls:
        return None
    return max(jsonls, key=lambda p: p.stat().st_mtime)


def _resolve_transcript_dir(home_dir: Path | None) -> Path:
    """Resolve the polecat transcripts directory.

    Prefers ``lib.paths.get_polecat_transcripts_dir`` when available; falls
    back to ``<home_dir|~/.polecat>/transcripts`` for older installations.
    Shared by lifecycle-event writer and reader so they always agree on the
    same path.
    """
    try:
        from lib.paths import get_polecat_transcripts_dir

        return get_polecat_transcripts_dir()
    except ImportError:
        base = home_dir or Path.home() / ".polecat"
        return Path(base) / "transcripts"


def _write_lifecycle_event(
    task_id: str,
    phase: str,
    home_dir: Path | None,
    **fields,
) -> None:
    """Append a lifecycle event to the polecat transcript stub.

    Best-effort: never raises. Fires at major phase boundaries so a supervisor
    can determine where a crashed run died (started → worktree_ready →
    agent_started → completed/failed). See task-a3bbf74c for context.
    """
    try:
        transcript_dir = _resolve_transcript_dir(home_dir)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "task_id": task_id,
            "phase": phase,
            "session_type": "polecat",
            **fields,
        }
        with open(transcript_dir / f"{task_id}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Observability MUST NEVER crash the run.
        pass


def save_worker_transcript(
    task_id: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    agent_type: str,
    home_dir: Path,
    real_transcript: Path | None = None,
) -> Path:
    """Save worker output to transcript file.

    Writes a JSONL entry with metadata and full output to
    $POLECAT_HOME/polecats/<task-id>.jsonl

    Args:
        task_id: The task identifier
        stdout: Captured standard output
        stderr: Captured standard error
        exit_code: Process exit code
        agent_type: "claude" or "gemini"
        home_dir: Polecat home directory (fallback if AOPS_SESSIONS not set)
        real_transcript: Resolved path to the real Claude Code session
            transcript (caller obtains via _find_real_transcript)

    Returns:
        Path to the transcript file

    Raises:
        OSError: If transcript directory cannot be created or file cannot be written
    """
    try:
        try:
            from lib.paths import get_polecat_transcripts_dir

            transcript_dir = get_polecat_transcripts_dir()
        except ImportError:
            # Fallback for older installations or missing lib.paths
            transcript_dir = home_dir / "transcripts"

        transcript_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = transcript_dir / f"{task_id}.jsonl"

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "task_id": task_id,
            "agent": agent_type,
            "session_type": "polecat",
            "exit_code": exit_code,
            "success": exit_code == 0,
            "stdout": stdout or "",
            "stderr": stderr or "",
            "real_transcript_path": str(real_transcript) if real_transcript else None,
            "real_transcript_size_bytes": (
                real_transcript.stat().st_size if real_transcript else None
            ),
        }

        with open(transcript_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return transcript_file
    except OSError as e:
        raise OSError(f"Failed to save transcript for task {task_id}: {e}") from e


# Marker strings used to detect prior emission so re-runs are idempotent.
TRANSCRIPT_TASK_BODY_HEADER = "## 📝 Polecat run transcript"
TRANSCRIPT_PR_DETAILS_SUMMARY = "<summary>Polecat run transcript</summary>"


def _read_latest_real_transcript_path(task_id: str, home_dir: Path) -> Path | None:
    """Return the most recently recorded real transcript path for ``task_id``.

    Reads ``$POLECAT_HOME/polecats/<task-id>.jsonl`` (the same file
    ``save_worker_transcript`` writes). Each line is a JSON object; we take
    the LAST line that has a non-null ``real_transcript_path`` and return it
    as a ``Path``.

    Returns ``None`` when the stub file does not exist, when no entry has a
    real transcript path, or when the file cannot be parsed.
    """
    try:
        try:
            from lib.paths import get_polecat_transcripts_dir

            transcript_dir = get_polecat_transcripts_dir()
        except ImportError:
            transcript_dir = home_dir / "transcripts"

        stub_file = transcript_dir / f"{task_id}.jsonl"
        if not stub_file.is_file():
            return None

        # Walk lines in reverse so we return the most recent recorded path
        # without buffering the whole file when only the tail matters.
        try:
            content = stub_file.read_text()
        except OSError:
            return None

        for line in reversed(content.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            path_str = entry.get("real_transcript_path")
            if path_str:
                return Path(path_str)
        return None
    except OSError:
        return None


def _format_transcript_task_body_section(transcript_path: Path) -> str:
    """Return the markdown section appended to the task body."""
    return f"\n\n{TRANSCRIPT_TASK_BODY_HEADER}\n- Transcript: `{transcript_path}`\n"


def _format_transcript_pr_details_block(transcript_path: Path) -> str:
    """Return the ``<details>`` block embedded in the PR body."""
    return f"\n\n<details>\n{TRANSCRIPT_PR_DETAILS_SUMMARY}\n\n`{transcript_path}`\n\n</details>\n"


def _get_sessions_base() -> Path:
    """Return the base directory for session transcript storage.

    Uses ``get_sessions_repo()`` from ``lib.paths`` when available, falling
    back to ``$AOPS_SESSIONS`` or ``$POLECAT_HOME/sessions``.
    """
    try:
        from lib.paths import get_sessions_repo

        return get_sessions_repo()
    except ImportError:
        aops_sessions = os.environ.get("AOPS_SESSIONS")
        if aops_sessions:
            return Path(aops_sessions)
        return Path(os.environ.get("POLECAT_HOME", str(Path.home() / ".polecat"))) / "sessions"


def _detect_system_timezone() -> str:
    """Detect system timezone from /etc/localtime or /etc/timezone. Returns 'UTC' if undetectable."""
    try:
        tz_link = Path("/etc/localtime")
        if tz_link.is_symlink():
            target = str(tz_link.resolve())
            # /etc/localtime -> /usr/share/zoneinfo/Region/City
            marker = "/zoneinfo/"
            idx = target.find(marker)
            if idx != -1:
                return target[idx + len(marker) :]
    except OSError:
        pass
    try:
        tz_file = Path("/etc/timezone")
        if tz_file.exists():
            return tz_file.read_text().strip()
    except OSError:
        pass
    return "UTC"


_DIND_MOUNTS: list[dict[str, str]] | None = None


def _container_to_host_path(container_path: Path) -> Path:
    """Resolve a container path to its host-visible path for Docker bind mounts.

    In Docker-in-Docker (DinD) environments where the Docker socket is shared
    with the host, bind-mount paths must be host-visible paths.  This function
    uses ``docker inspect`` on the current container to get the actual
    Source (host) / Destination (container) mount mappings, then finds the
    longest-matching Destination prefix and replaces it with Source.

    Results are cached — mount mappings don't change during a process lifetime.

    Returns the original path unchanged in non-DinD environments or when
    docker inspect fails.
    """
    global _DIND_MOUNTS  # noqa: PLW0603

    # Lazy-load mount mappings on first call
    if _DIND_MOUNTS is None:
        _DIND_MOUNTS = []
        if Path("/.dockerenv").exists():
            try:
                import socket
                import subprocess as _sp

                result = _sp.run(
                    [
                        "docker",
                        "inspect",
                        socket.gethostname(),
                        "--format",
                        "{{json .Mounts}}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    mounts = json.loads(result.stdout.strip())
                    # Sort by Destination length descending for longest-prefix matching
                    _DIND_MOUNTS = sorted(
                        [m for m in mounts if m.get("Destination") and m.get("Source")],
                        key=lambda m: len(m["Destination"]),
                        reverse=True,
                    )
            except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
                pass

    if not _DIND_MOUNTS:
        return container_path

    path_str = str(container_path.resolve())
    for mount in _DIND_MOUNTS:
        dest = mount["Destination"]
        if path_str == dest or path_str.startswith(dest + "/"):
            rel = path_str[len(dest) :]
            return Path(mount["Source"] + rel)

    return container_path


class DockerCmd(NamedTuple):
    """Result of _build_docker_cmd: the command to run and an optional staging dir.

    When staging_dir is set, callers must use _run_docker_container() instead of
    a plain subprocess.run() — it injects the staging files via ``docker cp``
    which works on all platforms (bind mounts fail on WSL2/Docker Desktop).
    """

    cmd: list[str]
    staging_dir: Path | None
    workspace_dir: Path | None = None


class DockerSock(NamedTuple):
    """Docker socket paths for mounting into containers.

    mount_source: path to use in the ``-v`` argument (VM-internal for Colima).
    host_path: path on the macOS/Linux host for ``stat()`` (GID discovery).
               May equal *mount_source* on Linux / Docker Desktop.
    """

    mount_source: Path
    host_path: Path


# macOS/Linux locations where the docker binary may live outside the user's
# interactive PATH. Probed in order as a last-resort fallback when neither the
# subprocess env nor os.environ surface "docker" — for example, a `pc` launched
# from a context (launchd, cron, headless ssh) whose PATH never sourced the
# user's shell rc files. See task-1929bf59 / task-dff66ab3.
_DOCKER_BINARY_FALLBACK_PATHS: tuple[str, ...] = (
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
    "/usr/bin/docker",
)


def _resolve_docker_binary(env: dict | None = None) -> str:
    """Return an absolute path to the ``docker`` binary, or ``"docker"`` as a
    last resort.

    Lookup order (first hit wins):
      1. ``env["PATH"]`` (when ``env`` is provided) — matches what
         ``subprocess.run(..., env=env)`` will use for executable resolution
         on POSIX (``os.get_exec_path(env)``).
      2. ``os.environ["PATH"]`` — the parent process's PATH; covers cases
         where the worker env was sanitised but the parent shell still has
         docker on PATH.
      3. ``_DOCKER_BINARY_FALLBACK_PATHS`` — common install locations on
         macOS/Linux. Closes the regression where ``pc run`` failed with
         ``'claude' command not found`` (actually ``docker``) on hosts where
         docker is at ``/usr/local/bin/docker`` but the subprocess env's
         PATH didn't contain it.

    Returns the literal ``"docker"`` if no resolution works — the caller will
    fail with a clear FileNotFoundError naming the missing binary.
    """
    if env is not None:
        resolved = shutil.which("docker", path=env.get("PATH"))
        if resolved:
            return resolved
    resolved = shutil.which("docker")
    if resolved:
        return resolved
    for candidate in _DOCKER_BINARY_FALLBACK_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "docker"


@functools.lru_cache(maxsize=1)
def _docker_daemon_host() -> str:
    """Return the docker daemon endpoint URL (cached for the process lifetime).

    Used by `_is_remote_daemon()` to choose between the local bind-mount
    container strategy and the remote docker-cp strategy.
    """
    # 1. Honour explicit DOCKER_HOST.
    explicit = os.environ.get("DOCKER_HOST")
    if explicit:
        return explicit
    # 2. Otherwise ask the docker CLI which context is active.
    try:
        result = subprocess.run(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Cannot determine Docker daemon host: `docker` CLI not found. "
            "Set DOCKER_HOST explicitly or ensure `docker` is on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Cannot determine Docker daemon host: `docker context inspect` timed out. "
            "Set DOCKER_HOST explicitly."
        ) from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(
            f"Cannot determine Docker daemon host: `docker context inspect` exited "
            f"{result.returncode}. Set DOCKER_HOST explicitly. "
            f"stderr: {result.stderr.strip()!r}"
        )
    return result.stdout.strip()


def _is_remote_daemon() -> bool:
    """True when the docker daemon is not on the local host filesystem.

    Local daemons (`unix://...`) can serve bind mounts directly. Remote
    daemons (`ssh://`, `tcp://`, `npipe://`) cannot — paths in `-v` flags
    resolve daemon-side, where the host worktree usually doesn't exist.

    Override with `POLECAT_FORCE_STAGING=cp` (force remote/cp path) or
    `POLECAT_FORCE_STAGING=bind` (force local/bind-mount path).
    """
    override = os.environ.get("POLECAT_FORCE_STAGING")
    if override == "cp":
        return True
    if override == "bind":
        return False
    return not _docker_daemon_host().startswith("unix://")


def _find_docker_sock(env: dict, home: Path | None = None) -> DockerSock | None:
    """Return Docker socket paths to mount, or None if unavailable.

    Discovery order:
    1. DOCKER_HOST in *env* dict or os.environ (env dict takes precedence).
       - If set to a ``unix://`` socket that exists on disk → use it.
       - If set to any other scheme (e.g. ``tcp://``) → return None; the
         daemon is remote so mounting a local socket would be wrong.
    2. ~/.colima/default/docker.sock  (Colima on macOS, default profile)
    3. ~/.colima/docker.sock          (Colima legacy path)
    4. /var/run/docker.sock           (standard Linux / Docker Desktop)

    **Colima quirk:** Colima's file-sharing layer (virtiofs / 9p) cannot
    bind-mount Unix sockets from the macOS host into containers.  The Docker
    daemon inside the Colima VM already exposes its socket at
    ``/var/run/docker.sock``, so we use that VM-internal path as the mount
    source while keeping the host path for ``stat()`` (GID discovery).

    ``home`` is injectable for testing; defaults to ``Path.home()``.  When
    ``home`` is explicitly provided the absolute system path
    ``/var/run/docker.sock`` is excluded from probing so tests remain
    isolated from the host environment.
    """
    _home = home if home is not None else Path.home()

    def _is_colima(p: Path) -> bool:
        return ".colima" in p.parts

    docker_host = env.get("DOCKER_HOST") or os.environ.get("DOCKER_HOST", "")
    if docker_host:
        if docker_host.startswith("unix://"):
            candidate = Path(docker_host.removeprefix("unix://"))
            if not candidate.exists():
                return None
            if _is_colima(candidate):
                return DockerSock(Path("/var/run/docker.sock"), candidate)
            return DockerSock(candidate, candidate)
        # Non-unix scheme (tcp://, etc.) — remote daemon, skip local mount.
        return None
    candidates: list[Path] = [
        _home / ".colima" / "default" / "docker.sock",
        _home / ".colima" / "docker.sock",
    ]
    if home is None:
        # Only probe the absolute system path in production; tests pass home
        # explicitly so they don't accidentally pick up a real host socket.
        candidates.append(Path("/var/run/docker.sock"))
    for candidate in candidates:
        if candidate.exists():
            if _is_colima(candidate):
                return DockerSock(Path("/var/run/docker.sock"), candidate)
            return DockerSock(candidate, candidate)
    return None


# ---------------------------------------------------------------------------
# Docker memory helpers
# ---------------------------------------------------------------------------

_DOCKER_LOW_MEMORY_THRESHOLD_GB = 3.0
_DOCKER_MEMORY_LIMIT_WARN_RATIO = 0.8


def _get_docker_daemon_memory() -> int | None:
    """Return Docker daemon total memory in bytes, or None if unavailable."""
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.MemTotal}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def _is_colima_env(env: dict) -> bool:
    """Check if the current Docker environment is Colima."""
    sock = _find_docker_sock(env)
    if sock is None:
        return False
    return ".colima" in str(sock.host_path)


def _format_watchdog_terminated_message(task_id: str | None = None) -> str:
    """Format the message printed when polecat's own watchdog killed the container.

    The PKB termination watchdog (`_pkb_termination_watchdog`) fires SIGKILL
    after the task reaches a terminal status (done / merge_ready / blocked /
    cancelled) and the agent fails to exit within the grace + SIGTERM window.
    Clean termination — distinct from OOM — must not show OOM remediation
    (that sent users chasing memory ghosts).
    """
    target = f"task {task_id}" if task_id else "the task"
    return (
        "\n"
        f"\u2713  Container terminated by polecat watchdog: {target} "
        "reached a terminal status and the agent did not exit on its own.\n"
        "    (exit 137 = SIGKILL from polecat, NOT out-of-memory.)\n"
    )


def _format_oom_message(env: dict, daemon_mem_bytes: int | None = None) -> str:
    """Format a SIGKILL diagnostic message with OOM as the leading hypothesis.

    Exit 137 = SIGKILL. The watchdog path is checked separately by the caller;
    if we reach this message, polecat did not initiate the kill, so the
    suspect list is OOM killer, manual `docker kill`, or a system signal. OOM
    is the most common cause when no human pressed anything — but we tell the
    user how to confirm it rather than asserting it.
    """
    lines = [
        "",
        "\u274c  Container killed by SIGKILL — exit code 137",
        "    Most likely cause: Out-Of-Memory (OOM) killer.",
        "    Confirm with: docker inspect <container> --format '{{.State.OOMKilled}}'",
        "    or check kernel logs: dmesg | grep -i 'killed process'",
        "",
    ]
    if daemon_mem_bytes is not None:
        mem_gb = daemon_mem_bytes / (1024**3)
        lines.append(f"   Docker daemon has {mem_gb:.1f} GB memory available.")

    if _is_colima_env(env):
        lines.extend(
            [
                "",
                "   Remediation (Colima):",
                "     colima stop && colima start --memory 8 --cpu 4",
            ]
        )
    elif sys.platform == "darwin":
        lines.extend(
            [
                "",
                "   Remediation (Docker Desktop):",
                "     Increase memory in Docker Desktop > Settings > Resources > Memory",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "   Remediation (Linux):",
                "     Check available memory with 'free -h'. Close other applications",
                "     or increase system swap.",
            ]
        )

    lines.extend(
        [
            "",
            "   You can also set a container memory limit to fail predictably:",
            "     POLECAT_DOCKER_MEMORY=6g polecat crew <project>",
            "     polecat crew --memory 6g <project>",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_memory_limit(cli_flag: str | None) -> str | None:
    """Resolve container memory limit from CLI flag or env var.

    Priority: CLI flag > POLECAT_DOCKER_MEMORY env var > None.
    """
    if cli_flag:
        return cli_flag
    return os.environ.get("POLECAT_DOCKER_MEMORY")


def _warn_low_docker_memory(
    memory_limit: str | None,
    env: dict,
    daemon_mem_bytes: int | None = None,
) -> None:
    """Print a warning if Docker daemon memory is too low."""
    if daemon_mem_bytes is None:
        daemon_mem_bytes = _get_docker_daemon_memory()
    if daemon_mem_bytes is None:
        return  # can't determine — skip warning

    mem_gb = daemon_mem_bytes / (1024**3)

    if mem_gb < _DOCKER_LOW_MEMORY_THRESHOLD_GB:
        print(
            f"\u26a0\ufe0f  Warning: Docker daemon has only {mem_gb:.1f} GB memory. "
            "Crew sessions typically need 4-6 GB.",
            file=sys.stderr,
        )
        if _is_colima_env(env):
            print(
                "   Increase with: colima stop && colima start --memory 8",
                file=sys.stderr,
            )
        elif sys.platform == "darwin":
            print(
                "   Increase in Docker Desktop > Settings > Resources > Memory",
                file=sys.stderr,
            )

    if memory_limit:
        # Parse memory limit to bytes for comparison
        limit_bytes = _parse_memory_string(memory_limit)
        if limit_bytes and limit_bytes > daemon_mem_bytes * _DOCKER_MEMORY_LIMIT_WARN_RATIO:
            print(
                f"\u26a0\ufe0f  Warning: Memory limit ({memory_limit}) exceeds 80% of "
                f"Docker daemon memory ({mem_gb:.1f} GB).",
                file=sys.stderr,
            )


def _parse_memory_string(mem_str: str) -> int | None:
    """Parse Docker memory string (e.g. '4g', '2048m', '1073741824') to bytes."""
    mem_str = mem_str.strip().lower()
    try:
        if mem_str.endswith("g"):
            return int(float(mem_str[:-1]) * 1024**3)
        elif mem_str.endswith("m"):
            return int(float(mem_str[:-1]) * 1024**2)
        elif mem_str.endswith("k"):
            return int(float(mem_str[:-1]) * 1024)
        elif mem_str.endswith("b"):
            return int(float(mem_str[:-1]))
        else:
            return int(mem_str)
    except ValueError:
        return None


def _init_container_memory(
    memory: str | None,
    manager,
    env: dict,
) -> tuple[str | None, int | None]:
    """Resolve container memory limit and emit daemon-memory warnings.

    Returns (memory_limit, daemon_mem_bytes) for use in OOM reporting.
    """
    memory_limit = _resolve_memory_limit(memory)
    daemon_mem = _get_docker_daemon_memory()
    _warn_low_docker_memory(memory_limit, env, daemon_mem)
    return memory_limit, daemon_mem


def _build_docker_cmd(
    cli_tool: str,
    work_dir: Path,
    env: dict,
    agent_cmd: list[str],
    is_interactive: bool,
    *,
    cfg: PolecatConfig | None = None,
    hooks_enabled: bool | None = None,
    tmp_files: list[Path] | None = None,
    session_dir: Path | None = None,
    session_volume: str | None = None,
    memory_limit: str | None = None,
    project_slug: str | None = None,
    manager: PolecatManager | None = None,
) -> DockerCmd:
    """Build a Docker command with appropriate mounts and env for an agent session.

    Returns a DockerCmd with the command args and an optional staging_dir.  When
    staging_dir is set, callers MUST use _run_docker_container() which injects
    files via ``docker cp`` (portable across WSL2, Colima, native Docker).

    If tmp_files is provided, any temporary files created (e.g. modified .claude.json)
    are appended to it so callers can clean them up.

    If session_volume is provided and cli_tool is "claude" or "shell", uses it as a
    Docker named volume at /home/worker/.claude/projects. Preferred in DinD environments
    where bind-mounted paths may not be host-visible.

    If memory_limit is provided (e.g. "4g", "2048m"), sets ``--memory`` and
    ``--memory-swap`` on the container to prevent silent OOM kills.

    If session_dir is provided (and session_volume is not), mounts it as a bind mount at
    /home/worker/.claude/projects so Claude session transcripts persist on the host.
    """
    # Container image — sourced from polecat.yaml (no env-var override).
    # ``cfg`` and ``hooks_enabled`` default to the loaded config's session
    # defaults; production callers always pass both. Defaulting is for tests
    # that exercise pure docker-arg construction without crew/run handlers.
    if cfg is None:
        cfg = load_polecat_config()
    if hooks_enabled is None:
        hooks_enabled = cfg.session_defaults.hooks_enabled
    image = cfg.docker.image

    # Resolve docker to an absolute path up front so the eventual
    # ``subprocess.run(..., env=env)`` cannot fail with FileNotFoundError when
    # the worker env's PATH happens not to contain it (regression of
    # task-dff66ab3 — see _resolve_docker_binary docstring).
    cmd = [_resolve_docker_binary(env), "run", "--rm"]
    _staging_dir: Path | None = None  # set below if auth files are staged

    # TTY allocation — flags must be separate elements so _run_docker_container
    # can detect "-i" when building the "docker start" command.
    cmd.append("-i")
    if is_interactive:
        cmd.append("-t")

    # Container memory limit — prevents silent OOM kills.
    # Setting --memory-swap equal to --memory disables swap so the OOM kill
    # fires at the configured limit with a clean exit code 137.
    if memory_limit:
        cmd.extend(["--memory", memory_limit])
        cmd.extend(["--memory-swap", memory_limit])

    # Run as current user — Claude Code refuses --dangerously-skip-permissions under root
    uid = os.getuid()
    gid = os.getgid()
    cmd.extend(["--user", f"{uid}:{gid}"])
    # Use /home/worker as container home — NOT --tmpfs on $HOME.
    # Docker --tmpfs mounts override bind mounts at the same path, hiding
    # .claude/ and .claude.json and causing Claude to hang on startup.
    container_home = "/home/worker"
    # HOME is set in the image ENV; no need to pass it at runtime

    # Timezone — match host timezone for consistent timestamps in commits/logs
    tz = os.environ.get("TZ") or _detect_system_timezone()
    cmd.extend(["-e", f"TZ={tz}"])

    # Git identity, credentials, terminal capability, and other env forwards
    # are conf-driven via lib.agent_env.get_container_env_forwards (see step
    # below). agent-env-map.conf is the single source of truth.

    # Workspace directory.
    # Local daemon: bind-mount host worktree → /workspace (rw, agent must commit).
    # Remote daemon: injected via docker cp in _run_docker_container() because
    # bind mounts resolve daemon-side and the host worktree isn't there.
    workspace_dir = work_dir.resolve()
    cmd.extend(["-w", "/workspace"])
    if not _is_remote_daemon():
        cmd.extend(["-v", f"{workspace_dir}:/workspace"])

    # Mount authentication and plugin cache for Claude/Gemini.
    # Also mount for "shell" mode so users can run either CLI interactively.
    home = Path.home()
    staging_dir: Path | None = None
    if cli_tool in ("claude", "shell", "gemini"):
        # Create a staging directory for auth files. Bind-mounted (ro) into
        # /tmp/staging on local daemons; injected via docker cp on remote ones.
        tmp_root = home / ".aops" / "tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(tempfile.mkdtemp(prefix="staging-", dir=tmp_root))
        os.chmod(staging_dir, 0o700)
        if tmp_files is not None:
            tmp_files.append(staging_dir)
        _staging_dir = staging_dir
        if not _is_remote_daemon():
            cmd.extend(["-v", f"{staging_dir}:/tmp/staging:ro"])

    if cli_tool in ("claude", "shell"):
        assert (
            staging_dir is not None
        )  # always set: ("claude","shell") ⊆ ("claude","shell","gemini")
        claude_dir = home / ".claude"
        # Stage a fixed .claude.json template rather than reading & merging the
        # host's. Three flags are needed for fully headless operation inside
        # Docker:
        #   bypassPermissionsModeAccepted — skips the --dangerously-skip-permissions prompt.
        #   hasTrustDialogAccepted — suppresses "Skipping project agents due to untrusted
        #     folder" so CLAUDE.md and framework hooks are loaded from /workspace.
        #   hasCompletedProjectOnboarding — suppresses the first-run onboarding wizard
        #     that would otherwise block a headless session on new projects.
        # Template lives in polecat/defaults/claude-headless.json — that is the
        # single source of truth for the staged file's contents.
        headless_template = SCRIPT_DIR / "defaults" / "claude-headless.json"
        if not headless_template.exists():
            raise RuntimeError(f"Missing bundled template: {headless_template}")
        staged_claude_json = staging_dir / ".claude.json"
        # Interactive `claude` (crew) consults .claude.json on launch and runs
        # the onboarding wizard unless `oauthAccount` is present — the staged
        # `.credentials.json` alone is not enough. Merge the host's account
        # record into the template so crew workers boot authenticated. Non-
        # interactive `polecat run` uses `-p` (print mode) which bypasses
        # onboarding entirely, but interactive crew has no such escape hatch.
        # (oauthAccount is PII — email, org UUID — so it cannot live in the
        # bundled template.) See issue #938.
        host_claude_json = home / ".claude.json"
        with open(headless_template) as f:
            staged_data = json.load(f)
        if host_claude_json.exists():
            try:
                with open(host_claude_json) as f:
                    host_data = json.load(f)
                if "oauthAccount" in host_data:
                    staged_data["oauthAccount"] = host_data["oauthAccount"]
            except (OSError, json.JSONDecodeError):
                # Host .claude.json missing/corrupt — proceed without merge;
                # worker will hit the OAuth wall and the user will see why.
                pass
        with open(staged_claude_json, "w") as f:
            json.dump(staged_data, f)
        os.chmod(staged_claude_json, 0o600)
        if claude_dir.exists():
            # Copy only the auth files Claude needs at runtime — not the whole directory.
            # The plugin installation is baked into the image (see Dockerfile), so mounting
            # the full ~/.claude dir would override the image's plugin data with the host's
            # (potentially stale or wrong-path) copy.
            #
            # Pick up the host's settings.json (autoMode rules, status line).
            staged_claude_dir = staging_dir / ".claude"
            staged_claude_dir.mkdir(exist_ok=True)
            for auth_file in (".credentials.json", "settings.json"):
                src = claude_dir / auth_file
                if src.exists():
                    shutil.copy2(src, staged_claude_dir / auth_file)
        # Stage Gemini auth files for "shell" mode so users can run gemini interactively.
        # Gemini normally handles its own sandbox, but in shell mode we're managing Docker.
        if cli_tool == "shell":
            gemini_dir = home / ".gemini"
            if gemini_dir.exists():
                staged_gemini_dir = staging_dir / ".gemini"
                staged_gemini_dir.mkdir(exist_ok=True)
                for auth_file in (
                    "settings.json",
                    "google_accounts.json",
                    "oauth_creds.json",
                    "installation_id",
                ):
                    src = gemini_dir / auth_file
                    if src.exists():
                        shutil.copy2(src, staged_gemini_dir / auth_file)
                # Also forward GEMINI_API_KEY if set
                gemini_key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
                if gemini_key:
                    cmd.extend(["-e", f"GEMINI_API_KEY={gemini_key}"])

    # Mount Docker socket for Docker-outside-of-Docker (build/test inside agents).
    # Pass the socket's gid so the non-root container user can access it — the gid
    # varies by host so we read it from the socket file rather than hardcoding.
    # For Colima the mount_source is the VM-internal path (/var/run/docker.sock)
    # which differs from the host_path used for stat().
    docker_sock = _find_docker_sock(env)
    if docker_sock is not None:
        # host_path is stattable on the host; mount_source may be VM-internal.
        try:
            docker_gid = docker_sock.host_path.stat().st_gid
            cmd.extend(["--group-add", str(docker_gid)])
        except OSError:
            pass
        cmd.extend(["-v", f"{docker_sock.mount_source}:/var/run/docker.sock"])

    # Add host networking for MCPs running on localhost
    cmd.extend(["--add-host", "host.docker.internal:host-gateway"])

    # Conf-driven env forwarding (agent-env-map.conf is the SSoT).
    # Covers: git identity literals, PKB_MCP_URL/PKB_MCP_TOKEN, GH/GITHUB
    # bot tokens, Anthropic & Gemini auth, terminal capability, runtime
    # config, GIT_ASKPASS=true, SSH_AUTH_SOCK="" / GIT_SSH_COMMAND=false /
    # GIT_TERMINAL_PROMPT=0 isolation literals.
    # Empty source values are skipped (closes the empty-credential 401 leak).
    conf_forwards = get_container_env_forwards(env)
    for key, val in conf_forwards.items():
        cmd.extend(["-e", f"{key}={val}"])

    # Project-specific mounts and env (from polecat.yaml mounts: block).
    if project_slug and manager:
        try:
            _canonical_slug = manager.resolve_project_alias(project_slug)
        except ValueError:
            _canonical_slug = project_slug
        _project_entry = manager.projects.get(_canonical_slug)
        if _project_entry:
            for mount in _project_entry.get("mounts") or []:
                if not isinstance(mount, dict):
                    continue
                host_raw = mount.get("host")
                container_path = mount.get("container")
                if not host_raw or not container_path:
                    continue

                mode = mount.get("mode", "ro")
                # Expand ~ and env vars; resolve relative paths against polecat.yaml location
                _host_raw_path = Path(os.path.expandvars(os.path.expanduser(str(host_raw))))
                if not _host_raw_path.is_absolute() and cfg and getattr(cfg, "source_path", None):
                    host_path = (cfg.source_path.parent / _host_raw_path).resolve()
                else:
                    host_path = _host_raw_path.resolve()

                if host_path.exists():
                    cmd.extend(["-v", f"{host_path}:{container_path}:{mode}"])

                    # Auto-set credentials env vars if matching files are found
                    if (host_path / "sa.json").exists():
                        cmd.extend(
                            ["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_path}/sa.json"]
                        )
                    if (host_path / "profiles.yml").exists():
                        cmd.extend(["-e", f"DBT_PROFILES_DIR={container_path}/"])

    # Pattern-arm forwarding — POLECAT_* and AOPS_* (excluding the resolved
    # config-path env: that is set explicitly below to point at the in-container
    # staged polecat.yaml). Gate-mode env vars no longer exist; gate modes are
    # resolved from polecat.yaml inside the container.
    for key, val in env.items():
        if not val or key in conf_forwards:
            continue
        if key == CONFIG_PATH_ENV:
            continue
        if key.startswith("POLECAT_") or key.startswith("AOPS_"):
            cmd.extend(["-e", f"{key}={val}"])

    # Session storage: transcripts persist beyond container lifetime.
    # Local daemon → bind-mount session_dir for live host visibility.
    # Remote daemon → mkdir only; callers extract via docker cp after run.
    # session_volume (named volume) is the DinD path and overrides both.
    if cli_tool in ("claude", "shell", "gemini"):
        # Determine the project-specific subdirectory name.
        # Inside the container, we chdir to /workspace.
        # Claude uses -workspace (sanitized /workspace), Gemini uses workspace.
        if cli_tool in ("claude", "shell"):
            session_container_path = f"{container_home}/.claude/projects/-workspace"
        else:
            session_container_path = f"{container_home}/.gemini/tmp/workspace"

        # Set AOPS_SESSION_STATE_DIR so hooks write to the same directory.
        # This ensures hooks.jsonl and state JSON land in the host session_dir.
        cmd.extend(["-e", f"AOPS_SESSION_STATE_DIR={session_container_path}"])

        if session_volume:
            # For volumes, we still mount to the parent so multiple projects can coexist if needed
            vol_target = (
                f"{container_home}/.claude/projects"
                if cli_tool in ("claude", "shell")
                else f"{container_home}/.gemini/tmp"
            )
            cmd.extend(["-v", f"{session_volume}:{vol_target}"])
        elif session_dir:
            session_dir.mkdir(parents=True, exist_ok=True)
            if not _is_remote_daemon():
                cmd.extend(["-v", f"{session_dir}:{session_container_path}"])

    # Stage polecat.yaml into the container so hooks resolve gate modes,
    # provider lists, and any other config without re-reading host paths.
    # The host config is the SSoT — the staged file is a copy.
    staged_aops_dir = staging_dir / ".aops" if staging_dir else None
    if staged_aops_dir is not None:
        staged_aops_dir.mkdir(exist_ok=True)
        shutil.copy2(cfg.source_path, staged_aops_dir / "polecat.yaml")
    cmd.extend(["-e", f"{CONFIG_PATH_ENV}={_CONTAINER_POLECAT_YAML}"])

    cmd.append(image)
    cmd.extend(agent_cmd)
    return DockerCmd(cmd=cmd, staging_dir=_staging_dir, workspace_dir=workspace_dir)


def _pkb_termination_watchdog(
    container_id: str,
    task_id: str,
    cancel_event: threading.Event,
    fired_event: threading.Event | None = None,
    bypass: bool = False,
) -> None:
    """Poll PKB for task terminal status; kill the container when reached.

    Issue #521 fix: Gemini CLI has no Stop hook, so polecat must detect
    task completion externally. Polls PKB every
    ``TERMINATION_POLL_INTERVAL_SECONDS`` via ``polecat.pkb_bridge.get_task``.
    When the task reaches a terminal status (done / merge_ready / blocked /
    cancelled) the watchdog waits ``POLECAT_TERMINATION_GRACE_SECONDS``
    (default 60), sends SIGTERM to the container, then SIGKILL after
    ``TERMINATION_SIGKILL_DELAY_SECONDS`` more.

    ``cancel_event`` is set by the main thread when the CLI exits cleanly
    on its own; the watchdog then returns without killing anything.

    If ``bypass`` is True (interactive or crew sessions), the watchdog logs
    the terminal status but does NOT kill the container, as a user is
    likely present.
    """
    try:
        from polecat.pkb_bridge import get_task as pkb_get_task
    except Exception as exc:  # pragma: no cover — defensive
        print(
            f"   [termination watchdog] unable to import pkb_bridge: {exc}",
            file=sys.stderr,
        )
        return

    _grace_env = os.environ.get("POLECAT_TERMINATION_GRACE_SECONDS")
    if _grace_env is not None:
        try:
            grace_seconds = int(_grace_env)
        except ValueError:
            print(
                f"   [termination watchdog] POLECAT_TERMINATION_GRACE_SECONDS={_grace_env!r} "
                f"is not a valid integer — failing fast (P#8). Aborting watchdog.",
                file=sys.stderr,
            )
            return
    else:
        grace_seconds = DEFAULT_TERMINATION_GRACE_SECONDS

    while not cancel_event.is_set():
        try:
            task = pkb_get_task(task_id)
        except Exception as exc:  # pragma: no cover — network/transient
            print(
                f"   [termination watchdog] PKB poll failed for {task_id}: {exc}",
                file=sys.stderr,
            )
            task = None

        status = getattr(task, "status", None) if task is not None else None
        if status in TERMINAL_PKB_STATUSES:
            if bypass:
                print(
                    f"   [termination watchdog] task {task_id} status={status!r}; "
                    f"BYPASS: interactive/crew session — watchdog will NOT kill container.",
                    file=sys.stderr,
                )
                metrics.record_watchdog_event(task_id, "bypass", status=status)
                return

            print(
                f"   [termination watchdog] task {task_id} status={status!r}; "
                f"grace={grace_seconds}s before SIGTERM",
                file=sys.stderr,
            )
            metrics.record_watchdog_event(
                task_id, "waiting", status=status, grace_seconds=grace_seconds
            )

            # Grace period — respect cancellation so a natural exit wins.
            if cancel_event.wait(timeout=grace_seconds):
                metrics.record_watchdog_event(task_id, "natural_exit", status=status)
                return

            # Mark that the watchdog (not OOM, not user) is the cause of any
            # subsequent SIGKILL exit. Caller checks this to format the right
            # exit message — see `_format_watchdog_terminated_message`.
            if fired_event is not None:
                fired_event.set()

            metrics.record_watchdog_event(
                task_id, "timeout", status=status, grace_seconds=grace_seconds
            )
            try:
                subprocess.run(
                    ["docker", "kill", "--signal=TERM", container_id],
                    capture_output=True,
                    check=False,
                )
            except Exception as exc:  # pragma: no cover — docker transient
                print(
                    f"   [termination watchdog] docker kill TERM failed: {exc}",
                    file=sys.stderr,
                )
            if cancel_event.wait(timeout=TERMINATION_SIGKILL_DELAY_SECONDS):
                return
            try:
                subprocess.run(
                    ["docker", "kill", "--signal=KILL", container_id],
                    capture_output=True,
                    check=False,
                )
            except Exception as exc:  # pragma: no cover — docker transient
                print(
                    f"   [termination watchdog] docker kill KILL failed: {exc}",
                    file=sys.stderr,
                )
            return

        if cancel_event.wait(timeout=TERMINATION_POLL_INTERVAL_SECONDS):
            return


def _run_docker_container(
    docker_cmd: DockerCmd,
    *,
    cwd: Path | None = None,
    env: dict | None = None,
    capture_output: bool = False,
    text: bool = True,
    extract_paths: list[tuple[str, Path]] | None = None,
    gemini: bool = False,
    task_id: str | None = None,
) -> subprocess.CompletedProcess:
    """Launch a Docker container.

    Local daemon: plain ``docker run`` — workspace/session/staging are bind
    mounts added by ``_build_docker_cmd``. A ``--name polecat-{nonce}`` flag
    lets the PKB watchdog target the container by name.

    Remote daemon (or ``POLECAT_FORCE_STAGING=cp``): bind mounts cannot reach
    a remote daemon's filesystem, so we fall back to ``docker create`` +
    ``docker cp`` (workspace, staging in; ``extract_paths`` out) +
    ``docker start -a``.
    """
    cmd = list(docker_cmd.cmd)  # copy to avoid mutation
    # Bypass watchdog kills for interactive or crew sessions (user present)
    _is_crew = env.get("POLECAT_SESSION_TYPE") == "crew" if env else False
    _is_interactive = any(arg in cmd for arg in ["-t", "--tty"])
    _bypass = _is_crew or _is_interactive

    if not _is_remote_daemon():
        # Local: bind mounts already in cmd. Add --name for watchdog targeting.
        container_name = f"polecat-{task_id or uuid.uuid4().hex[:8]}"
        cmd[3:3] = ["--name", container_name]

        _watchdog_cancel = None
        _watchdog_fired: threading.Event | None = None
        _watchdog_thread = None
        if gemini and task_id:
            _watchdog_cancel = threading.Event()
            _watchdog_fired = threading.Event()
            _watchdog_thread = threading.Thread(
                target=_pkb_termination_watchdog,
                args=(
                    container_name,
                    task_id,
                    _watchdog_cancel,
                    _watchdog_fired,
                    _bypass,
                ),
                name=f"polecat-watchdog-{task_id}",
                daemon=True,
            )
            _watchdog_thread.start()

        try:
            _result = subprocess.run(
                cmd, cwd=cwd, env=env, capture_output=capture_output, text=text
            )
            # Annotate so callers can distinguish polecat-initiated SIGKILL
            # from OOM / external SIGKILL when returncode == 137.
            _result.watchdog_terminated = bool(  # type: ignore[attr-defined]
                _watchdog_fired and _watchdog_fired.is_set()
            )
            return _result
        except KeyboardInterrupt:
            # SIGINT/SIGTERM reached us while docker run was blocking. Ask
            # docker to gracefully stop the container so the agent has time
            # to flush its session transcript before the host process exits
            # (task-11de7b21). Then re-raise so callers' `finally` blocks
            # (cleanup, extraction) execute.
            try:
                subprocess.run(
                    ["docker", "stop", "--time", "10", container_name],
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
            except Exception:  # pragma: no cover — best-effort cleanup
                pass
            raise
        finally:
            if _watchdog_cancel is not None:
                _watchdog_cancel.set()
            if _watchdog_thread is not None:
                _watchdog_thread.join(timeout=5.0)

    # Replace "docker run --rm" with "docker create" (no --rm, we clean up manually)
    # The cmd starts with ["docker", "run", "--rm", ...]
    create_cmd = ["docker", "create"] + cmd[3:]  # skip "docker", "run", "--rm"

    # Create the container (stopped)
    result = subprocess.run(create_cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"docker create failed: {result.stderr}", file=sys.stderr)
        return result
    container_id = result.stdout.strip()

    try:
        # Copy workspace into the container and fix ownership.
        # docker cp writes files as root, but the container runs as the host UID
        # (--user flag). We tar with --owner/--group to set the correct UID:GID
        # during injection so pre-commit hooks, uv, and git can write to /workspace.
        if docker_cmd.workspace_dir:
            user_spec = next(
                (cmd[i + 1] for i, x in enumerate(cmd) if x == "--user"),
                None,
            )
            if user_spec:
                uid_str, gid_str = (user_spec.split(":") + [user_spec])[:2]
                # tar with forced ownership | docker cp from stdin
                tar_cmd = [
                    "tar",
                    "-cf",
                    "-",
                ]
                if sys.platform == "darwin":
                    tar_cmd.extend(["--no-mac-metadata", "--no-xattrs"])
                tar_cmd.extend(
                    [
                        "--owner",
                        uid_str,
                        "--group",
                        gid_str,
                        "-C",
                        str(docker_cmd.workspace_dir),
                        ".",
                    ]
                )
                tar_proc = subprocess.Popen(
                    tar_cmd,
                    stdout=subprocess.PIPE,
                    cwd=cwd,
                )
                cp_result = subprocess.run(
                    ["docker", "cp", "-", f"{container_id}:/workspace"],
                    stdin=tar_proc.stdout,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=env,
                )
                assert tar_proc.stdout is not None
                tar_proc.stdout.close()
                tar_proc.wait()
                if tar_proc.returncode != 0:
                    print(
                        f"tar failed (exit {tar_proc.returncode}) archiving workspace",
                        file=sys.stderr,
                    )
                    if cp_result.returncode != 0:
                        print(f"docker cp (workspace) failed: {cp_result.stderr}", file=sys.stderr)
                    return subprocess.CompletedProcess(
                        args=tar_cmd, returncode=tar_proc.returncode, stdout="", stderr=""
                    )
            else:
                cp_result = subprocess.run(
                    ["docker", "cp", f"{docker_cmd.workspace_dir}/.", f"{container_id}:/workspace"],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=env,
                )
            if cp_result.returncode != 0:
                print(f"docker cp (workspace) failed: {cp_result.stderr}", file=sys.stderr)
                return cp_result

        # Copy staging files into the container
        if docker_cmd.staging_dir:
            cp_result = subprocess.run(
                ["docker", "cp", f"{docker_cmd.staging_dir}/.", f"{container_id}:/tmp/staging"],
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
            )
            if cp_result.returncode != 0:
                print(f"docker cp failed: {cp_result.stderr}", file=sys.stderr)
                return cp_result

        # Start the container and wait for it to finish
        start_cmd = ["docker", "start", "-a"]
        if any(x in cmd for x in ["-i", "--interactive", "-it"]):
            start_cmd.append("-i")
        start_cmd.append(container_id)

        # Issue #521: Gemini workers have no Stop hook, so polecat must
        # watch PKB for a terminal status and kill the container when
        # observed. Claude workers terminate via their own Stop hook —
        # leave that path unchanged.
        watchdog_cancel: threading.Event | None = None
        watchdog_fired: threading.Event | None = None
        watchdog_thread: threading.Thread | None = None
        if gemini and task_id:
            watchdog_cancel = threading.Event()
            watchdog_fired = threading.Event()
            watchdog_thread = threading.Thread(
                target=_pkb_termination_watchdog,
                args=(container_id, task_id, watchdog_cancel, watchdog_fired, _bypass),
                name=f"polecat-watchdog-{task_id}",
                daemon=True,
            )
            watchdog_thread.start()

        run_result = None
        try:
            try:
                run_result = subprocess.run(
                    start_cmd, cwd=cwd, env=env, capture_output=capture_output, text=text
                )
                # Annotate so callers can distinguish polecat-initiated SIGKILL
                # from OOM / external SIGKILL when returncode == 137.
                run_result.watchdog_terminated = bool(  # type: ignore[attr-defined]
                    watchdog_fired and watchdog_fired.is_set()
                )
            except KeyboardInterrupt:
                # SIGTERM/SIGINT reached us while docker start -a was blocking.
                # Ask docker to gracefully stop the container so the agent has
                # time to flush its session transcript before we extract it
                # (task-11de7b21).
                try:
                    subprocess.run(
                        ["docker", "stop", "--time", "10", container_id],
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                except Exception:  # pragma: no cover — best-effort cleanup
                    pass
                # Don't re-raise yet: let the extraction below run so the
                # transcript still lands on the host. Re-raise after.
                _interrupted = True
            else:
                _interrupted = False
        finally:
            if watchdog_cancel is not None:
                watchdog_cancel.set()
            if watchdog_thread is not None:
                watchdog_thread.join(timeout=5.0)

        # Extract files from container before cleanup (belt-and-suspenders
        # for session persistence — bind mounts silently fail on WSL2).
        # Runs even after SIGTERM-induced interrupt so the graceful-shutdown
        # path still produces a transcript on the host.
        if extract_paths:
            for container_path, host_path in extract_paths:
                host_path.mkdir(parents=True, exist_ok=True)
                cp_out = subprocess.run(
                    ["docker", "cp", f"{container_id}:{container_path}/.", str(host_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if cp_out.returncode != 0:
                    print(
                        f"   Session extract warning: {cp_out.stderr.strip()}",
                        file=sys.stderr,
                    )

        if _interrupted:
            raise KeyboardInterrupt
        assert run_result is not None  # set in try block; None path raises above
        return run_result
    finally:
        # Always clean up the container (replaces --rm)
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            check=False,
        )


def _pass_pkb_url_sandbox(env: dict) -> None:
    """Ensure PKB_MCP_URL is forwarded into the Gemini sandbox.

    PKB now connects over HTTP — no data volume mount needed.
    This helper is called from both ``crew -g`` and ``run -g``.
    """
    pkb_url = env.get("PKB_MCP_URL") or os.environ.get("PKB_MCP_URL")
    if pkb_url:
        env.setdefault("PKB_MCP_URL", pkb_url)


def _mount_gemini_git_credentials(env: dict, tmp_files: list[Path]) -> list[str]:
    """Mount .gitconfig and gh hosts.yml into Gemini sandbox for git push.

    File-based credentials are preferred over SANDBOX_FLAGS -e for two reasons:
    1. Security: env vars are visible in /proc/<pid>/environ and ``ps auxe``;
       mounted files are not leaked through process listings.
    2. Reliability: Gemini sandbox only forwards a hardcoded allowlist of env
       vars into the container. SANDBOX_FLAGS -e is kept as belt-and-suspenders
       but cannot be the primary mechanism.

    The token is embedded directly in the gitconfig so git does not need
    $GH_TOKEN to be present in the container environment at push time.

    Returns extra_flags (list of ``-e KEY=VALUE`` strings) to append to
    SANDBOX_FLAGS.
    """
    extra_flags: list[str] = []
    gh_token = env.get("GH_TOKEN") or os.environ.get("AOPS_BOT_GH_TOKEN")
    if not gh_token:
        return extra_flags

    extra_flags.extend(["-e", "GIT_ASKPASS=true"])
    extra_flags.extend(["-e", f"GH_TOKEN={gh_token}"])
    extra_flags.extend(["-e", f"GITHUB_TOKEN={gh_token}"])
    extra_flags.extend(["-e", "SSH_AUTH_SOCK="])
    extra_flags.extend(["-e", "GIT_SSH_COMMAND=false"])
    extra_flags.extend(["-e", "GIT_TERMINAL_PROMPT=0"])

    # .gitconfig with embedded credential helper
    gitconfig = tempfile.NamedTemporaryFile(
        suffix=".gitconfig", delete=False, mode="w", prefix="polecat-"
    )
    gitconfig.write(
        "[credential]\n"
        f'\thelper = !f() {{ echo username=x-access-token; echo "password={gh_token}"; }}; f\n'
        '[credential "https://github.com"]\n'
        f'\thelper = !f() {{ echo username=x-access-token; echo "password={gh_token}"; }}; f\n'
        '[url "https://github.com/"]\n'
        "\tinsteadOf = git@github.com:\n"
    )
    gitconfig.close()
    tmp_files.append(Path(gitconfig.name))

    container_gitconfig = str(Path.home() / ".gitconfig")
    mounts = env.get("SANDBOX_MOUNTS", "")
    new_mount = f"{gitconfig.name}:{container_gitconfig}:ro"
    env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

    # gh CLI hosts.yml — file-based auth fallback for `gh pr create`
    gh_hosts = tempfile.NamedTemporaryFile(
        suffix=".yml", delete=False, mode="w", prefix="polecat-gh-hosts-"
    )
    gh_hosts.write(f"github.com:\n    oauth_token: {gh_token}\n    git_protocol: https\n")
    gh_hosts.close()
    tmp_files.append(Path(gh_hosts.name))

    container_gh_hosts = str(Path.home() / ".config" / "gh" / "hosts.yml")
    mounts = env.get("SANDBOX_MOUNTS", "")
    new_mount = f"{gh_hosts.name}:{container_gh_hosts}:ro"
    env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

    return extra_flags


def _replicate_gemini_auth(
    env: dict, work_dir: Path | None = None, hooks_enabled: bool = True
) -> Path | None:
    """Replicate Gemini authentication files to a directory.

    For headless sessions to authenticate properly in a sandbox, critical files
    from the user's ~/.gemini/ directory must be replicated in the temporary
    GEMINI_CLI_HOME:
    - settings.json
    - google_accounts.json
    - oauth_creds.json
    - installation_id
    - trustedFolders.json

    If work_dir is provided, it is added to the replicated trustedFolders.json
    to avoid trust prompts in the sandbox.

    Returns:
        Path to the directory containing the replicated files,
        or None if authentication replication is disabled or fails.
    """
    if os.environ.get("POLECAT_GEMINI_AUTH_DISABLED") == "1":
        return None

    home = Path.home()
    gemini_dir = home / ".gemini"

    if not gemini_dir.exists():
        return None

    # Check if we have any auth-related files
    # gemini-credentials.json is intentionally excluded: it's encrypted with the
    # host's libsecret/keyring key, which isn't available inside the container,
    # so Gemini logs a "Corrupted credentials file" stack trace on every
    # dispatch. oauth_creds.json provides working OAuth auth on its own.
    auth_files = [
        "settings.json",
        "google_accounts.json",
        "oauth_creds.json",
        "installation_id",
        "trustedFolders.json",
        "projects.json",
        "state.json",
        "policies",
    ]

    existing_files = [f for f in auth_files if (gemini_dir / f).exists()]
    if not existing_files:
        return None

    # Create a temporary directory under $HOME/.aops/tmp so Docker can access it.
    # macOS VMs (Colima/Docker) only share /Users, not /var/folders or /tmp.
    tmp_root = home / ".aops" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_gemini_home = Path(tempfile.mkdtemp(prefix="polecat-gemini-auth-", dir=tmp_root))
    # Gemini's --sandbox mounts GEMINI_CLI_HOME into a Docker container that may
    # run as a different UID. The container needs to write temp files (e.g.
    # projects.json.tmp) inside .gemini/, so both the parent and the .gemini
    # subdir must be world-writable. This is a throwaway copy of auth files.
    os.chmod(tmp_gemini_home, 0o755)

    target_dir = tmp_gemini_home / ".gemini"
    target_dir.mkdir(parents=True)
    os.chmod(target_dir, 0o777)

    policies_dir = target_dir / "policies"
    policies_dir.mkdir(exist_ok=True)
    os.chmod(policies_dir, 0o777)

    for f in existing_files:
        if f == "policies":
            src_policies = gemini_dir / "policies"
            if src_policies.is_dir():
                for policy_file in src_policies.glob("*.toml"):
                    shutil.copy2(policy_file, policies_dir / policy_file.name)
            continue

        if f == "trustedFolders.json" and work_dir:
            try:
                with open(gemini_dir / f) as src_f:
                    trust_data = json.load(src_f)
                # Inject both the host work_dir and the in-container mount path.
                # Gemini matches trust against the running CWD: inside the polecat
                # Docker container that's /workspace, on the host it's work_dir.
                # Adding both covers either invocation without an extra parameter.
                trust_data[str(work_dir.resolve())] = "TRUST_FOLDER"
                trust_data["/workspace"] = "TRUST_FOLDER"
                # Pre-trust the aops-core extension dir — its path is identical
                # in every fresh worker. Without this, gemini prompts for trust
                # on the extension on every crew start, even though "remember"
                # is meaningless across ephemeral workers.
                trust_data["/home/worker/.gemini/extensions/aops-core"] = "TRUST_FOLDER"
                with open(target_dir / f, "w") as dest_f:
                    json.dump(trust_data, dest_f, indent=2)
                continue
            except (json.JSONDecodeError, OSError) as e:
                # Fall back to simple copy if processing fails
                print(f"   Warning: could not process {gemini_dir / f}: {e}", file=sys.stderr)

        if f == "settings.json":
            try:
                # Start from our controlled template, then set auth type based on
                # what credentials were actually replicated. Gemini CLI does NOT
                # auto-detect auth — it fails with "Please set an Auth method" if
                # selectedType is missing. We infer the type from available files:
                #   oauth_creds.json → "oauth-personal"
                #   GEMINI_API_KEY env → "api-key" (handled by env, no setting needed)
                template_path = SCRIPT_DIR / "defaults" / "gemini-settings.json"
                if not template_path.exists():
                    raise RuntimeError(f"Missing bundled template: {template_path}")
                with open(template_path) as tpl_f:
                    minimal = json.load(tpl_f)

                # Set auth type if OAuth credentials are being replicated
                if "oauth_creds.json" in existing_files:
                    minimal.setdefault("security", {}).setdefault("auth", {})["selectedType"] = (
                        "oauth-personal"
                    )

                with open(target_dir / f, "w") as dst_f:
                    json.dump(minimal, dst_f, indent=2)
                continue
            except (json.JSONDecodeError, OSError) as e:
                print(f"   Warning: could not process settings.json template: {e}", file=sys.stderr)
                continue

        # Follow symlinks to copy the actual file content, not the link itself.
        # This is critical for ~/.gemini/settings.json which is often symlinked.
        shutil.copy2(gemini_dir / f, target_dir / f, follow_symlinks=True)

    # Copy our default framework policies. Source from aops-core/policies/
    # (the single source of truth) rather than a duplicate under
    # polecat/defaults/ — the bundled copy got out of sync with gemini's
    # policy engine schema and silently disabled itself. See issue #940.
    deny_ext_src = SCRIPT_DIR.parent / "aops-core" / "policies" / "deny-extension-writes.toml"
    if not deny_ext_src.exists():
        raise RuntimeError(f"Missing framework policy file: {deny_ext_src}")
    shutil.copy2(deny_ext_src, policies_dir / "deny-extension-writes.toml")

    # If trustedFolders.json didn't exist but we have a work_dir, create it.
    # Cover both the host path and the in-container mount (/workspace) so the
    # trust prompt is suppressed regardless of where Gemini runs.
    if "trustedFolders.json" not in existing_files and work_dir:
        try:
            trust_data = {
                str(work_dir.resolve()): "TRUST_FOLDER",
                "/workspace": "TRUST_FOLDER",
                "/home/worker/.gemini/extensions/aops-core": "TRUST_FOLDER",
            }
            with open(target_dir / "trustedFolders.json", "w") as f:
                json.dump(trust_data, f, indent=2)
        except OSError as e:
            print(f"   Warning: could not create trustedFolders.json: {e}", file=sys.stderr)

    # Replicate extensions so that extension hooks fire in sandbox sessions.
    # Copy (not symlink) extension dirs because Gemini's sandbox mounts
    # GEMINI_CLI_HOME into a Docker container — symlinks to host paths
    # break since the target paths don't exist inside the container.
    # Create a fresh extension-enablement.json with a wildcard override so the
    # extension is active for any workspace path (the original restricts to
    # /home/<user>/* which won't match test or CI workspaces).
    src_extensions = gemini_dir / "extensions"
    if src_extensions.is_dir():
        dst_extensions = target_dir / "extensions"
        dst_extensions.mkdir(parents=True, exist_ok=True)

        # Copy each extension subdirectory (not symlink — breaks in Docker).
        # Exclude .venv — it contains symlinks to the host Python install
        # which break in Docker/temp dirs.  `uv run` in router.sh will
        # recreate a fresh venv from pyproject.toml on first hook invocation.
        def _ignore_venv(directory, contents):
            return [c for c in contents if c in (".venv", ".uv-cache")]

        for child in src_extensions.iterdir():
            if child.is_dir():
                shutil.copytree(
                    child,
                    dst_extensions / child.name,
                    ignore=_ignore_venv,
                    ignore_dangling_symlinks=True,
                )

        # Build a permissive enablement file — allow all paths
        enablement_src = src_extensions / "extension-enablement.json"
        if enablement_src.exists():
            try:
                with open(enablement_src) as f:
                    enablement = json.load(f)
                for ext_name in enablement:
                    enablement[ext_name]["overrides"] = ["*"]
                with open(dst_extensions / "extension-enablement.json", "w") as f:
                    json.dump(enablement, f, indent=2)
            except (json.JSONDecodeError, OSError):
                shutil.copy2(enablement_src, dst_extensions / "extension-enablement.json")

    # Replicate policies so that policy engine is active in sandbox sessions.
    src_policies = gemini_dir / "policies"
    if src_policies.is_dir():
        dst_policies = target_dir / "policies"
        dst_policies.mkdir(parents=True, exist_ok=True)
        for policy in src_policies.glob("*.toml"):
            shutil.copy2(policy, dst_policies / policy.name)

    # Copy bundled admin policies AFTER user policies so they always take
    # precedence — a same-named user file must not override an admin policy.
    compliance_src = SCRIPT_DIR / "defaults" / "compliance-agents.toml"
    if not compliance_src.exists():
        raise RuntimeError(f"Missing bundled policy file: {compliance_src}")
    shutil.copy2(compliance_src, policies_dir / "compliance-agents.toml")

    # Make all replicated files and directories writable by any UID.
    # Gemini's sandbox container may run as a different user than the host
    # and needs to write temp files (projects.json.tmp, settings updates).
    for dirpath, _dirnames, filenames in os.walk(target_dir):
        os.chmod(dirpath, 0o777)
        for fname in filenames:
            os.chmod(os.path.join(dirpath, fname), 0o666)

    # Set GEMINI_CLI_HOME to the parent directory — Gemini creates .gemini/
    # inside GEMINI_CLI_HOME (i.e. path.join(GEMINI_CLI_HOME, ".gemini", ...)).
    env["GEMINI_CLI_HOME"] = str(tmp_gemini_home)

    return tmp_gemini_home


def _extract_gemini_sessions(tmp_gemini_home: Path, session_dir: Path) -> None:
    """Copy Gemini session transcripts from tmp auth home to persistent session_dir.

    Gemini CLI writes sessions to ``$GEMINI_CLI_HOME/.gemini/tmp/<hash>/chats/session-*.json``
    where ``<hash>`` is a SHA256 of the working directory.  These files live inside
    the temporary auth home that gets deleted after each run.  This function
    extracts them to the persistent ``session_dir`` so they survive cleanup.
    """
    gemini_tmp = tmp_gemini_home / ".gemini" / "tmp"
    if not gemini_tmp.is_dir():
        return

    dest = session_dir / "chats"
    dest.mkdir(parents=True, exist_ok=True)

    for session_file in gemini_tmp.rglob("session-*.json"):
        target = dest / session_file.name
        if target.exists():
            # Avoid collision: prefix with parent hash dir name
            target = dest / f"{session_file.parent.parent.name}-{session_file.name}"
        shutil.copy2(session_file, target)


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty()


def _require_pkb_url_or_exit() -> None:
    """Emit a friendly one-liner and exit(4) if PKB_MCP_URL is unset.

    Runs before :func:`_bootstrap_or_exit` so the most common missing-env
    failure produces remediation guidance rather than a generic bootstrap
    banner (and certainly not the bare ``RuntimeError`` from
    ``pkb_bridge._get_client``).  Exit code 4 distinguishes config failures
    from bootstrap errors (1), locked tasks (2), and empty queues (3).
    """
    if os.environ.get("PKB_MCP_URL"):
        return
    print(
        "polecat: PKB_MCP_URL is not set.\n"
        "  Start the PKB MCP server and export its URL, e.g.:\n"
        "      export PKB_MCP_URL=http://localhost:8026/mcp",
        file=sys.stderr,
    )
    sys.exit(4)


def _bootstrap_or_exit() -> None:
    from polecat.bootstrap import BootstrapError, validate_bootstrap

    try:
        validate_bootstrap(aops_path=os.environ.get("AOPS"))
    except BootstrapError as e:
        print("\n❌ Bootstrap validation failed:", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        print("", file=sys.stderr)
        sys.exit(1)


@click.group()
@click.option(
    "--home",
    envvar="POLECAT_HOME",
    type=click.Path(path_type=Path),
    help="Polecat home directory (default: $POLECAT_HOME, or ~/.polecat)",
)
@click.pass_context
def main(ctx, home):
    """Polecat: Ephemeral worker management system."""
    ctx.ensure_object(dict)
    ctx.obj["home"] = home


@main.command()
@click.pass_context
def setup(ctx):
    """Run full framework installation and extension linking.

    This builds extensions and runs scripts/install.py to set up
    cron jobs, symlinks, and link Gemini/Claude extensions.
    Requires uv and should be run from the repository root.
    """
    repo_root = Path(__file__).parent.parent.resolve()
    setup_script = repo_root / "setup.sh"

    if not setup_script.exists():
        print(f"Error: setup.sh not found at {setup_script}", file=sys.stderr)
        sys.exit(1)

    print(f"Running framework setup from {setup_script}...")
    try:
        subprocess.run(["bash", str(setup_script)], check=True)
        print("\n✓ Polecat setup complete")
    except subprocess.CalledProcessError as e:
        print(f"\nError: Setup failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)


@main.command()
@click.option("--project", "-p", help="Initialize only this project (default: all)")
@click.pass_context
def init(ctx, project):
    """Initialize bare mirror repos in <home>/polecat/.repos/

    Creates bare clones of all registered projects for isolated worktree spawning.
    Run this once before using polecat, or when adding new projects.

    Examples:
        polecat init              # Initialize all projects
        polecat init -p aops      # Initialize only aops
        polecat --home /custom/path init  # Use custom home directory
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if project:
        try:
            path = manager.ensure_repo_mirror(project)
            print(f"✓ {project} -> {path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize {project}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Initializing mirrors in {manager.repos_dir}...")
        results = manager.init_all_mirrors()
        failures = [p for p, path in results.items() if path is None]
        if failures:
            print(f"\n⚠️  Failed: {', '.join(failures)}")
            sys.exit(1)
        print("\n✓ All mirrors ready")

    # Validate AOPS_SESSIONS is a git repo
    sessions_path = _get_sessions_base()
    if not sessions_path.is_dir():
        print(f"\n✗ AOPS_SESSIONS directory does not exist: {sessions_path}", file=sys.stderr)
        sys.exit(1)
    if not (sessions_path / ".git").exists():
        print(
            f"\n✗ AOPS_SESSIONS is not a git repo: {sessions_path}\n"
            f"  Session data will not sync without a git repo.\n"
            f"  Fix: cd {sessions_path} && git init && git remote add origin <url>",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"✓ Sessions repo: {sessions_path}")


def _clear_stale_git_lock(repo_path: Path) -> bool:
    """Remove stale .git/index.lock if no process holds it.

    Returns True if lock was cleared or didn't exist, False if held by a process.
    """
    lockfile = repo_path / ".git" / "index.lock"
    if not lockfile.exists():
        return True

    # Check if a process holds the lock
    lsof = shutil.which("lsof")
    if lsof:
        result = subprocess.run([lsof, str(lockfile)], capture_output=True, check=False)
        if result.returncode == 0:
            # Process holds the lock
            return False

    # No process holds it — stale lock, remove
    lockfile.unlink(missing_ok=True)
    return True


def _auto_resolve_merge(repo_path: Path, name: str) -> tuple[bool, str]:
    """Auto-resolve merge conflicts by keeping local (ours) versions."""
    unmerged = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not unmerged:
        return False, f"{name}: pull failed (non-conflict reason)"

    subprocess.run(
        ["git", "checkout", "--ours", "."],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=False)
    commit = subprocess.run(
        ["git", "commit", "--no-edit"],
        cwd=repo_path,
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_EDITOR": "true"},
    )
    if commit.returncode != 0:
        return False, f"{name}: merge commit failed after conflict resolution"

    conflict_files = unmerged.splitlines()
    print(
        f"⚠ {name}: merge conflict auto-resolved (kept local) in {len(conflict_files)} file(s)",
        file=sys.stderr,
    )
    return True, f"{name}: auto-resolved {len(conflict_files)} merge conflict(s)"


def _auto_resolve_rebase(repo_path: Path, name: str, ahead_count: int) -> tuple[bool, str]:
    """Auto-resolve conflicts during an in-progress rebase.

    Checks for unmerged files, resolves them (keeping local/--theirs),
    backs up remote versions of non-expendable files, and loops through
    rebase --continue until complete or unresolvable.

    Returns (success, message).
    """
    import fnmatch

    expendable_patterns = [
        "graph*.json",
        "graph*.dot",
        "graph*.svg",
        "graph*.graphml",
    ]

    def _is_expendable(filepath: str) -> bool:
        basename = Path(filepath).name
        return any(fnmatch.fnmatch(basename, p) for p in expendable_patterns)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    all_conflict_files: list[str] = []
    backup_paths: list[str] = []
    max_rounds = ahead_count + 5

    for _round in range(max_rounds):
        unmerged = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        if not unmerged:
            # No conflicts — try continuing (may be a non-conflict failure)
            cont = subprocess.run(
                ["git", "rebase", "--continue"],
                cwd=repo_path,
                capture_output=True,
                check=False,
                env={**os.environ, "GIT_EDITOR": "true"},
            )
            if cont.returncode == 0:
                break
            # rebase failed for non-conflict reason
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            return False, f"{name}: rebase failed"

        # Resolve conflicts: keep local (--theirs in rebase), backup remote for non-expendable
        resolved = True
        for cf in unmerged.splitlines():
            all_conflict_files.append(cf)
            if not _is_expendable(cf):
                rc = subprocess.run(
                    ["git", "show", f":2:{cf}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if rc.returncode == 0 and rc.stdout:
                    bp = Path(repo_path) / f"{cf}.conflict-remote-{timestamp}"
                    bp.parent.mkdir(parents=True, exist_ok=True)
                    bp.write_text(rc.stdout)
                    backup_paths.append(str(bp.relative_to(repo_path)))

            r = subprocess.run(
                ["git", "checkout", "--theirs", "--", cf],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if r.returncode == 0:
                subprocess.run(
                    ["git", "add", cf],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                )
            else:
                resolved = False
                break

        if not resolved:
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            return False, f"{name}: conflict needs manual resolution"

        # Stage backup files
        for bp in backup_paths:
            subprocess.run(
                ["git", "add", bp],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )

        cont = subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=repo_path,
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_EDITOR": "true"},
        )
        if cont.returncode == 0:
            break
        # If continue failed, loop back to check for new conflicts
    else:
        subprocess.run(
            ["git", "rebase", "--abort"],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        return False, f"{name}: rebase exceeded max rounds ({max_rounds})"

    if all_conflict_files:
        conflict_summary = ", ".join(set(all_conflict_files))
        warn = (
            f"⚠ {name}: rebase conflict auto-resolved (kept local) in: {conflict_summary}. "
            f"Remote versions saved to: {', '.join(backup_paths) or 'none'}"
        )
        print(warn, file=sys.stderr)

    return True, f"{name}: auto-resolved {len(set(all_conflict_files))} conflict(s)"


_OVERSIZE_BYTES = 95 * 1024 * 1024  # GitHub rejects >100 MB; leave headroom.


def _unstage_oversized(repo_path: Path, name: str) -> None:
    """Drop files over GitHub's push limit from the index.

    GitHub hard-rejects pushes containing any file >100 MB. The auto-commit
    path stages new files indiscriminately via `git add .`; this scrubs the
    index of anything over the threshold so the push doesn't fail and one
    rogue file doesn't block every other change in the same sync.
    Oversized files are left on disk and warned about — the operator can
    decide whether to gitignore them, split them, or store them elsewhere.
    """
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    oversized: list[str] = []
    for rel in (p for p in staged.split("\0") if p):
        try:
            if (repo_path / rel).stat().st_size > _OVERSIZE_BYTES:
                oversized.append(rel)
        except OSError:
            continue  # deleted file or symlink target gone — ignore
    if not oversized:
        return
    subprocess.run(
        ["git", "restore", "--staged", "--", *oversized],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    sizes = ", ".join(
        f"{f} ({(repo_path / f).stat().st_size / 1024 / 1024:.0f} MB)" for f in oversized
    )
    print(
        f"⚠ {name}: skipped {len(oversized)} oversized file(s) (>95 MB): {sizes}",
        file=sys.stderr,
    )


_GIT_NETWORK_TIMEOUT = 60
_GIT_NETWORK_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new",
    "GIT_HTTP_LOW_SPEED_LIMIT": "1000",
    "GIT_HTTP_LOW_SPEED_TIME": "30",
}


def _run_git_network(
    args: list[str],
    cwd: Path,
    *,
    timeout: int = _GIT_NETWORK_TIMEOUT,
) -> subprocess.CompletedProcess | None:
    """Run a network-touching git command with a timeout and SSH/HTTP hardening.

    Returns the CompletedProcess on completion, or None if it timed out.
    """
    env = {**os.environ, **_GIT_NETWORK_ENV}
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None


def _sync_working_repo(
    repo_path: Path,
    *,
    auto_commit: bool = False,
    quiet: bool = False,
    merge_strategy: str = "rebase",
) -> tuple[bool, str]:
    """Sync a working repo: fetch, pull/push, auto-resolve conflicts.

    Returns (success, message).
    """
    name = repo_path.name

    if not (repo_path / ".git").exists():
        return False, f"{name}: not a git repo"

    if not _clear_stale_git_lock(repo_path):
        return False, f"{name}: git lock held by active process"

    # Fetch
    if _run_git_network(["git", "fetch", "--quiet"], repo_path) is None:
        return False, f"{name}: fetch timed out after {_GIT_NETWORK_TIMEOUT}s"

    # Check status
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    dirty = bool(porcelain)

    # Check ahead/behind
    tracking = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    ahead_count = behind_count = 0
    if tracking:
        counts = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if counts:
            parts = counts.split()
            if len(parts) == 2:
                ahead_count, behind_count = int(parts[0]), int(parts[1])

    if dirty:
        if auto_commit:
            # Stage all files (including new untracked) and commit
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=False)
            _unstage_oversized(repo_path, name)
            has_staged = (
                subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                ).returncode
                != 0
            )

            if has_staged:
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"auto: sync {datetime.now():%Y-%m-%d %H:%M}",
                        "--quiet",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                )

            pull_flag = "--rebase" if merge_strategy == "rebase" else "--no-rebase"
            pull = _run_git_network(["git", "pull", pull_flag, "--quiet"], repo_path)
            if pull is None:
                return False, f"{name}: pull timed out after {_GIT_NETWORK_TIMEOUT}s"
            if pull.returncode != 0:
                if merge_strategy == "merge":
                    ok, resolve_msg = _auto_resolve_merge(repo_path, name)
                else:
                    ok, resolve_msg = _auto_resolve_rebase(repo_path, name, ahead_count)
                if not ok:
                    return False, resolve_msg

            # Push
            push = _run_git_network(["git", "push", "--quiet"], repo_path)
            if push is None:
                return False, f"{name}: push timed out after {_GIT_NETWORK_TIMEOUT}s"
            if push.returncode != 0:
                return False, f"{name}: push failed"
            return True, f"{name}: auto-synced (committed + pushed)"
        else:
            status_parts = ["dirty"]
            if ahead_count:
                status_parts.append(f"{ahead_count} ahead")
            if behind_count:
                status_parts.append(f"{behind_count} behind")
            return False, f"{name}: {', '.join(status_parts)} (skipped — not auto-commit)"

    elif behind_count > 0 and ahead_count == 0:
        pull = _run_git_network(["git", "pull", "--quiet"], repo_path)
        if pull is None:
            return False, f"{name}: pull timed out after {_GIT_NETWORK_TIMEOUT}s"
        if pull.returncode == 0:
            return True, f"{name}: pulled {behind_count} commit(s)"
        return False, f"{name}: pull failed"

    elif ahead_count > 0:
        if behind_count > 0:
            pull_flag = "--rebase" if merge_strategy == "rebase" else "--no-rebase"
            pull = _run_git_network(["git", "pull", pull_flag, "--quiet"], repo_path)
            if pull is None:
                return False, f"{name}: pull timed out after {_GIT_NETWORK_TIMEOUT}s"
            if pull.returncode != 0:
                if merge_strategy == "merge":
                    ok, resolve_msg = _auto_resolve_merge(repo_path, name)
                else:
                    ok, resolve_msg = _auto_resolve_rebase(repo_path, name, ahead_count)
                if not ok:
                    return False, resolve_msg
        push = _run_git_network(["git", "push", "--quiet"], repo_path)
        if push is None:
            return False, f"{name}: push timed out after {_GIT_NETWORK_TIMEOUT}s"
        if push.returncode == 0:
            return True, f"{name}: pushed {ahead_count} commit(s)"
        return False, f"{name}: push failed"

    else:
        return True, f"{name}: ok"


@main.command()
@click.option("--check", is_flag=True, help="Just show status, don't fix anything")
@click.option("--quiet", "-q", is_flag=True, help="Only show repos needing attention")
@click.option("--mirrors-only", is_flag=True, help="Only sync bare mirrors (skip working repos)")
@click.pass_context
def sync(ctx, check, quiet, mirrors_only):
    """Sync all git repos: working repos and bare mirrors.

    Fetches, pulls, and pushes working repos defined in $AOPS_SESSIONS/polecat.yaml.
    Also updates bare mirrors used by polecat workers.

    Working repos are only pulled/pushed if clean.

    Examples:
        polecat sync              # Sync everything
        polecat sync --check      # Just show status
        polecat sync --quiet      # Only show issues
        polecat sync --mirrors-only  # Only sync bare mirrors
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # --- Phase 1: Working repos ---
    if not mirrors_only:
        if not quiet:
            print("Syncing working repos...")

        needs_attention = []
        for project_name, project_cfg in manager.projects.items():
            repo_path = project_cfg["path"]
            if repo_path is None or not repo_path.is_dir():
                if not quiet:
                    print(f"  {project_name}: path not found")
                continue

            auto_commit = bool(project_cfg.get("auto_commit", False)) and not check
            merge_strategy = project_cfg.get("merge_strategy", "merge" if auto_commit else "rebase")
            success, msg = _sync_working_repo(
                repo_path, auto_commit=auto_commit, quiet=quiet, merge_strategy=merge_strategy
            )
            if not success or not quiet:
                print(f"  {msg}")
            if not success:
                needs_attention.append(project_name)

        if not quiet:
            if needs_attention:
                print(f"\n⚠ {len(needs_attention)} repo(s) need attention")
            else:
                print()

    # --- Phase 2: Bare mirrors ---
    if check:
        return
    if not quiet:
        print(f"Syncing mirrors in {manager.repos_dir}...")
    results = manager.sync_all_mirrors()
    successes = sum(1 for v in results.values() if v)
    if not quiet:
        print(f"✓ Synced {successes}/{len(results)} mirrors")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.pass_context
def start(ctx, project, caller):
    """Claim next ready task and spawn a worktree."""
    from polecat.claim import claim_next_ready

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    task = claim_next_ready(manager, caller, project)

    print(f"Claimed task: {task.title} ({task.id})")

    try:
        worktree_path = manager.setup_worktree(task)
        print(f"\nSuccess! Worktree ready at:\n{worktree_path}")
        print(f"\nTo start working:\ncd {worktree_path}")
    except Exception as e:
        print(f"\nError setting up worktree: {e}")
        if task:
            rollback_status = _rollback_status_for(task)
            print(
                f"Reverting task {task.id} to {rollback_status}...",
                file=sys.stderr,
            )
            try:
                manager.update_task(task.id, status=rollback_status, assignee=None)
            except Exception as re:
                print(f"Failed to revert task {task.id}: {re}", file=sys.stderr)
        sys.exit(1)


@main.command()
@click.argument("task_id")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.pass_context
def checkout(ctx, task_id, caller):
    """Checkout a specific task by ID and create its worktree.

    Use with shell integration for automatic cd:
        cd $(polecat checkout TASK_ID)

    Or add to your shell rc:
        pc() { cd "$(polecat checkout "$@")" 2>/dev/null || polecat checkout "$@"; }
    """
    # Validate task ID before any operations
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if manager.storage is not None:
        task = manager.storage.get_task(task_id)
    else:
        from polecat.pkb_bridge import get_task as pkb_get_task

        task = pkb_get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    # Claim the task if not already in progress
    try:
        from lib.task_model import TaskStatus

        if task.status in (
            getattr(TaskStatus, "QUEUED", None),
            getattr(TaskStatus, "ACTIVE", None),
        ):
            task.status = TaskStatus.IN_PROGRESS.value
            task.assignee = caller
            manager.storage.save_task(task)
            print(f"Claimed: {task.title}", file=sys.stderr)
    except ImportError:
        # PKB canonical statuses agents may claim from. See
        # aops-core/skills/remember/references/TAXONOMY.md. NEVER include
        # "active" — that is a non-canonical legacy term PKB rejects.
        if task.status in ("ready", "queued"):
            from polecat.pkb_bridge import update_task as pkb_update_task

            pkb_update_task(task_id, status="in_progress", assignee=caller)
            task.status = "in_progress"
            task.assignee = caller
            print(f"Claimed: {task.title}", file=sys.stderr)

    try:
        worktree_path = manager.setup_worktree(task)
        # Output just the path for shell integration (cd $(polecat checkout ...))
        print(worktree_path)
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)


# NOTE: ``finish`` lives in polecat/finalize.py and is registered below via
# ``main.add_command(finish_cmd)``. The helpers it relies on (_check_gh_installed,
# _generate_pr_body, _read_latest_real_transcript_path) remain in this module and
# are imported lazily inside finish_cmd to avoid an import cycle.


@main.command()
@click.argument("target", required=False)
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
@click.option(
    "--allow-unpushed",
    is_flag=True,
    help="Bypass the A3/A8 integrity gate that refuses to destroy unpushed commits. "
    "Use only when you are sure the commits can be discarded.",
)
@click.pass_context
def nuke(ctx, target, force, allow_unpushed):
    """Destroy a polecat or crew worker, or clean up stale branches when run without args."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if target:
        crew_path = manager.crew_dir / target
        if crew_path.exists():
            try:
                manager.nuke_crew(target, force=force)
                return
            except (ValueError, RuntimeError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        # Fallback to worktree logic
        try:
            validate_task_id_or_raise(target)
            manager.nuke_worktree(target, force=force, allow_unpushed=allow_unpushed)
            print(f"Nuked polecat {target}")
            return
        except TaskIDValidationError:
            print(
                f"Error: Target '{target}' is not a valid crew worker or task ID.", file=sys.stderr
            )
            sys.exit(1)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Target not provided, run stale cleanup
    print("No target provided. Cleaning up stale branches...")

    # 1. Cleanup stale worktrees
    if manager.polecats_dir.exists():
        for d in manager.polecats_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                task_id = d.name
                if manager.storage is not None:
                    task = manager.storage.get_task(task_id)
                else:
                    from polecat.pkb_bridge import get_task as pkb_get_task

                    task = pkb_get_task(task_id)
                if not task:
                    is_stale = True
                else:
                    # A malformed task raises ValueError from get_repo_path.
                    # Two distinct cases:
                    #   1. task.project is None/empty — structural data problem.
                    #   2. task.project names a project removed from polecat.yaml
                    #      — the project is no longer resolvable, so this
                    #      worktree will be silently skipped on every sweep and
                    #      never automatically cleaned up.
                    #
                    # Both are intentionally deferred: case 2 requires
                    # PKB-driven discovery (iterate tasks, not the filesystem)
                    # tracked in task-df1e5aa3. Skipping is strictly safer
                    # than aborting the whole sweep.
                    try:
                        repo_path = manager.get_repo_path(task)
                    except ValueError as e:
                        print(
                            f"Warning: skipping {task_id}: {e}",
                            file=sys.stderr,
                        )
                        continue
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

                # A crew is stale if all of its branches are merged or deleted
                projects = [d.name for d in c.iterdir() if d.is_dir()]
                if not projects:
                    continue

                any_repo_checked = False
                all_stale = True
                for project in projects:
                    repo_path = manager.projects.get(project, {}).get("path")
                    if not repo_path:
                        repo_path = manager.repos_dir / f"{project}.git"

                    if not repo_path.exists():
                        continue

                    any_repo_checked = True
                    if manager._branch_exists(repo_path, branch_name):
                        if not manager._is_branch_merged(repo_path, branch_name):
                            all_stale = False
                            break

                if not any_repo_checked:
                    continue
                if all_stale:
                    print(f"Nuking stale crew: {crew_name}")
                    try:
                        manager.nuke_crew(crew_name, force=True)
                    except (RuntimeError, ValueError) as e:
                        print(f"Warning: Failed to nuke crew {crew_name}: {e}", file=sys.stderr)


@main.command("ping-pkb")
@click.pass_context
def ping_pkb(ctx):
    """Probe PKB MCP reachability + initialize handshake.

    Exits 0 on success; 4 if PKB_MCP_URL is unset; 5 if the server is
    unreachable, refuses the connection, or the initialize handshake fails.

    The supervisor's pre-dispatch readiness gate calls this BEFORE firing a
    polecat run — locally and (over SSH) on the target host. A successful
    ping means the same configuration that polecat will use can complete
    PkbClient._initialize() without raising ConnectionRefusedError. See
    issues #598 and #600.
    """
    url = os.environ.get("PKB_MCP_URL")
    if not url:
        print(
            "polecat ping-pkb: PKB_MCP_URL is not set.\n"
            "  Export it to point at the PKB MCP HTTP endpoint, e.g.:\n"
            "      export PKB_MCP_URL=http://localhost:8026/mcp",
            file=sys.stderr,
        )
        sys.exit(4)

    from polecat.pkb_bridge import PkbClient

    print(f"polecat ping-pkb: probing {url}...")
    try:
        client = PkbClient(url)
    except (TimeoutError, urllib.error.URLError, ConnectionRefusedError) as e:
        print(
            f"polecat ping-pkb: FAILED to reach PKB MCP at {url}: {e}\n"
            "  This is the same failure mode that crashes `polecat run`'s\n"
            "  PkbClient._initialize() (see issues #598, #600). Fix PKB_MCP_URL\n"
            "  or expose the PKB service to this host (e.g. over Tailscale)\n"
            "  before dispatching a worker here.",
            file=sys.stderr,
        )
        sys.exit(5)
    except Exception as e:
        print(
            f"polecat ping-pkb: FAILED with unexpected error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        sys.exit(5)

    # Issue a low-cost tools/call to confirm the session is usable, not just
    # that the TCP socket accepted bytes. ``list_tasks`` with limit=1 keeps
    # the round-trip cheap and exercises the same code path workers use.
    try:
        result = client.call_tool("list_tasks", {"limit": 1})
    except Exception as e:
        print(
            f"polecat ping-pkb: handshake succeeded but tools/call failed: {e}",
            file=sys.stderr,
        )
        sys.exit(5)

    if result is None:
        print(
            "polecat ping-pkb: handshake succeeded but list_tasks returned no\n"
            "  result (server may have rejected the request — check logs).",
            file=sys.stderr,
        )
        sys.exit(5)

    print(f"polecat ping-pkb: OK — {url} reachable, MCP handshake succeeded.")


def _get_running_polecat_containers() -> set[str] | None:
    """Return task IDs with running polecat containers, or None if Docker unavailable.

    Queries `docker ps` for containers named polecat-<task_id> and extracts
    the task ID portion. Returns None when Docker cannot be reached or the daemon
    is remote (containers won't carry the polecat- prefix there) so callers can
    degrade gracefully to [UNKNOWN].
    """
    try:
        if _is_remote_daemon():
            return None
    except Exception:
        return None
    try:
        result = subprocess.run(
            [_resolve_docker_binary(), "ps", "--filter", "name=polecat-", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        running: set[str] = set()
        for name in result.stdout.strip().splitlines():
            if name.startswith("polecat-"):
                running.add(name[len("polecat-") :])
        return running
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


@main.command("list")
@click.pass_context
def list_polecats(ctx):
    """List active polecats, labelling stale worktrees without running containers."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    if not manager.polecats_dir.exists():
        print("No active polecats.")
        return

    running = _get_running_polecat_containers()
    docker_unavailable = running is None

    found = False
    for item in sorted(manager.polecats_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            task_id = item.name
            if docker_unavailable:
                label = "[UNKNOWN]"
            elif task_id in running:
                label = "[ACTIVE] "
            else:
                label = "[STALE]  "
            print(f"{label} {task_id} -> {item}")
            found = True

    if not found:
        print("No active polecats.")
    elif docker_unavailable:
        print(
            "\nWarning: Docker unavailable — container status unknown.",
            file=sys.stderr,
        )


# `sweep` subcommand removed — see task-9fa50763.
# PR-state transitions are now handled in-band by the supervisor agent loop
# (event-driven monitoring via `gh pr view` + Monitor). Keeping a duplicate
# shell command invited divergence between sweep rules and agent rules.


def _clone_has_changes(repo_path: Path, branch_name: str) -> bool:
    """Check if a crew branch has pushed work not yet merged to the default branch.

    Fetches fresh state from origin before checking, so this is correct even
    when the local clone is stale (e.g. after a Docker session where commits
    happened inside the container and were pushed directly to origin).

    Returns True if:
    - There are uncommitted local changes in the working tree, OR
    - The remote crew branch has commits with content not yet in the default branch
    Returns False if the remote branch is absent, merged, or squash-merged.
    """
    try:
        # Check for uncommitted local changes (catches non-Docker in-progress work)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if status.returncode == 0 and status.stdout.strip():
            return True

        # Determine the default branch name
        head_result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        default_ref = (
            head_result.stdout.strip()
            if head_result.returncode == 0
            else "refs/remotes/origin/main"
        )
        default_branch_short = default_ref.removeprefix("refs/remotes/origin/")

        # Use ls-remote to check branch existence on origin.
        # Cleanly separates "branch absent" (exit 0, empty stdout) from
        # "can't reach origin" (exit non-0 → unknown state → preserve).
        remote_branch_ref = f"refs/remotes/origin/{branch_name}"
        ls_remote = subprocess.run(
            ["git", "ls-remote", "origin", f"refs/heads/{branch_name}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if ls_remote.returncode != 0:
            # Can't reach origin — cannot determine state; safe default is preserve.
            return True
        if not ls_remote.stdout.strip():
            # Origin reachable but branch absent — nothing was pushed, safe to nuke.
            return False

        # Branch exists on remote. Fetch fresh state to update local tracking refs.
        subprocess.run(
            ["git", "fetch", "origin", branch_name, default_branch_short],
            cwd=repo_path,
            capture_output=True,
            timeout=15,
            check=False,
        )

        # Count commits on the remote crew branch not reachable from remote default.
        rev_count = subprocess.run(
            ["git", "rev-list", "--count", f"{default_ref}..{remote_branch_ref}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if rev_count.returncode == 0:
            count = int(rev_count.stdout.strip())
            if count == 0:
                # All commits are ancestors of the default branch (normal merge).
                return False

            # Commits exist beyond the default branch. Check if content is identical —
            # this handles squash-merge/rebase where commits land in main with
            # different SHAs but the same file content.
            diff = subprocess.run(
                ["git", "diff", "--quiet", default_ref, remote_branch_ref],
                cwd=repo_path,
                capture_output=True,
                timeout=10,
            )
            if diff.returncode == 0:
                # Content identical to default → squash-merged → safe to nuke.
                return False
            return True  # Genuine unmerged work exists — preserve.

    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    # If we can't determine, assume there are changes (safe default).
    return True


def _branch_has_open_pr(branch_name: str, repo_path: Path) -> bool:
    """Check if a branch has an open PR on GitHub."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch_name, "--state", "open", "--json", "number"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = json.loads(result.stdout)
            return len(prs) > 0
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return False


@main.command("c", hidden=True, context_settings={"ignore_unknown_options": True})
@click.argument("target", required=False, default=None)
@click.argument("extra", required=False, default=None)
@click.option("--name", "-n", help="Crew name (randomly generated if not specified)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Drop into an interactive shell (no agent)")
@click.option("--resume", "-r", help="Resume existing crew worker by name")
@click.option("--keep", "-k", is_flag=True, help="Keep worktree even if a PR is open")
@click.option("--memory", default=None, help="Container memory limit (e.g. 4g, 2048m)")
@click.option("--model", default=None, help="Override the model (claude/gemini model id).")
@click.option(
    "--debug/--no-debug",
    "debug_flag",
    default=None,
    help="Override debug from polecat.yaml. --debug forwards DEBUG_HOOKS=1 into the container.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override an arbitrary config key (e.g. gates.handover=block).",
)
@click.argument("agent_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def crew_alias(
    ctx,
    target,
    extra,
    name,
    gemini,
    interactive,
    resume,
    keep,
    memory,
    model,
    debug_flag,
    set_overrides,
    agent_args,
):
    """Shorthand for 'crew'. See 'polecat crew --help'."""
    ctx.invoke(
        crew,
        target=target,
        extra=extra,
        name=name,
        gemini=gemini,
        interactive=interactive,
        resume=resume,
        keep=keep,
        memory=memory,
        model=model,
        debug_flag=debug_flag,
        set_overrides=set_overrides,
        agent_args=agent_args,
    )


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("target", required=False, default=None)
@click.argument("extra", required=False, default=None)
@click.option("--name", "-n", help="Crew name (randomly generated if not specified)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Drop into an interactive shell (no agent)")
@click.option("--resume", "-r", help="Resume existing crew worker by name")
@click.option("--keep", "-k", is_flag=True, help="Keep worktree even if a PR is open")
@click.option("--memory", default=None, help="Container memory limit (e.g. 4g, 2048m)")
@click.option("--model", default=None, help="Override the model (claude/gemini model id).")
@click.option(
    "--debug/--no-debug",
    "debug_flag",
    default=None,
    help="Override debug from polecat.yaml. --debug forwards DEBUG_HOOKS=1 into the container.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override an arbitrary config key (e.g. gates.handover=block).",
)
@click.argument("agent_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def crew(
    ctx,
    target,
    extra,
    name,
    gemini,
    interactive,
    resume,
    keep,
    memory,
    model,
    debug_flag,
    set_overrides,
    agent_args,
):
    """Start an interactive crew session with worker isolation.

    Crew workers are persistent, named agents for interactive collaboration.
    Each crew session creates an isolated local git clone and drops you into it.
    Workers are sandboxed to their clone — no operations outside it.

    TARGET is a project alias (e.g., aops, bm), or 'repo' for arbitrary paths.
    If TARGET is 'repo', EXTRA is the path to the repository.

    Any extra arguments after '--' are passed through to the underlying agent CLI.

    \b
    Examples:
        polecat crew aops             # Crew in academicOps repo
        polecat crew bm               # Crew in buttermilk repo
        polecat crew repo /path/to/x  # Crew in arbitrary repo
        polecat crew -r audre         # Resume crew worker "audre"
        polecat crew -i aops          # Interactive shell in crew container
        polecat crew -g aops          # Gemini CLI in sandbox mode
        polecat crew aops -- -p "do something"  # Pass args to agent CLI
    """
    import subprocess

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # --- Resolve target project(s) ---
    if resume:
        # Resume mode: ignore target, use existing crew
        projects = []  # Will be populated from existing worktrees
        crew_name = resume
        if crew_name not in manager.list_crew():
            print(
                f"Error: No crew worker named '{crew_name}'. Active: {manager.list_crew()}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif target == "repo":
        # Ad-hoc repo mode: pc crew repo /path/to/repo
        if not extra:
            print("Error: 'repo' target requires a path argument.", file=sys.stderr)
            print("Usage: polecat crew repo /path/to/repo", file=sys.stderr)
            sys.exit(1)
        repo_path = Path(extra).expanduser().resolve()
        try:
            slug = manager.register_adhoc_project(repo_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        projects = [slug]
        crew_name = name or manager.generate_crew_name()
    elif target:
        # Named project/alias: pc crew aops, pc crew bm
        try:
            slug = manager.resolve_project_alias(target)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        projects = [slug]
        crew_name = name or manager.generate_crew_name()
    else:
        # No target and not resuming
        print("Error: 'crew' requires a target project or --resume.", file=sys.stderr)
        print("Usage: polecat crew <project>  # e.g., 'polecat crew aops'", file=sys.stderr)
        print("       polecat crew -r <name>  # resume existing crew", file=sys.stderr)
        sys.exit(1)

    print(f"\U0001f9d1\u200d\U0001f91d\u200d\U0001f9d1 Crew worker: {crew_name}")

    # Setup isolated clones for project(s)
    clone_paths = {}
    if resume:
        # Recover clone paths from existing crew directory and sync with upstream
        crew_path = manager.crew_dir / crew_name
        for project_dir in crew_path.iterdir():
            if project_dir.is_dir() and (project_dir / ".git").exists():
                clone_paths[project_dir.name] = project_dir
                print(f"\U0001f4c1 {project_dir.name}: {project_dir}")
                # Sync with upstream so we don't resume on stale code
                print(f"   Syncing {project_dir.name} with origin...")
                fetch_result = _run_git_network(["git", "fetch", "origin"], project_dir)
                if fetch_result is None:
                    print(f"   \u26a0 git fetch timed out after {_GIT_NETWORK_TIMEOUT}s")
                    continue
                if fetch_result.returncode != 0:
                    print(f"   \u26a0 git fetch failed: {fetch_result.stderr.strip()}")
                    continue
                # Detect default branch from remote HEAD, fall back to project config
                head_result = subprocess.run(
                    ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=project_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if head_result.returncode == 0:
                    # refs/remotes/origin/HEAD -> refs/remotes/origin/main
                    default_branch = head_result.stdout.strip().split("/")[-1]
                else:
                    default_branch = manager.projects.get(project_dir.name, {}).get(
                        "default_branch", "main"
                    )
                merge_result = subprocess.run(
                    ["git", "merge", "--ff-only", f"origin/{default_branch}"],
                    cwd=project_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if merge_result.returncode == 0:
                    print(f"   \u2705 Up to date with origin/{default_branch}")
                else:
                    print(
                        f"   \u26a0 Could not fast-forward to origin/{default_branch} "
                        f"(local changes?). Manual merge may be needed."
                    )
                    if merge_result.stderr:
                        print(f"      Git error: {merge_result.stderr.strip()}")

                # Detect divergence between local crew branch and its origin
                # counterpart (e.g. force-push upstream). The previous
                # implementation silently ignored this.
                crew_branch = f"crew/{crew_name}"
                remote_ref = f"refs/remotes/origin/{crew_branch}"
                remote_exists = (
                    subprocess.run(
                        ["git", "rev-parse", "--verify", "--quiet", remote_ref],
                        cwd=project_dir,
                        capture_output=True,
                    ).returncode
                    == 0
                )
                local_exists = (
                    subprocess.run(
                        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{crew_branch}"],
                        cwd=project_dir,
                        capture_output=True,
                    ).returncode
                    == 0
                )
                if remote_exists and local_exists:
                    local_anc = (
                        subprocess.run(
                            [
                                "git",
                                "merge-base",
                                "--is-ancestor",
                                f"refs/heads/{crew_branch}",
                                remote_ref,
                            ],
                            cwd=project_dir,
                            capture_output=True,
                        ).returncode
                        == 0
                    )
                    remote_anc = (
                        subprocess.run(
                            [
                                "git",
                                "merge-base",
                                "--is-ancestor",
                                remote_ref,
                                f"refs/heads/{crew_branch}",
                            ],
                            cwd=project_dir,
                            capture_output=True,
                        ).returncode
                        == 0
                    )
                    if local_anc and not remote_anc:
                        ahead = subprocess.run(
                            [
                                "git",
                                "rev-list",
                                "--count",
                                f"refs/heads/{crew_branch}..{remote_ref}",
                            ],
                            cwd=project_dir,
                            capture_output=True,
                            text=True,
                        ).stdout.strip()
                        print(
                            f"   \u26a0 {crew_branch} is {ahead} commits behind "
                            f"origin/{crew_branch}. Run 'git pull --ff-only' "
                            f"inside the crew session."
                        )
                    elif not local_anc and not remote_anc:
                        print(
                            f"   \u274c {crew_branch} has DIVERGED from "
                            f"origin/{crew_branch} (likely force-push upstream). "
                            f"Local and remote have commits the other doesn't. "
                            f"Resolve manually: 'git log --oneline --graph "
                            f"HEAD origin/{crew_branch}'."
                        )
        projects = list(clone_paths.keys())
    else:
        try:
            for proj in projects:
                clone_path = manager.setup_crew_worktree(crew_name, proj)
                clone_paths[proj] = clone_path
                print(f"\U0001f4c1 {proj}: {clone_path}")
        except FileExistsError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error setting up crew clone: {e}", file=sys.stderr)
            sys.exit(1)

    if not clone_paths:
        print("Error: No clones available.", file=sys.stderr)
        sys.exit(1)

    # Determine working directory:
    # Single project -> drop directly into the project clone
    # Multiple projects -> use crew root (parent of all project clones)
    if len(clone_paths) == 1:
        work_dir = next(iter(clone_paths.values()))
    else:
        work_dir = manager.crew_dir / crew_name

    # Build agent command with isolation
    if interactive:
        cli_tool = "shell"
    elif gemini:
        cli_tool = "gemini"
    else:
        cli_tool = "claude"
    print(f"\n\U0001f91d Starting {cli_tool} crew session...")
    print(f"   Crew: {crew_name}")
    print(f"   Projects: {', '.join(projects)}")
    print(f"   Working dir: {work_dir}")
    cfg, session_cfg = _resolve_session_config(
        "crew",
        client=cli_tool,
        model=model,
        debug=debug_flag,
        set_overrides=set_overrides,
    )
    _client_model = None if cli_tool == "shell" else session_cfg.model_for(cli_tool)
    print(
        "   Mode: "
        f"hooks_enabled={session_cfg.hooks_enabled}, "
        f"model={_client_model}, debug={session_cfg.debug}"
    )
    print(f"   Config: {cfg.source_path}")
    print("-" * 50)

    if interactive:
        # Interactive shell: drop into bash inside the Docker container.
        # Both claude and gemini CLIs are pre-installed in the image along
        # with their aops plugins, so the user can run either manually.
        cmd = ["bash"]
    elif gemini:
        # Gemini: run inside our Docker container (not --sandbox, which uses
        # bind mounts that fail on WSL2/Docker Desktop).  Auth files are staged
        # via docker cp, and session transcripts are extracted after the run.
        # --approval-mode yolo: gemini's plan mode default-denies tools that
        # lack an explicit allow rule, blocking even read_file/list_directory.
        # Trust boundary is the polecat router hook + policy engine, not the
        # gemini approval prompt. Autonomous workers must never run in plan mode.
        # Only inject approval-mode if agent_args doesn't already provide one —
        # callers may pass --approval-mode via extra args after '--'.
        _has_approval = agent_args and "--approval-mode" in agent_args
        cmd = ["gemini"]
        if not _has_approval:
            cmd.extend(["--approval-mode", "yolo"])
        cmd.extend(
            [
                "--include-directories",
                "/home/worker/.gemini/extensions/aops-core",
                "--model",
                session_cfg.gemini_model,
            ]
        )
    else:
        # Claude Code: sandbox via project settings.json + setting-sources.
        # Plan mode + full hook stack — the legacy hooks-off branch was removed
        # along with the vanilla settings template (#940).
        cmd = [
            "claude",
            "--permission-mode=plan",
            "--allow-dangerously-skip-permissions",
            "--setting-sources=user,project",
            "--model",
            session_cfg.claude_model,
        ]

    # Append any extra args passed after '--' to the agent command
    if agent_args:
        cmd.extend(agent_args)

    # Set session type environment variable for hooks to detect
    # Use sanitized env: SSH stripped, git auth set to bot token only
    env = _make_worker_env(interactive=True, work_dir=work_dir)
    env["POLECAT_SESSION_TYPE"] = "crew"
    env["POLECAT_CREW_NAME"] = crew_name
    if session_cfg.debug:
        env["DEBUG_HOOKS"] = "1"
    # Claude crew runs in plan mode; signal that to the gate engine so it
    # skips the custodiet ops counter (the gate must not fire when rbg
    # cannot be invoked). Suppressed for gemini / interactive shell paths.
    if not interactive and not gemini:
        env["POLECAT_APPROVAL_MODE"] = "plan"

    # Compute session directory for Claude transcript persistence.
    project_slug = target or projects[0]
    session_dir = _get_sessions_base() / "crew" / crew_name / project_slug
    env["AOPS_SESSION_STATE_DIR"] = str(session_dir)

    # Resolve container memory limit and check daemon memory
    memory_limit, daemon_mem = _init_container_memory(memory, manager, env)

    tmp_gemini_home = None
    tmp_files: list[Path] = []
    if gemini:
        # Replicate Gemini authentication — creates a temp dir with .gemini/ auth files.
        tmp_gemini_home = _replicate_gemini_auth(
            env, work_dir=work_dir, hooks_enabled=session_cfg.hooks_enabled
        )
        if tmp_gemini_home:
            print(f"   Auth: Replicated to {tmp_gemini_home}")

        # _replicate_gemini_auth sets env["GEMINI_CLI_HOME"] to the host tmp
        # path (its original use was Gemini's own --sandbox flag, where the
        # host path equals the in-container path via bind-mount). For polecat's
        # docker-wrap path the auth files are staged to /home/worker/.gemini/
        # via docker cp (see staging block below), so the in-container value
        # must be /home/worker. agent-env-map.conf forwards GEMINI_CLI_HOME
        # verbatim from this env into `docker run -e`, so override here BEFORE
        # _build_docker_cmd reads it. Without this, gemini in-container reads
        # from the non-existent host path and auth fails (regression of #931).
        env["GEMINI_CLI_HOME"] = "/home/worker"

        # Provide a stable Gemini session ID based on the crew name.
        # GEMINI_SESSION_ID is also used by the framework as a provider
        # discriminator (Gemini CLI sets it itself when launched directly).
        # AOPS_SESSION_ID is the canonical, vendor-neutral name read by
        # skills/agents/gates — set it here so Gemini sessions match the
        # Claude Code path (which sets it via the SessionStart hook).
        crew_hash = hashlib.sha256(crew_name.encode()).hexdigest()[:8]
        gemini_session_id = f"{crew_hash}-gemini"
        env["GEMINI_SESSION_ID"] = gemini_session_id
        env["AOPS_SESSION_ID"] = gemini_session_id

        # Gemini's isHeadlessMode() forces non-interactive mode when CI=true,
        # even with a TTY attached. _make_worker_env sets CI=true to suppress
        # prompts in gh/git, but that breaks gemini's interactive REPL — crew
        # sessions must stay interactive. Drop it for this path only.
        headless = agent_args and "-p" in agent_args
        if not headless:
            env.pop("CI", None)

        # Wrap Gemini in our Docker container (same as Claude path).
        # Headless when agent_args contains -p (prompt mode, no TTY needed)
        docker_cmd = _build_docker_cmd(
            "gemini",
            work_dir,
            env,
            cmd,
            is_interactive=not headless,
            tmp_files=tmp_files,
            session_dir=session_dir,
            memory_limit=memory_limit,
            cfg=cfg,
            hooks_enabled=session_cfg.hooks_enabled,
            project_slug=project_slug,
            manager=manager,
        )

        # Copy replicated .gemini/ auth into staging_dir so docker cp injects
        # it into /home/worker/.gemini/ via the entrypoint.
        if tmp_gemini_home and docker_cmd.staging_dir:
            src_gemini = tmp_gemini_home / ".gemini"
            if src_gemini.is_dir():
                dst_gemini = docker_cmd.staging_dir / ".gemini"
                if dst_gemini.exists():
                    shutil.rmtree(dst_gemini)
                shutil.copytree(src_gemini, dst_gemini)

        final_cmd = docker_cmd.cmd
    elif interactive:
        # Interactive shell: wrap in Docker container (same as Claude path)
        docker_cmd = _build_docker_cmd(
            "shell",
            work_dir,
            env,
            cmd,
            is_interactive=True,
            tmp_files=tmp_files,
            session_dir=session_dir,
            memory_limit=memory_limit,
            cfg=cfg,
            hooks_enabled=session_cfg.hooks_enabled,
            project_slug=project_slug,
            manager=manager,
        )
        final_cmd = docker_cmd.cmd
    else:
        # Claude Code: manually wrap in docker container
        # Headless when agent_args contains -p (prompt mode, no TTY needed)
        headless = agent_args and "-p" in agent_args
        docker_cmd = _build_docker_cmd(
            cli_tool,
            work_dir,
            env,
            cmd,
            is_interactive=not headless,
            tmp_files=tmp_files,
            session_dir=session_dir,
            memory_limit=memory_limit,
            cfg=cfg,
            hooks_enabled=session_cfg.hooks_enabled,
            project_slug=project_slug,
            manager=manager,
        )
        final_cmd = docker_cmd.cmd
    print(f"   Sessions: {session_dir}")

    # Resolve CLI binary to absolute path so subprocess doesn't depend on PATH lookup
    resolved = shutil.which(final_cmd[0], path=env.get("PATH"))
    if resolved:
        final_cmd[0] = resolved

    set_terminal_title(f"crew:{crew_name}")
    result = None
    try:
        if docker_cmd and docker_cmd.staging_dir:
            # Extract session transcripts after the container stops.
            # Claude writes to /home/worker/.claude/projects/-workspace/
            # Gemini writes to /home/worker/.gemini/tmp/workspace/
            extract = []
            if gemini:
                extract.append(("/home/worker/.gemini/tmp/workspace", session_dir))
            else:
                extract.append(("/home/worker/.claude/projects/-workspace", session_dir))
            result = _run_docker_container(
                docker_cmd,
                cwd=work_dir,
                env=env,
                extract_paths=extract,
            )
        else:
            result = subprocess.run(final_cmd, cwd=work_dir, env=env)
    except FileNotFoundError as exc:
        # Surface the binary the kernel actually couldn't find — not cli_tool.
        # When the agent is wrapped in docker, final_cmd[0] is "docker", so
        # printing cli_tool ("claude"/"gemini") is misleading. (task-1929bf59)
        missing = exc.filename or (final_cmd[0] if final_cmd else cli_tool)
        print(f"Error: '{missing}' command not found.", file=sys.stderr)
        if missing == "docker" or str(missing).endswith("/docker"):
            print(
                "  polecat wraps the agent in a Docker container; the docker CLI must be on PATH.\n"
                "  Verify with: which docker\n"
                "  On macOS, ensure Docker Desktop or Colima is installed and running.",
                file=sys.stderr,
            )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n\u26a0\ufe0f  Session interrupted")
    finally:
        reset_terminal_title()
        # Extract Gemini session files before cleaning up
        if tmp_gemini_home and tmp_gemini_home.exists():
            _extract_gemini_sessions(tmp_gemini_home, session_dir)
            shutil.rmtree(tmp_gemini_home)
        # Clean up temporary files created by _build_docker_cmd
        for tmp_file in tmp_files:
            if tmp_file.is_dir():
                shutil.rmtree(tmp_file, ignore_errors=True)
            else:
                tmp_file.unlink(missing_ok=True)

    print("-" * 50)
    if result is not None and result.returncode == 137:
        print(_format_oom_message(env, daemon_mem))
    print(f"\n\U0001f4cb Crew '{crew_name}' session ended.")

    # Auto-cleanup: nuke clone if no changes were made or a PR is open
    branch_name = f"crew/{crew_name}"
    auto_nuke = False
    nuke_reason = ""
    if not keep:
        if not _clone_has_changes(work_dir, branch_name):
            auto_nuke = True
            nuke_reason = "no changes made"
        elif _branch_has_open_pr(branch_name, work_dir):
            auto_nuke = True
            nuke_reason = f"PR open for {branch_name}"

    if auto_nuke:
        print(f"   {nuke_reason} — cleaning up clone.")
        try:
            manager.nuke_crew(crew_name, force=True)
            print("   Clone removed.")
        except (ValueError, RuntimeError) as e:
            print(f"   Cleanup failed: {e}", file=sys.stderr)
            print(f"   Manual cleanup: polecat nuke {crew_name}")
    else:
        print(f"   Clone preserved at: {manager.crew_dir / crew_name}")
        print(f"   To resume: polecat crew -r {crew_name}")
        print(f"   To nuke:   polecat nuke {crew_name}")


@main.command("list-crew")
@click.pass_context
def list_crew(ctx):
    """List active crew workers."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    crew = manager.list_crew()
    if not crew:
        print("No active crew workers.")
        return
    print("Active crew workers:")
    for name in crew:
        crew_path = manager.crew_dir / name
        projects = [d.name for d in crew_path.iterdir() if d.is_dir()]
        print(f"  {name}: {', '.join(projects)}")


def _fetch_github_issue(issue_ref: str, project: str | None) -> dict:
    """Fetch a GitHub issue and return a dict with task-like fields.

    Args:
        issue_ref: GitHub issue reference. Accepted formats:
            - "owner/repo#123"
            - "https://github.com/owner/repo/issues/123"
            - "#123" or "123" (requires --project to resolve the repo)
        project: Polecat project slug, used to resolve bare issue numbers.

    Returns:
        Dict with keys: id, title, body, project, repo, number, url
    """
    import json
    import re
    import subprocess

    repo = None
    number = None

    # Full URL: https://github.com/owner/repo/issues/123
    url_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_ref)
    if url_match:
        repo = url_match.group(1)
        number = url_match.group(2)

    # owner/repo#123
    if not repo:
        ref_match = re.match(r"([^/]+/[^#]+)#(\d+)", issue_ref)
        if ref_match:
            repo = ref_match.group(1)
            number = ref_match.group(2)

    # Bare #123 or 123
    if not repo:
        bare_match = re.match(r"#?(\d+)$", issue_ref)
        if bare_match:
            number = bare_match.group(1)
            if not project:
                print(
                    f"Error: Bare issue number '{issue_ref}' requires --project to resolve the repo.",
                    file=sys.stderr,
                )
                sys.exit(1)

    if number is None:
        print(f"Error: Could not parse issue reference: {issue_ref}", file=sys.stderr)
        sys.exit(1)

    gh_args = ["gh", "issue", "view", number, "--json", "title,body,number,url"]
    if repo:
        gh_args.extend(["--repo", repo])

    try:
        result = subprocess.run(gh_args, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)

    # Synthesize a safe task ID for worktree/branch naming
    repo_slug = repo.replace("/", "-") if repo else (project or "gh")
    task_id = f"gh-{repo_slug}-{number}"

    return {
        "id": task_id,
        "title": data.get("title", f"Issue #{number}"),
        "body": data.get("body", ""),
        "project": project,
        "number": int(number),
        "url": data.get("url", ""),
        "repo": repo,
    }


class _IssueTask:
    """Lightweight task-like object for GitHub issues.

    Duck-types the attributes that setup_worktree and prompt_template need.
    """

    def __init__(self, issue_data: dict):
        self.id = issue_data["id"]
        self.title = issue_data["title"]
        self.body = issue_data["body"]
        self.project = issue_data["project"]
        self.type = "task"
        self.status = None
        self.parent = None
        self.priority = None
        self.tags = []
        self.soft_depends_on = []
        self.assignee = None
        self.issue_url = issue_data.get("url", "")
        self.issue_number = issue_data.get("number")
        self.issue_repo = issue_data.get("repo")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.option("--task-id", "-t", help="Specific task ID to run (skips claim)")
@click.option("--issue", help="GitHub issue to run (owner/repo#N, URL, or #N with --project)")
@click.option("--no-finish", is_flag=True, hidden=True, help="(Deprecated, no-op)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive mode (not headless)")
@click.option(
    "--no-auto-finish",
    is_flag=True,
    help="Skip automatic 'polecat finish' on successful completion",
)
@click.option("--memory", default=None, help="Container memory limit (e.g. 4g, 2048m)")
@click.option(
    "--force",
    is_flag=True,
    help=(
        "Bypass the task status check and claim the task regardless of its "
        "current status (including done, cancelled, merge_ready, review, or "
        "PR-locked). Still claims the task to in_progress before running."
    ),
)
@click.option("--model", default=None, help="Override the model.")
@click.option(
    "--debug/--no-debug",
    "debug_flag",
    default=None,
    help="Override debug from polecat.yaml.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override an arbitrary config key.",
)
@click.pass_context
def run(
    ctx,
    project,
    caller,
    task_id,
    issue,
    no_finish,
    gemini,
    interactive,
    no_auto_finish,
    memory,
    force,
    model,
    debug_flag,
    set_overrides,
):
    """Run a polecat cycle: claim → setup → work → finish.

    Claims a task, spawns a worktree, and runs claude with the task context.
    On successful completion (exit code 0), automatically runs `polecat finish`.

    Turn budget (--max-turns semantics):
        One "turn" = one full agentic loop iteration: the model generates a
        response (potentially with many tool_use blocks) and all tool results
        are returned.  Calling 10 tools in a single response still counts as
        ONE turn.  The budget is derived from the task's effort field:

            XS  →  40 turns   (trivial, single-file edits)
            S   →  70 turns   (small, a few files)
            M   → 100 turns   (typical PR-scoped work — default)
            L   → 150 turns   (large, multi-component)
            (no effort field) → 100 turns

        Hook overhead (~2–4 turns per session for the hydration gate and
        enforcer compliance check) counts against the budget.

        When the budget is exhausted polecat emits a diagnostic showing the
        last observed tool call so supervisors can assess over-exploration
        without reading the full transcript.

    Examples:
        polecat run -p aops              # Run next ready task from aops project
        polecat run -t task-123          # Run specific task
        polecat run --issue owner/repo#42  # Run a GitHub issue
        polecat run --issue 42 -p writing  # Run issue #42 from writing project repo
        polecat run -p aops --no-auto-finish  # Skip auto-finish on success
    """
    import signal as _signal
    import subprocess

    # Install a SIGTERM handler so transcript-extraction `finally` blocks fire
    # on container stop (task-11de7b21). Python's default SIGTERM action
    # terminates the process immediately, skipping `finally` blocks — the
    # session transcript would be lost on the remote-daemon path (where
    # extraction happens via `docker cp` in the finally) and partially lost
    # on the local-daemon path (cleanup of staging dirs / tmp files skipped).
    #
    # We convert SIGTERM into KeyboardInterrupt, which the existing
    # ``except KeyboardInterrupt`` handler below already absorbs and which
    # lets ``subprocess.run``'s context-manager teardown fire (killing the
    # docker subprocess) before the `finally` runs extraction.
    def _polecat_sigterm_handler(signum, frame):
        print(
            "\n⚠️  Received SIGTERM — extracting transcript and exiting...",
            file=sys.stderr,
        )
        raise KeyboardInterrupt

    try:
        _signal.signal(_signal.SIGTERM, _polecat_sigterm_handler)
    except (ValueError, OSError):
        # signal.signal() only works on the main thread; in unusual
        # invocation contexts (e.g. embedded in a worker) we silently
        # skip the handler rather than crash.
        pass

    _require_pkb_url_or_exit()
    _bootstrap_or_exit()

    if issue and task_id:
        print("Error: --issue and --task-id are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Step 1: Get/claim task (or fetch GitHub issue)
    is_issue = False
    was_claimed = False
    if issue:
        # GitHub issue path — fetch metadata, create lightweight task object
        print(f"Fetching GitHub issue: {issue}...")
        issue_data = _fetch_github_issue(issue, project)
        task = _IssueTask(issue_data)
        is_issue = True
    elif task_id:
        # Validate task ID before any operations
        try:
            validate_task_id_or_raise(task_id)
        except TaskIDValidationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        task = manager.get_task(task_id)
        if not task:
            print(f"Task not found: {task_id}", file=sys.stderr)
            sys.exit(1)

        # Normalize status to a plain string for uniform handling
        status_str = task.status.value if hasattr(task.status, "value") else str(task.status or "")

        if not force:
            _DONE_STATUSES = ("done", "cancelled")
            _LOCKED_STATUSES = ("merge_ready", "review")

            if status_str in _DONE_STATUSES:
                print(f"✅ Task {task_id} is already '{status_str}'.")
                sys.exit(0)

            # Refuse to re-dispatch tasks locked by an open PR (not yet merged).
            pr_ref = task.pr_url or (f"#{task.pr}" if task.pr else None)
            if status_str in _LOCKED_STATUSES or pr_ref:
                print(
                    f"🔒 Task {task_id} is locked "
                    f"(status: {status_str}"
                    + (f", PR: {pr_ref}" if pr_ref else "")
                    + "). A PR already exists for this task — refusing to re-dispatch.",
                    file=sys.stderr,
                )
                sys.exit(2)  # Exit 2 = locked; distinct from exit 1 (error) / exit 3 (empty queue)
        else:
            print(f"⚠️  --force: bypassing status check for {task_id} (status: {status_str}).")

        # Canonical PKB statuses agents may claim from. See
        # aops-core/skills/remember/references/TAXONOMY.md. NEVER add the
        # legacy "active" — PKB rejects it as Invalid status.
        # With --force, claim from any non-terminal status.
        _CLAIMABLE_STATUSES = ("ready", "queued") if not force else None
        if _CLAIMABLE_STATUSES is None or status_str in _CLAIMABLE_STATUSES:
            # Capture prior status so a downstream failure can restore
            # exactly what we found, rather than guessing a default.
            prior_status = status_str
            try:
                manager.update_task(task_id, status="in_progress", assignee=caller)
                was_claimed = True
            except (TimeoutError, urllib.error.URLError) as e:
                # Handle timeout during direct claim
                print(f"⚠️  PKB claim timeout for {task_id}: {e}", file=sys.stderr)
                print("   Verifying if claim succeeded despite timeout...", file=sys.stderr)
                try:
                    verified = manager.get_task(task_id)
                    if (
                        verified
                        and verified.status == "in_progress"
                        and verified.assignee == caller
                    ):
                        print("   ✅ Verified: claim succeeded. Proceeding.", file=sys.stderr)
                        task = verified
                        was_claimed = True
                    else:
                        raise
                except Exception:
                    print(f"   Task {task_id} may be stranded in_progress.", file=sys.stderr)
                    print(
                        f"   Recovery: polecat reset-stalled --hours 0 --project {task.project or 'aops'}",
                        file=sys.stderr,
                    )
                    raise
            task.status = "in_progress"
            task.assignee = caller
            # Annotate prior status for rollback (mirrors what
            # PolecatManager.claim_next_task does for the queue path).
            try:
                task._prior_status = prior_status
            except AttributeError:
                pass
    else:
        from polecat.claim import claim_next_ready

        task = claim_next_ready(manager, caller, project)
        was_claimed = True

    # CLI --project/-p overrides task.project (e.g. task has no project set).
    # Resolve aliases / repo names to the canonical slug so downstream lookups
    # (mirror path, default_branch) hit the registry.
    if project:
        try:
            task.project = manager.resolve_project_alias(project)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if is_issue:
        print(f"🎯 Issue: {task.title} ({getattr(task, 'issue_url', '') or task.id})")
    else:
        print(f"🎯 Task: {task.title} ({task.id})")

    # Lifecycle: record run-started so a crash before worktree setup is visible.
    _write_lifecycle_event(
        task_id=task.id,
        phase="started",
        home_dir=manager.home_dir,
        project=project or task.project or "",
        caller=caller,
        agent="gemini" if gemini else "claude",
        is_issue=is_issue,
        force=bool(force),
    )

    # Step 2: Setup worktree
    try:
        worktree_path = manager.setup_worktree(task)
        print(f"📁 Worktree: {worktree_path}")
        _write_lifecycle_event(
            task_id=task.id,
            phase="worktree_ready",
            home_dir=manager.home_dir,
            path=str(worktree_path),
        )
    except Exception as e:
        _write_lifecycle_event(
            task_id=task.id,
            phase="failed",
            home_dir=manager.home_dir,
            error=str(e),
            failed_in="worktree_setup",
        )
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        if was_claimed and task and not is_issue:
            rollback_status = _rollback_status_for(task)
            print(
                f"Reverting task {task.id} to {rollback_status}...",
                file=sys.stderr,
            )
            try:
                manager.update_task(task.id, status=rollback_status, assignee=None)
            except Exception as re:
                print(f"Failed to revert task {task.id}: {re}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Build prompt from task context (self-contained, no /pull needed)
    from polecat.prompt_template import build_polecat_prompt

    # Build task body — for issues, prepend the issue URL for reference
    task_body = task.body or ""
    issue_url = getattr(task, "issue_url", "")
    if is_issue and issue_url:
        task_body = f"**GitHub Issue**: {issue_url}\n\n{task_body}"

    # Resolve soft dependencies for context injection (local tasks only)
    soft_deps = None
    if not is_issue and task.soft_depends_on:
        soft_deps = []
        for dep_id in task.soft_depends_on:
            dep_task = manager.get_task(dep_id)
            if dep_task:
                soft_deps.append(
                    {
                        "id": dep_task.id,
                        "title": dep_task.title,
                        "status": dep_task.status.value
                        if hasattr(dep_task.status, "value")
                        else str(dep_task.status),
                        "body": dep_task.body or "",
                    }
                )

    prompt = build_polecat_prompt(
        task_id=task.id,
        task_title=task.title,
        task_type=task.type.value if hasattr(task.type, "value") else str(task.type),  # type: ignore[reportAttributeAccessIssue]
        task_project=project or task.project or "",
        task_body=task_body,
        task_meta={
            "parent": task.parent,
            "priority": task.priority,
            "tags": task.tags,
            "status": task.status,
            "pr_url": getattr(task, "pr_url", None),
            "pr": getattr(task, "pr", None),
        },
        soft_deps=soft_deps,
        is_issue=is_issue,
    )

    # Step 4: Run agent in the worktree
    # Choose CLI tool based on --gemini flag
    cli_tool = "gemini" if gemini else "claude"
    mode = "interactive" if interactive else "headless"
    cfg, session_cfg = _resolve_session_config(
        "run",
        client=cli_tool,
        model=model,
        debug=debug_flag,
        set_overrides=set_overrides,
    )
    print(f"\n🤖 Starting {cli_tool} agent ({mode})...")
    print(
        "   Mode: "
        f"hooks_enabled={session_cfg.hooks_enabled}, "
        f"model={session_cfg.model_for(cli_tool)}, debug={session_cfg.debug}"
    )
    print(f"   Config: {cfg.source_path}")
    print("-" * 50)

    # Build command - gemini and claude have different CLI interfaces
    if gemini:
        # Gemini CLI — run inside our Docker container (not --sandbox, which
        # uses bind mounts that fail on WSL2/Docker Desktop).
        #
        # Sandbox allowlist (#522): Gemini's workspace sandbox blocks reads of
        # files outside /workspace, including the aops-core extension's
        # GEMINI.md and sibling skills. Explicitly widen the allowlist to the
        # extension directory so read_file / activate_skill work.  Keep this
        # list narrow — DO NOT blanket-widen; each entry is a specific dir
        # the agent needs to reach.
        cmd = [
            "gemini",
            "--approval-mode",
            "yolo",
            "--include-directories",
            "/home/worker/.gemini/extensions/aops-core",
            "--model",
            session_cfg.gemini_model,
        ]

        if interactive:
            # -i starts interactive mode with initial prompt
            cmd.extend(["-i", prompt])
        else:
            # Headless mode with auto-approve
            cmd.extend(["-p", prompt])
    else:
        # Claude CLI. Autonomous polecat workers run bypass-permissions in both
        # hooks-on and hooks-off cases.
        #
        # We deliberately do NOT use --permission-mode=plan here, even when
        # hooks are enabled. In headless ``-p`` mode, claude calls
        # ``ExitPlanMode`` after writing the plan and then exits — it never
        # proceeds to execute. The hook stack (router + gates inside the
        # container) is the actual policy boundary; plan mode would only
        # add value if a human were present to confirm the plan, which by
        # definition isn't the case for an autonomous polecat run.
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--setting-sources=user,project",
            "--model",
            session_cfg.claude_model,
        ]

        if interactive:
            # Interactive: just append the prompt as positional arg
            cmd.append(prompt)
        else:
            # Headless: use -p for print mode
            cmd.extend(["-p", prompt, "--max-turns", _compute_max_turns(task)])

    # Set session type environment variable for hooks to detect
    # Use sanitized env: SSH stripped, git auth set to bot token only
    env = _make_worker_env(interactive=interactive, work_dir=worktree_path)
    env["POLECAT_SESSION_TYPE"] = "polecat"
    env["AOPS_TASK_ID"] = task.id
    if session_cfg.debug:
        env["DEBUG_HOOKS"] = "1"

    # Resolve container memory limit and check daemon memory
    memory_limit, daemon_mem = _init_container_memory(memory, manager, env)

    tmp_gemini_home = None
    tmp_files: list[Path] = []
    # Compute session directory for transcript persistence.
    project_slug = project or task.project or worktree_path.name
    run_session_dir = _get_sessions_base() / "polecats" / task.id / project_slug
    env["AOPS_SESSION_STATE_DIR"] = str(run_session_dir)

    if gemini:
        # Replicate Gemini authentication — creates a temp dir with .gemini/ auth files.
        tmp_gemini_home = _replicate_gemini_auth(
            env, work_dir=worktree_path, hooks_enabled=session_cfg.hooks_enabled
        )
        if tmp_gemini_home:
            print(f"   Auth: Replicated to {tmp_gemini_home}")

        # See parallel block in the crew path: override the host tmp path
        # that _replicate_gemini_auth set so gemini-in-container reads from
        # /home/worker/.gemini/ where docker cp stages the auth files.
        env["GEMINI_CLI_HOME"] = "/home/worker"

        # Provide a stable Gemini session ID based on the task ID hash.
        # This ensures the task's 8-char hash (e.g. 33dee777) appears in the
        # session-*.json filename.
        task_hash = derive_polecat_session_id(task.id)
        gemini_session_id = f"{task_hash}-gemini"
        env["GEMINI_SESSION_ID"] = gemini_session_id
        env["AOPS_SESSION_ID"] = gemini_session_id

        # Wrap Gemini in our Docker container (same as Claude path).
        docker_cmd = _build_docker_cmd(
            "gemini",
            worktree_path,
            env,
            cmd,
            is_interactive=interactive,
            tmp_files=tmp_files,
            session_dir=run_session_dir,
            memory_limit=memory_limit,
            cfg=cfg,
            hooks_enabled=session_cfg.hooks_enabled,
            project_slug=project_slug,
            manager=manager,
        )

        # Copy replicated .gemini/ auth into staging_dir so docker cp injects
        # it into /home/worker/.gemini/ via the entrypoint.
        if tmp_gemini_home and docker_cmd.staging_dir:
            src_gemini = tmp_gemini_home / ".gemini"
            if src_gemini.is_dir():
                dst_gemini = docker_cmd.staging_dir / ".gemini"
                if dst_gemini.exists():
                    shutil.rmtree(dst_gemini)
                shutil.copytree(src_gemini, dst_gemini)

        final_cmd = docker_cmd.cmd
    else:
        # Claude Code: manually wrap in docker container
        docker_cmd = _build_docker_cmd(
            cli_tool,
            worktree_path,
            env,
            cmd,
            is_interactive=interactive,
            tmp_files=tmp_files,
            session_dir=run_session_dir,
            memory_limit=memory_limit,
            cfg=cfg,
            hooks_enabled=session_cfg.hooks_enabled,
            project_slug=project_slug,
            manager=manager,
        )
        final_cmd = docker_cmd.cmd
    print(f"   Sessions: {run_session_dir}")

    # Resolve CLI binary to absolute path so subprocess doesn't depend on PATH lookup
    resolved = shutil.which(final_cmd[0], path=env.get("PATH"))
    if resolved:
        final_cmd[0] = resolved

    # Compute extract_paths for session transcript persistence.
    # Claude writes to /home/worker/.claude/projects/-workspace/
    # Gemini writes to /home/worker/.gemini/tmp/workspace/
    if gemini:
        _extract = [("/home/worker/.gemini/tmp/workspace", run_session_dir)]
    else:
        _extract = [("/home/worker/.claude/projects/-workspace", run_session_dir)]

    if interactive:
        set_terminal_title(f"polecat:{task.id}")

    # Lifecycle: about to launch the agent process. If the agent crashes, the
    # final phase recorded will be agent_started → supervisor knows we got
    # past worktree setup and the failure was inside the agent run.
    _write_lifecycle_event(
        task_id=task.id,
        phase="agent_started",
        home_dir=manager.home_dir,
        cli_tool=cli_tool,
        mode="interactive" if interactive else "headless",
        session_dir=str(run_session_dir),
    )

    try:
        if interactive:
            # In interactive mode, we MUST NOT capture output or it will hang
            # and we want the user to see/interact with the CLI
            if docker_cmd and docker_cmd.staging_dir:
                result = _run_docker_container(
                    docker_cmd,
                    cwd=worktree_path,
                    env=env,
                    extract_paths=_extract,
                    gemini=gemini,
                    task_id=task.id,
                )
            else:
                result = subprocess.run(
                    final_cmd,
                    cwd=worktree_path,
                    env=env,
                )
            exit_code = result.returncode
            # No transcript to analyze in interactive mode (currently)
        else:
            if docker_cmd and docker_cmd.staging_dir:
                result = _run_docker_container(
                    docker_cmd,
                    cwd=worktree_path,
                    env=env,
                    capture_output=True,
                    text=True,
                    extract_paths=_extract,
                    gemini=gemini,
                    task_id=task.id,
                )
            else:
                result = subprocess.run(
                    final_cmd,
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    env=env,
                )
            exit_code = result.returncode
            # Display agent output after run
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            # Save transcript to $POLECAT_HOME/polecats/<task-id>.jsonl
            try:
                real_transcript = _find_real_transcript(run_session_dir)
                transcript_path = save_worker_transcript(
                    task_id=task.id,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=exit_code,
                    agent_type=cli_tool,
                    home_dir=manager.home_dir,
                    real_transcript=real_transcript,
                )
                if real_transcript:
                    print(f"📝 Transcript: {real_transcript}")
                else:
                    print(f"📝 Transcript stub: {transcript_path}")
            except OSError as e:
                print(f"⚠️  Warning: Failed to save transcript: {e}", file=sys.stderr)

            # Detect turn-budget exhaustion and emit supervisor-friendly diagnostic
            _emit_budget_hit_diagnostic(result.stdout, result.stderr, _compute_max_turns(task))

            # Analyze the transcript for failures
            analyze_func = getattr(manager, "analyze_transcript", None)
            if analyze_func:
                analyze_func(task, result.stdout, result.stderr)

    except FileNotFoundError as exc:
        # Surface the binary the kernel actually couldn't find — not cli_tool.
        # When the agent is wrapped in docker, final_cmd[0] is "docker", so
        # printing cli_tool ("claude"/"gemini") is misleading. (task-1929bf59)
        missing = exc.filename or (final_cmd[0] if final_cmd else cli_tool)
        _write_lifecycle_event(
            task_id=task.id,
            phase="failed",
            home_dir=manager.home_dir,
            error=f"{missing} command not found",
            failed_in="agent_launch",
        )
        print(f"Error: '{missing}' command not found.", file=sys.stderr)
        if missing == "docker" or str(missing).endswith("/docker"):
            print(
                "  polecat wraps the agent in a Docker container; the docker CLI must be on PATH.\n"
                "  Verify with: which docker\n"
                "  On macOS, ensure Docker Desktop or Colima is installed and running.",
                file=sys.stderr,
            )
        sys.exit(1)
    except KeyboardInterrupt:
        _write_lifecycle_event(
            task_id=task.id,
            phase="failed",
            home_dir=manager.home_dir,
            error="KeyboardInterrupt",
            failed_in="agent_run",
        )
        print("\n\n⚠️  Agent interrupted by user")
        exit_code = 130
    finally:
        if interactive:
            reset_terminal_title()
        # Extract Gemini session files before cleaning up
        if tmp_gemini_home and tmp_gemini_home.exists():
            _extract_gemini_sessions(tmp_gemini_home, run_session_dir)
            shutil.rmtree(tmp_gemini_home)
        # Clean up temporary files created by _build_docker_cmd
        for tmp_file in tmp_files:
            if tmp_file.is_dir():
                shutil.rmtree(tmp_file, ignore_errors=True)
            else:
                tmp_file.unlink(missing_ok=True)

    print("-" * 50)

    # Step 5: Auto-finish on success (unless disabled)
    if exit_code == 0:
        print("\n✅ Agent completed successfully.")

        # Check for completion signals in stdout/stderr (e.g. fix already deployed)
        # This allows us to auto-finish even if no git changes were detected.
        auto_force_done = False
        completion_signals = [
            "verified complete",
            "fix already deployed",
            "no changes needed",
            "work already done",
            "verified the change is present",
            "verified the fix is already there",
            "task already completed",
            "already been completed",
        ]

        # Use result.stdout if it exists (not captured in interactive mode)
        agent_output = ""
        try:
            if not interactive and result.stdout:
                stdout = (
                    result.stdout
                    if isinstance(result.stdout, str)
                    else result.stdout.decode("utf-8", errors="replace")
                )
                agent_output += stdout
            if not interactive and result.stderr:
                stderr = (
                    result.stderr
                    if isinstance(result.stderr, str)
                    else result.stderr.decode("utf-8", errors="replace")
                )
                agent_output += stderr
        except (AttributeError, NameError):
            pass

        if agent_output:
            for signal in completion_signals:
                if signal.lower() in agent_output.lower():
                    print(f"✨ Found completion signal: '{signal}'")
                    auto_force_done = True
                    break

        if not no_auto_finish:
            print("🔄 Running auto-finish...")
            # Change to worktree directory and invoke finish directly
            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_path)
                # Pass force_done if we detected a completion signal.
                # ``finish`` was extracted to polecat/finalize.py — import the
                # underlying Click command lazily here (the registration alias
                # ``_finish_cmd`` is added at module bottom, after this fn).
                try:
                    from polecat.finalize import finish_cmd as _finish_cmd
                except ImportError:
                    from finalize import finish_cmd as _finish_cmd  # type: ignore[no-redef]
                ctx.invoke(
                    _finish_cmd,
                    no_push=False,
                    do_nuke=True,
                    force_done=auto_force_done,
                    project=project,
                )
                print("✅ Auto-finish completed.")
            except SystemExit as e:
                if e.code != 0:
                    print("⚠️  Auto-finish failed.")
                    print(f"   You can retry manually: cd {worktree_path} && polecat finish")
            except Exception as e:
                print(f"⚠️  Auto-finish failed: {e}")
                print(f"   You can retry manually: cd {worktree_path} && polecat finish")
            finally:
                os.chdir(original_cwd)
        else:
            print("📝 Auto-finish disabled. Run `polecat finish` when ready.")
            print(f"   Worktree: {worktree_path}")
    else:
        worktree_removed = False
        if exit_code == 137:
            if getattr(result, "watchdog_terminated", False):
                print(_format_watchdog_terminated_message(task_id=task.id))
                if not no_auto_finish:
                    try:
                        from polecat.pkb_bridge import get_task as pkb_get_task

                        current_task = pkb_get_task(task.id)
                        current_status = getattr(current_task, "status", None)
                        if current_status in TERMINAL_PKB_STATUSES or current_status == "review":
                            print(
                                f"🔄 Task {task.id} is terminal ({current_status}). Nuking orphaned worktree..."
                            )
                            original_cwd = os.getcwd()
                            # git worktree remove fails if cwd is inside the tree being removed
                            os.chdir(Path.home())
                            try:
                                manager.nuke_worktree(task.id, force=True, allow_unpushed=False)
                                print("✅ Orphaned worktree removed.")
                                worktree_removed = True
                            except Exception as e:
                                print(f"⚠️  Could not GC worktree: {e}")
                            finally:
                                os.chdir(original_cwd)
                    except Exception as e:
                        print(f"⚠️  Failed to check task status for worktree GC: {e}")
            else:
                print(_format_oom_message(env, daemon_mem))
        else:
            print(f"\n⚠️  Agent exited with code {exit_code}. Skipping auto-finish.")

        if not worktree_removed:
            print(f"   Worktree: {worktree_path}")
            print(f"   To finish manually: cd {worktree_path} && polecat finish")


try:
    from polecat.diagnostics import analyze as _analyze_cmd
    from polecat.diagnostics import reset_stalled as _reset_stalled_cmd
except ImportError:
    from diagnostics import analyze as _analyze_cmd  # type: ignore[no-redef]
    from diagnostics import reset_stalled as _reset_stalled_cmd  # type: ignore[no-redef]

main.add_command(_analyze_cmd)
main.add_command(_reset_stalled_cmd)


try:
    from polecat.watch import watch as _watch_cmd
except ImportError:
    from watch import watch as _watch_cmd  # type: ignore[no-redef]

main.add_command(_watch_cmd)


@main.command()
@click.option("--claude", "-c", default=0, help="Number of Claude workers")
@click.option("--gemini", "-g", default=0, help="Number of Gemini workers")
@click.option("--project", "-p", help="Project to focus on (default: all)")
@click.option("--caller", default="polecat", help="Identity claiming the tasks (default: bot)")
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.pass_context
def swarm(ctx, claude, gemini, project, caller, dry_run):
    """Run a swarm of parallel Polecat workers.

    Spawns N claude and M gemini workers, managing CPU affinity.
    Restarting workers on success, stopping on failure.
    """
    _bootstrap_or_exit()

    try:
        from swarm import run_swarm
    except ImportError:
        # Fallback for when running as script in same dir
        try:
            from .swarm import run_swarm
        except ImportError:
            # Last ditch for direct execution
            try:
                import swarm as swarm_module

                run_swarm = swarm_module.run_swarm
            except ImportError:
                print("Error: Could not import swarm module.", file=sys.stderr)
                sys.exit(1)

    home = ctx.obj.get("home")
    run_swarm(claude, gemini, project, caller, dry_run, str(home) if home else None)


try:
    from polecat.summary import summary as _summary_cmd
except ImportError:
    from summary import summary as _summary_cmd  # type: ignore[no-redef]

main.add_command(_summary_cmd)


# Register commands extracted into sibling modules (Polecat v2 module split).
try:
    from polecat.finalize import finish_cmd as _finish_cmd
except ImportError:
    from finalize import finish_cmd as _finish_cmd  # type: ignore[no-redef]

main.add_command(_finish_cmd)


if __name__ == "__main__":
    main()
