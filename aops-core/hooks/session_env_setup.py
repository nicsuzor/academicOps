#!/usr/bin/env -S uv run python
"""
Session environment setup hook for Claude Code.

Ensures AOPS, PYTHONPATH, and other required environment variables are
persisted for the duration of the Claude Code session using CLAUDE_ENV_FILE.
"""

import os
import shlex
import sys
from pathlib import Path

# Ensure aops-core is in path for imports
HOOK_DIR = Path(__file__).parent
AOPS_CORE_DIR = HOOK_DIR.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from lib.gate_model import GateResult, GateVerdict
from lib.session_paths import (
    get_all_gate_file_paths,
    get_hook_log_path,
    get_session_file_path,
    get_session_status_dir,
)
from lib.session_state import SessionState

from hooks.schemas import HookContext


def set_persistent_env(env_dict: dict[str, str]):
    """Set environment variables persistently for the session, if possible."""

    # Claude Code support -- write to CLAUDE_ENV_FILE provided in session start hook:
    if env_path := os.environ.get("CLAUDE_ENV_FILE"):
        try:
            with open(env_path, "a") as f:
                for key, value in env_dict.items():
                    f.write(f"export {key}={shlex.quote(value)}\n")
        except Exception as e:
            print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)


def append_shell_lines(lines: list[str]):
    """Append raw shell lines to CLAUDE_ENV_FILE.

    Unlike set_persistent_env, lines are written verbatim — no shell
    quoting. Use this for shell-syntax constructs (conditional exports,
    variable references) that must be evaluated at shell-source time.
    """
    if not lines:
        return
    if env_path := os.environ.get("CLAUDE_ENV_FILE"):
        try:
            with open(env_path, "a") as f:
                for line in lines:
                    f.write(line + "\n")
        except Exception as e:
            print(f"WARNING: Failed to append shell lines to CLAUDE_ENV_FILE: {e}", file=sys.stderr)


def run_session_env_setup(ctx: HookContext, state: SessionState) -> GateResult | None:
    """Session start initialization - fail-fast checks and user messages.


    Sets:
    - AOPS_SESSION_ID  (canonical, vendor-neutral session id)
    - PYTHONPATH (includes aops-core)
    - AOPS_SESSION_STATE_DIR
    - AOPS_HOOK_LOG_PATH
    - Other placeholder variables from original script

    """

    if ctx.hook_event != "SessionStart":
        return None

    persist = {}

    # Use precomputed short_hash from context
    short_hash = ctx.session_short_hash
    hook_log_path = get_hook_log_path(ctx.session_id, transcript_path=ctx.transcript_path)
    state_file_path = get_session_file_path(ctx.session_id, transcript_path=ctx.transcript_path)
    status_dir = get_session_status_dir(ctx.session_id, transcript_path=ctx.transcript_path)

    # Fail-fast: ensure state file can be written
    if not state_file_path.exists():
        try:
            state.save()
        except OSError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"FAIL-FAST: Cannot write session state file.\n"
                    f"Path: {state_file_path}\n"
                    f"Error: {e}\n"
                    f"Fix: Check directory permissions and disk space."
                ),
                metadata={"source": "session_start", "error": str(e)},
            )

    transcript_path = ctx.transcript_path or ""  # allow-fallback: status string only

    # Session started messages
    messages = [
        f"Session Started: {ctx.session_id} ({short_hash})",
        f"Version: {state.version}",
        f"State File: {state_file_path}",
        f"Hooks log: {hook_log_path}",
        f"Transcript: {transcript_path}",
    ]

    # Ensure auto mode classifier rules are installed
    try:
        from lib.automode import install, is_installed

        if not is_installed():
            ok, msg = install()
            if ok:
                messages.append(f"autoMode: {msg}")
            else:
                messages.append(f"autoMode: skipped ({msg})")
    except Exception as e:
        messages.append(f"autoMode: check failed ({e})")

    # 1. Persist Session ID
    # AOPS_SESSION_ID is the canonical, vendor-neutral session-id env var
    # used by skills, agents, and the gate engine. Set here for Claude Code;
    # polecat sets it for Gemini sessions in cli.py (alongside GEMINI_SESSION_ID,
    # which Gemini CLI sets itself and we read as a provider discriminator).
    if ctx.session_id:
        persist["AOPS_SESSION_ID"] = ctx.session_id

    # 2. Persist PYTHONPATH
    # Include aops-core in PYTHONPATH so hooks and scripts can find lib/
    aops_core = str(AOPS_CORE_DIR)
    current_pythonpath = os.environ.get("PYTHONPATH", "")  # allow-fallback: PYTHONPATH may be unset
    if aops_core not in current_pythonpath:
        new_pythonpath = f"{aops_core}:{current_pythonpath}".strip(":")
        persist["PYTHONPATH"] = new_pythonpath

    # 3. Persist paths
    # Persist AOPS_SESSIONS and POLECAT_HOME so subagents (worktree agents,
    # macOS app sessions) write transcripts/summaries to the correct git-synced
    # directory instead of falling back to ~/.polecat/sessions/.
    for var in ("AOPS_SESSIONS", "POLECAT_HOME", "AOPS_SRC_DIR"):
        val = os.environ.get(var)
        if val:
            persist[var] = val

    try:
        persist["AOPS_SESSION_STATE_DIR"] = str(status_dir)
    except Exception as e:
        print(f"WARNING: Failed to determine session status dir: {e}", file=sys.stderr)

    persist["AOPS_HOOK_LOG_PATH"] = str(hook_log_path)

    # 4. Persist gate file paths
    gate_paths = get_all_gate_file_paths(ctx.session_id, transcript_path=ctx.transcript_path)
    for gate_name, gate_path in gate_paths.items():
        persist[f"AOPS_GATE_FILE_{gate_name.upper()}"] = str(gate_path)

    # 5. Apply agent-env-map.conf credential isolation mappings (issue #581).
    # The conf is the shared source of truth (containers + tests + host).
    # For the HOST Claude session we additionally enforce a stricter,
    # fail-closed GitHub identity below (step 5b).
    from lib.agent_env import (
        get_env_mapping_persist_dict,
        get_env_mapping_shell_lines,
    )

    persist.update(get_env_mapping_persist_dict())

    # GH_TOKEN / GITHUB_TOKEN are handled authoritatively in step 5c as
    # deferred shell exports that track AOPS_BOT_GH_TOKEN exactly (and clobber
    # any personal value inherited from the parent env). Drop the conf-derived
    # hook-time values here to avoid double / divergent writes.
    persist.pop("GH_TOKEN", None)
    persist.pop("GITHUB_TOKEN", None)

    # 5b. GitHub agent-identity isolation (fail-closed).
    #
    # Inside agent sessions, ALL GitHub authentication uses AOPS_BOT_GH_TOKEN
    # and nothing else. If that token is absent, auth fails cleanly rather than
    # silently falling back to the user's identity. Three personal-credential
    # channels are disabled:
    #   - SSH agent / Keychain keys → SSH_AUTH_SOCK="" + GIT_SSH_COMMAND=false
    #     (from conf) plus the insteadOf rewrite below forces github.com to
    #     HTTPS, so git never attempts SSH.
    #   - ~/.gitconfig credential helper (e.g. `!gh auth git-credential`) →
    #     overridden below: the helper list is reset to empty, then a single
    #     helper is installed that emits the bot PAT *exclusively*. (Git treats
    #     `helper` as list-typed, so the empty value clears the prior list.)
    #   - gh CLI keyring / hosts.yml → GH_CONFIG_DIR points at an isolated,
    #     session-scoped empty dir (below), so gh cannot read the user's stored
    #     login and must use GH_TOKEN (the bot token) or fail.
    #
    # NB: none of this touches the user's own terminal — these vars are written
    # only to CLAUDE_ENV_FILE, which Claude Code sources for its own tool calls.
    # An interactive shell never sources it.
    persist["GIT_CONFIG_COUNT"] = "4"
    persist["GIT_CONFIG_KEY_0"] = "url.https://github.com/.insteadOf"
    persist["GIT_CONFIG_VALUE_0"] = "git@github.com:"
    persist["GIT_CONFIG_KEY_1"] = "url.https://github.com/.insteadOf"
    persist["GIT_CONFIG_VALUE_1"] = "ssh://git@github.com/"
    persist["GIT_CONFIG_KEY_2"] = "credential.https://github.com.helper"
    persist["GIT_CONFIG_VALUE_2"] = ""
    persist["GIT_CONFIG_KEY_3"] = "credential.https://github.com.helper"
    persist["GIT_CONFIG_VALUE_3"] = (
        '!f() { test "$1" = get && '
        'printf "username=x-access-token\\npassword=%s\\n" '
        '"${AOPS_BOT_GH_TOKEN}"; }; f'
    )

    # Isolate the gh CLI from the user's keyring / personal hosts.yml so it
    # cannot authenticate as the user. With an empty GH_CONFIG_DIR, gh has no
    # stored login and uses GH_TOKEN (the bot token) exclusively, or fails.
    gh_config_dir = Path(status_dir) / "gh-config"
    try:
        gh_config_dir.mkdir(parents=True, exist_ok=True)
        persist["GH_CONFIG_DIR"] = str(gh_config_dir)
    except OSError as e:
        print(f"WARNING: Failed to create isolated GH_CONFIG_DIR: {e}", file=sys.stderr)

    # Fail-fast signal: warn loudly if the bot token isn't visible to the hook.
    # It may still arrive via the shell snapshot (see deferred exports in 5c),
    # so this is a warning rather than a hard block.
    if not os.environ.get("AOPS_BOT_GH_TOKEN"):
        messages.append(
            "⚠️  GitHub auth: AOPS_BOT_GH_TOKEN not set in the hook environment. "
            "git/gh will fail-closed (no personal-credential fallback). "
            "If it is set in your shell profile it will still be picked up."
        )

    # 7. Ensure required CLIs (uv, gh, etc.) are accessible in PATH.
    # Centralised in lib/path_bootstrap — shared logic with ensure-path.sh.
    from lib.path_bootstrap import detect_path_additions

    current_path = os.environ.get("PATH", "")  # allow-fallback: handler accepts ""
    updated_path = detect_path_additions(current_path)
    if updated_path:
        persist["PATH"] = updated_path
        # Also update live env so subprocesses spawned later in this hook
        # invocation find the tools immediately (persist only applies to
        # future Claude tool calls via CLAUDE_ENV_FILE).
        os.environ["PATH"] = updated_path

    # 8. Inject Tier 1 Core context (CORE.md)
    # This ensures Claude Code receives the essential framework context.
    core_md_path = AOPS_CORE_DIR / "CORE.md"
    if core_md_path.exists():
        try:
            core_content = core_md_path.read_text().strip()
            if core_content:
                messages.extend(
                    [
                        "",
                        "--- FRAMEWORK CORE ---",
                        core_content,
                        "----------------------",
                        "",
                    ]
                )
        except Exception as e:
            print(f"WARNING: Failed to read CORE.md: {e}", file=sys.stderr)

    # 9. Ensure daily note exists for today to avoid stale landing (P2)
    try:
        from datetime import datetime

        from lib.paths import get_daily_dir

        # Use simple date format to match SKILL.md naming convention
        today_compact = datetime.now().strftime("%Y%m%d")
        today_iso = datetime.now().strftime("%Y-%m-%d")
        daily_dir = get_daily_dir()
        daily_note_path = daily_dir / f"{today_compact}-daily.md"

        if not daily_note_path.exists():
            daily_dir.mkdir(parents=True, exist_ok=True)
            # Minimal valid daily note template per SSoT
            content = f"""---
title: "Daily Summary - {today_iso}"
type: daily
date: {today_iso}
---

# Daily Summary - {today_iso}

Today's note has not been populated yet. Run `/daily` to update.
"""
            daily_note_path.write_text(content)
            messages.append(
                f"Daily note: Created {today_compact}-daily.md (Run /daily to populate)"
            )
        else:
            messages.append(f"Daily note: {today_compact}-daily.md")

    except Exception as e:
        # Graceful degradation for daily note bootstrap
        messages.append(f"Daily note: bootstrap failed ({e})")

    # Persist all resolved environment variables (literals and any env-to-env
    # mappings that resolved at hook time).
    set_persistent_env(persist)

    # 5c. Deferred-shell exports. SOURCE resolution is deferred to shell-source
    # time so vars set only in the user's shell snapshot (e.g. AOPS_BOT_GH_TOKEN
    # from ~/.zshenv, invisible to the launchd-inherited Python hook) are still
    # picked up. Two groups:
    #   (i)  conf-driven mappings (Gemini/PKB/etc.). GH_TOKEN/GITHUB_TOKEN are
    #        filtered out — they are exported authoritatively in group (ii).
    #   (ii) the fail-closed GitHub identity: GH_TOKEN and GITHUB_TOKEN track
    #        AOPS_BOT_GH_TOKEN *exactly* (empty if it is unset/empty), which also
    #        clobbers any personal token inherited from the parent env. These
    #        run last, so they are authoritative.
    conf_lines = [
        line
        for line in get_env_mapping_shell_lines()
        if "export GH_TOKEN=" not in line and "export GITHUB_TOKEN=" not in line
    ]
    shell_lines: list[str] = []
    if conf_lines:
        shell_lines.append("# agent-env-map.conf: deferred-shell exports (issue #581)")
        shell_lines.extend(conf_lines)
    shell_lines.extend(
        [
            "# Fail-closed GitHub identity: bot token only (empty => auth fails).",
            'export GH_TOKEN="${AOPS_BOT_GH_TOKEN:-}"',
            'export GITHUB_TOKEN="${AOPS_BOT_GH_TOKEN:-}"',
        ]
    )
    append_shell_lines(shell_lines)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        system_message="\n".join(messages),
        metadata={
            "source": "session_env_setup",
            "persisted_vars": persist,
            "deferred_shell_lines": shell_lines,
        },
    )
