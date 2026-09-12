"""aops hook handlers."""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import socket
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, load_message_pair, refuse, warn

log = logging.getLogger("aops.handlers")

try:
    import claude_code_tracer
except ImportError as exc:
    claude_code_tracer = None
    log.warning(
        "claude_code_tracer did not import (%s) — OTel tracing is disabled for every hook",
        exc,
    )

try:
    import agy_tracer
except ImportError as exc:
    agy_tracer = None
    log.warning("agy_tracer did not import (%s)", exc)

Handler = Callable[[HookContext], Result | None]

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


def _scrub(value: object) -> str:
    """Neutralise characters that let a client-supplied value forge a field."""
    return " ".join(str(value).split()).replace("|", "")


def _get_plugin_version_metadata(ctx: HookContext) -> str | None:
    # 1. Check direct environment variable
    if os.environ.get("AOPS_IMAGE_PLUGINS_VERSION"):
        return os.environ["AOPS_IMAGE_PLUGINS_VERSION"]
    # 2. Check ctx.raw
    if ctx.raw.get("plugins"):
        return str(ctx.raw["plugins"])
    if ctx.raw.get("plugins_version"):
        return str(ctx.raw["plugins_version"])
    # 3. Check /home/worker/.aops-image-metadata.json
    metadata_path = Path("/home/worker/.aops-image-metadata.json")
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            version = data.get("aops_version") or "0.9.1"
            dist_source = data.get("dist_source") or "local"
            return f"{version} ({dist_source}:match)"
        except Exception:
            pass
    return None


def _format_session_metadata(ctx: HookContext) -> str:
    # ``%z`` (``+1000``), never ``%Z``. The abbreviation is not unique — ``IST``
    # is both Asia/Kolkata (+05:30) and Europe/Dublin (+01:00) — so a reader
    # cannot recover an offset from it, which is the whole point of naming the
    # zone. ``astimezone()`` guarantees an aware datetime, so ``%z`` is never empty.
    now = datetime.now().astimezone()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S %z")

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    session_id = ctx.session_id or ctx.raw.get("session_id") or ctx.raw.get("conversationId") or ""
    cwd = ctx.cwd or ctx.raw.get("cwd") or ""

    plugins_meta = _get_plugin_version_metadata(ctx)

    pkb_version = os.environ.get("PKB_VERSION") or ctx.raw.get("pkb_version") or "unknown"

    parts = [
        f"session: {_scrub(session_id)}" if session_id else "session: unknown",
        f"time: {time_str}",
        f"host: {_scrub(hostname)}" if hostname else "host: unknown",
        f"cwd: {_scrub(cwd)}" if cwd else "cwd: unknown",
    ]
    if plugins_meta:
        parts.append(f"plugins: {_scrub(plugins_meta)}")
    parts.append(f"pkb: {_scrub(pkb_version)}")

    otel_endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("BETA_TRACING_ENDPOINT")
        or os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")
    )
    if otel_endpoint:
        service_name = os.environ.get("OTEL_SERVICE_NAME") or "unknown"
        parts.append(f"tracing: {_scrub(otel_endpoint)} (service: {_scrub(service_name)})")
    else:
        parts.append("tracing: unconfigured")

    return " | ".join(parts)


def _get_injected_files(ctx: HookContext) -> list[str]:
    injected_str = os.environ.get("AOPS_INJECT_FILES", "").strip()
    if not injected_str:
        return []

    lines = []
    base_dir = ctx.cwd
    for p_str in injected_str.split(","):
        p_str = p_str.strip()
        if not p_str:
            continue
        p = Path(p_str)
        if not p.is_absolute():
            p = base_dir / p

        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                lines.append(f"--- START: {p_str} ---\n{content}\n--- END: {p_str} ---")
            except Exception as e:
                lines.append(f"--- ERROR reading {p_str}: {e} ---")
        else:
            lines.append(f"--- MISSING: {p_str} ---")
    return lines


def _read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        k, sep, v = line.partition("=")
        if not sep:
            continue
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[k] = v
    return out


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"export {k}={shlex.quote(v)}" for k, v in sorted(values.items())]
    content = "\n".join(lines) + ("\n" if lines else "")
    path.write_text(content, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _isolate_credentials(ctx: HookContext) -> bool:
    env_file_str = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file_str:
        return False
    env_file = Path(env_file_str)

    existing = _read_env_file(env_file)
    moved: dict[str, str] = {}

    for var in _BASIC_VARS:
        val = os.environ.get(var)
        if val is not None:
            moved[var] = val

    if not moved:
        return False

    existing.update(moved)
    _write_env_file(env_file, existing)

    for var in moved:
        os.environ.pop(var, None)

    return True


def _check_stale_baked_plugins() -> str | None:
    metadata_path = Path("/home/worker/.aops-image-metadata.json")
    if not metadata_path.exists():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        if data.get("dist_source") == "stale":
            built = data.get("built_at", "unknown")
            host_commit = data.get("host_commit", "unknown")
            built_commit = data.get("built_commit", "unknown")
            return (
                f"[WARNING: STALE BAKED PLUGINS DETECTED]\n"
                f"The plugins baked into this container image do not match the current commit on the host.\n"
                f"Image built at: {built}\n"
                f"Baked commit:   {built_commit}\n"
                f"Host commit:    {host_commit}\n"
                f"Behavior of skills/hooks may diverge from host edits. Run 'polecat build' to refresh."
            )
    except Exception:
        pass
    return None


def _record_session_own_branch(ctx: HookContext) -> None:
    """Best-effort: remember this session's branch at container start.

    `AOPS_SESSION_STATE_DIR` is set once per container by the polecat CLI
    (lib/polecat/cli.py) and is not something a running session can
    reassign for a later tool call -- each Bash invocation is a fresh
    subprocess with no carried shell state, so a session cannot `export`
    its way out of this. Writing the branch here, at session start, before
    any adversarial cwd-switching could happen, gives `guard_own_pr_ready`
    a session-identity-keyed fact to check in addition to the current
    cwd's branch -- closing the "second clone at a different path, same
    session" bypass (aops_3c133222 dispatch log, 2026-09-12 06:20 UTC).
    Never raises: a session-start hook must not fail the session over this.
    """
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if not state_dir:
        return
    branch = _own_git_branch(ctx.cwd)
    if not branch:
        return
    try:
        Path(state_dir).mkdir(parents=True, exist_ok=True)
        (Path(state_dir) / _OWN_BRANCH_STATE_FILENAME).write_text(branch)
    except OSError:
        pass


def _recorded_session_own_branch() -> str | None:
    """The branch `_record_session_own_branch` saved for this container, if any."""
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if not state_dir:
        return None
    try:
        text = (Path(state_dir) / _OWN_BRANCH_STATE_FILENAME).read_text()
    except OSError:
        return None
    return text.strip() or None


def session_start(ctx: HookContext) -> Result | None:
    """Handle SessionStart for Claude Code and SessionStart for agy."""
    _record_session_own_branch(ctx)
    metadata = _format_session_metadata(ctx)
    parts = ["aops hook: Session started.", metadata]
    user_parts = [metadata]

    stale_warning = os.environ.get("AOPS_IMAGE_STALENESS_WARNING") or ctx.raw.get(
        "image_staleness_warning"
    )
    if not stale_warning and (
        os.environ.get("AOPS_IMAGE_STALE") == "1" or ctx.raw.get("image_stale")
    ):
        stale_warning = (
            "[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]\n"
            "Container plugin payload lags workspace under test.\n"
            "Any skill, hook, or MCP behavior verified in this session reflects the BAKED payload, NOT workspace edits."
        )

    if stale_warning:
        parts.append(stale_warning)
        user_parts.append(stale_warning)

    if _isolate_credentials(ctx):
        parts.append("Credentials have been isolated in CLAUDE_ENV_FILE.")
        user_parts.insert(0, "Credentials isolated.")

    injected = _get_injected_files(ctx)
    if injected:
        files_str = "Injected context files:\n" + "\n".join(injected)
        parts.append(files_str)
        user_parts.append(files_str)

    return warn("\n\n".join(parts), "\n\n".join(user_parts))


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind the dispatcher that a subagent's report is not evidence."""
    # Only fire on supervisor profiles
    if ctx.agent_type in ("aops:ida", "aops:james", "orchestrate:james"):
        if any(call.get("tool_name") == "Agent" for call in ctx.tool_calls):
            return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))

    return None


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims."""
    # Do not fire on supervisor profiles (Ida and James)
    # <!-- NS: fix the magic values here -- we have a constant somewhere else -->
    if ctx.agent_type in (
        "aops:ida",
        "aops:james",
        "orchestrate:james",
        "pkb:ida",
    ) or (ctx.agent_type and ctx.agent_type.endswith((":ida", ":james"))):
        return None

    if ctx.raw.get("background_tasks"):
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing."""
    # Only fire on Ida
    if ctx.agent_type == "aops:ida":
        if ctx.raw.get("background_tasks"):
            return None
        return warn(*load_message_pair(ctx.hooks_dir, "quiet"))

    return None


def _prepare_tracer_data(ctx: HookContext) -> dict[str, Any]:
    """Extract and normalize payload dictionary for claude_code_tracer."""
    data = dict(ctx.raw)
    if ctx.session_id:
        data.setdefault("session_id", ctx.session_id)
    if ctx.tool:
        data.setdefault("tool_name", ctx.tool)
    if "toolName" in data and "tool_name" not in data:
        data["tool_name"] = data["toolName"]
    if "toolInput" in data and "tool_input" not in data:
        data["tool_input"] = data["toolInput"]
    if "toolResponse" in data and "tool_response" not in data:
        data["tool_response"] = data["toolResponse"]
    return data


def user_prompt_submit(ctx: HookContext) -> Result | None:
    """Tracer hook handler for canonical UserPromptSubmit, Claude Code side."""
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_user_prompt_submit(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer user_prompt_submit failed: %s", exc)
    return None


def pre_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer pre_tool failed: %s", exc)
    return None


def post_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool failed: %s", exc)
    return None


def post_tool_failure(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool_failure(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool_failure failed: %s", exc)
    return None


def stop(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer stop failed: %s", exc)
    return None


def agy_user_prompt_submit(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_pre_invocation(data, config)
    except Exception as exc:
        log.warning("agy_user_prompt_submit tracer failed: %s", exc)
    return None


def agy_pre_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("agy_pre_tool tracer failed: %s", exc)
    return None


def agy_post_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("agy_post_tool tracer failed: %s", exc)
    return None


def agy_stop(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("agy_stop tracer failed: %s", exc)
    return None


_SHELL_TOOL_NAMES = frozenset({"Bash", "run_command"})
_PR_READY_RE = re.compile(r"\bgh\s+pr\s+ready\b")
_GRAPHQL_READY_RE = re.compile(r"markPullRequestReadyForReview")
_TICKET = "aops_3c133222"
_OWN_BRANCH_STATE_FILENAME = "own_pr_ready_guard_branch.txt"


def _own_git_branch(cwd: str) -> str | None:
    """This session's checked-out branch, or None if it cannot be read.

    A polecat run's clone is checked out to one branch for the life of the
    container (specs/polecat/polecat-system.md); that branch is the head
    branch of any PR the run itself opens.
    """
    if not cwd:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _pr_head_branch(ref: str, cwd: str) -> str | None:
    """Resolve a PR number or URL to its head branch via `gh pr view`.

    None on any failure (gh unavailable, network, bad ref, timeout) — callers
    treat "could not verify" as a reason to refuse, not to allow.
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", ref, "--json", "headRefName", "--jq", ".headRefName"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=cwd or None,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _pr_ready_ref(command: str) -> tuple[str | None, bool]:
    """Parse `gh ... pr ready [<ref>] [--undo]`. Returns (ref, is_undo)."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    is_undo = "--undo" in tokens
    ref = None
    seen_ready = False
    for tok in tokens:
        if seen_ready:
            if tok.startswith("-"):
                continue
            ref = tok
            break
        if tok == "ready":
            seen_ready = True
    return ref, is_undo


def guard_own_pr_ready(ctx: HookContext) -> Result | None:
    """Refuse a run marking its own PR ready for review.

    "Independent review = a different run" was dispatch discipline only --
    nothing stopped the run that opened a PR from also flipping it ready
    itself (observed on academicOps#2653, ruled on in aops_d8085e5b). Ida's
    ruling was a worker-side mechanical block, not a second bot identity or a
    GitHub review-approval requirement (`aops_3c133222`).

    The mechanical fact this checks: a polecat run's clone stays on one
    branch for its whole life, and that branch is the head branch of any PR
    it opens itself. So a `gh pr ready` (or the raw GraphQL mutation) whose
    target PR's head branch is this session's own current branch is this
    session marking its own PR ready -- refused. A different branch (a
    review run's own clone, checked out at the base ref, never the original
    PR's branch) is a different PR or a genuinely independent one -- allowed.

    "This session's own branch" is not just `ctx.cwd`'s current branch: a
    session that opens a second clone at a different path, on a different
    branch, is still this session (observed on #2658 -- the authoring run
    flipped its own PR ready from an "independent v0.10 clone" that was in
    fact its own second checkout). `_recorded_session_own_branch` reads a
    branch this same container recorded at SessionStart, before any
    cwd-switching -- keyed by session identity (`AOPS_SESSION_STATE_DIR`,
    set once per container, not reassignable from inside a later tool
    call), not by whichever directory this particular command happens to
    run in. Both sources are checked; either matching is a refusal.
    """
    if ctx.tool not in _SHELL_TOOL_NAMES:
        return None
    command = ctx.command or ""
    if not command:
        return None

    if _GRAPHQL_READY_RE.search(command):
        return refuse(
            f"refused ({_TICKET}): this command invokes the ready-for-review "
            "GraphQL mutation directly, which this hook cannot verify "
            "ownership for. Use `gh pr ready <number>` instead -- it is "
            "checked for self-review; the raw API call is refused outright."
        )

    if not _PR_READY_RE.search(command):
        return None

    ref, is_undo = _pr_ready_ref(command)
    if is_undo:
        return None

    own_branches = {b for b in (_own_git_branch(ctx.cwd), _recorded_session_own_branch()) if b}
    if not own_branches:
        return refuse(
            f"refused ({_TICKET}): could not determine this session's own "
            "branch, so whether this PR belongs to this run cannot be "
            "verified. A run may not mark its own PR ready for review -- "
            "resolve manually or have a separate review run do this."
        )

    if ref is None or ref in own_branches:
        return refuse(
            f"refused ({_TICKET}): `gh pr ready` with no argument (or "
            f"targeting this run's own branch, {ref or next(iter(own_branches))!r}) "
            "operates on this session's own PR. A run may not mark its own "
            "PR ready for review -- a separate review run must do this."
        )

    opaque_ref = ref.lstrip("#").isdigit() or "github.com" in ref
    if not opaque_ref:
        # A bare branch name that is none of this session's own branches
        # cannot be this session's own PR -- no lookup needed.
        return None

    head_branch = _pr_head_branch(ref.lstrip("#"), ctx.cwd)
    if head_branch is None:
        return refuse(
            f"refused ({_TICKET}): could not resolve the head branch of PR "
            f"{ref!r} via `gh pr view`, so whether it belongs to this run "
            "cannot be verified. A run may not mark its own PR ready for "
            "review -- resolve manually or have a separate review run do "
            "this."
        )

    if head_branch in own_branches:
        return refuse(
            f"refused ({_TICKET}): PR {ref} has head branch {head_branch!r}, "
            "this session's own branch. A run may not mark its own PR ready "
            "for review -- a separate review run must do this."
        )

    return None


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [user_prompt_submit, agy_user_prompt_submit],
    "PreToolUse": [h for h in (guard_own_pr_ready, pre_tool, agy_pre_tool) if h is not None],
    "PostToolUse": [post_tool, agy_post_tool],
    "PostToolUseFailure": [post_tool_failure],
    "Stop": [stop, agy_stop],
    "PostToolBatch": [h for h in (rule_against_hearsay, be_quiet) if h is not None],
    "SubagentStart": [honest_output],
}
