"""Boots the REAL, locally built crew image and runs the structural checks a
human previously ran by hand: `claude plugin list`, the agy plugins
directory, `$ACA_DATA`, and the container path polecat mounts an agy
session's live state into (specs/polecat/tmux-interactive-driving.md,
"Plugin structural check").

**What this proves, and what it does not.** A plugin reported as installed,
or a directory present on disk, is not proof its hooks or MCP servers are
actually active for a running session (tmux-interactive-driving.md says this
explicitly). These are structural checks only — they catch a plugin silently
dropped from the image, a permission regression, or a mount-path drift. They
do not exercise a live hook firing or a real MCP round trip; that is a
functional check this module does not attempt.

Opt-in, per the `e2e` marker's own convention (pyproject.toml): skips with an
explicit reason unless `POLECAT_E2E=1`, docker is reachable, and the image
this module names is already built locally — a missing precondition here must
read as a skip, never a silent pass. Every container this module starts is
named, `--rm`, and bounded by an explicit subprocess timeout; a timeout path
also force-removes the container so nothing outlives the test.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

from lib.polecat import cli  # for CONTAINER_ACA_DATA — no duplicated literal

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MARKETPLACE_TOML = _REPO_ROOT / "build" / "marketplace.toml"
_CLI_PY = _REPO_ROOT / "lib" / "polecat" / "cli.py"

# `make docker-build`'s second tag (Makefile, `docker-build:`) — always this
# name locally regardless of $IMAGE, so it is the one fixed point a smoke
# test can name without guessing at a registry. $POLECAT_IMAGE overrides it,
# same precedence as everywhere else in this plugin.
_DEFAULT_IMAGE = "aops-crew:latest"

_CONTAINER_TIMEOUT = 60

# The agy session-state mount target `cli.py`'s `run()` hardcodes for
# `agent_cmd == "agy"`. Not importable — it is a local inside `run()`, not a
# module constant — so this is pinned by the companion contract test below
# rather than silently drifting out of sync with the real source.
_AGY_SESSION_PATH = "/home/worker/.gemini/tmp/workspace"


def _expected_plugin_names() -> set[str]:
    data = tomllib.loads(_MARKETPLACE_TOML.read_text())
    return {p["name"] for p in data["plugins"]}


def _image() -> str:
    return os.environ.get("POLECAT_IMAGE", _DEFAULT_IMAGE)


@pytest.fixture(scope="module")
def real_image():
    """The image name, once every precondition to actually run against it is
    confirmed — otherwise an explicit, named skip. Session-module scoped so
    the docker calls that check availability run once, not once per test."""
    if os.environ.get("POLECAT_E2E") != "1":
        pytest.skip(
            "POLECAT_E2E is not '1' — set it to run the container smoke test "
            "(boots the real image; see specs/polecat/tmux-interactive-driving.md)"
        )
    if shutil.which("docker") is None:
        pytest.skip("docker is not on PATH — cannot boot the real image")
    daemon = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
    )
    if daemon.returncode != 0:
        pytest.skip("the docker daemon is not reachable — cannot boot the real image")
    image = _image()
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if inspect.returncode != 0:
        pytest.skip(f"image {image!r} is not present locally — run `make docker-build` first")
    return image


def _run_in_container(
    image: str, script: str, *, mounts: list[str] | None = None, timeout: int = _CONTAINER_TIMEOUT
) -> subprocess.CompletedProcess:
    """`docker run --rm --entrypoint sh <image> -c <script>`, named so a
    timeout path can force-remove it, and hard-bounded so this can never hang
    the suite.

    `--entrypoint sh` bypasses `entrypoint.sh`'s git-identity/GitHub-token
    refusal on purpose (specs/polecat/tmux-interactive-driving.md, "Plugin
    structural check") — these checks are read-only and need neither.
    """
    name = f"aops-smoke-{uuid.uuid4().hex[:8]}"
    cmd = ["docker", "run", "--rm", "--name", name, "--entrypoint", "sh"]
    for mount in mounts or []:
        cmd.extend(["-v", mount])
    cmd.extend([image, "-c", script])
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        raise


def _parse_claude_plugin_list(output: str) -> dict[str, bool]:
    """`{plugin_name: is_enabled}` from `claude plugin list`'s human-readable
    text — there is no `--json` form of this command to parse instead."""
    result: dict[str, bool] = {}
    blocks = re.split(r"\n(?=\s*❯\s+)", output)
    for block in blocks:
        match = re.search(r"❯\s+([\w-]+)@", block)
        if not match:
            continue
        result[match.group(1)] = "✔ enabled" in block
    return result


# ---------------------------------------------------------------------------


def test_claude_plugin_list_matches_the_marketplace(real_image):
    """Every plugin `build/marketplace.toml` declares must be installed and
    enabled for the `claude` client. Does not prove any plugin's hooks or MCP
    servers are actually live — see the module docstring."""
    expected = _expected_plugin_names()
    result = _run_in_container(real_image, "claude plugin list")
    assert result.returncode == 0, result.stderr

    installed = _parse_claude_plugin_list(result.stdout)
    missing = expected - set(installed)
    assert not missing, (
        f"declared in marketplace.toml but not installed: {missing}\n{result.stdout}"
    )

    not_enabled = {name for name in expected if not installed.get(name)}
    assert not not_enabled, f"installed but not enabled: {not_enabled}\n{result.stdout}"


def test_agy_plugins_directory_matches_the_marketplace(real_image):
    """Every plugin declared for the `claude` client must also be present
    under agy's plugin directory — the two clients ship from the same
    marketplace list (Dockerfile's plugin-install RUN block)."""
    expected = _expected_plugin_names()
    result = _run_in_container(real_image, "ls /home/worker/.gemini/antigravity-cli/plugins/")
    assert result.returncode == 0, result.stderr

    present = set(result.stdout.split())
    missing = expected - present
    assert not missing, f"declared in marketplace.toml but absent from agy's plugins/: {missing}"


def test_aca_data_matches_what_polecat_mounts_layer_3_rules_into(real_image):
    """`$ACA_DATA` inside the image must be exactly the path
    `lib/polecat/cli.py`'s `CONTAINER_ACA_DATA` mounts a configured
    `rules_dir` onto — a drift between the two would silently break cope's
    layer 3 in every container even though both sides looked correct alone."""
    result = _run_in_container(real_image, 'echo "$ACA_DATA"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == cli.CONTAINER_ACA_DATA


def test_agy_session_mount_target_is_writable_by_the_invoking_host_uid(real_image, tmp_path):
    """Structural proxy for the path `cli.py` mounts an agy session's host log
    directory onto (`container_session_path` in `run()`, `agent_cmd ==
    "agy"`): mount a throwaway host directory there under the same `-u
    hostuid:hostgid` polecat itself uses, and confirm a file can be created.

    This proves the mount TARGET is viable for any invoking host UID — it does
    not prove agy actually writes its live session state there at runtime;
    tmux-interactive-driving.md already names that a design assumption to
    confirm separately, not a guarantee this structural check can give."""
    host_dir = tmp_path / "agy-session-probe"
    host_dir.mkdir()
    result = _run_in_container(
        real_image,
        f"touch {_AGY_SESSION_PATH}/probe && echo WROTE",
        mounts=[f"{host_dir}:{_AGY_SESSION_PATH}"],
    )
    assert result.returncode == 0, result.stderr
    assert "WROTE" in result.stdout
    assert (host_dir / "probe").exists()


def test_the_agy_session_path_literal_is_pinned_to_the_real_source():
    """The companion contract for the test above: `_AGY_SESSION_PATH` is a
    copy of a local variable inside `cli.py`'s `run()`, not an import — this
    is what stops that copy from silently drifting if the real path is ever
    renamed there."""
    source = _CLI_PY.read_text()
    assert _AGY_SESSION_PATH in source, (
        f"{_AGY_SESSION_PATH!r} no longer appears in cli.py — this test's mount "
        "target has drifted from the real agy container_session_path"
    )


def test_every_declared_plugin_has_at_least_one_check_above():
    """A marketplace.toml edit that adds a plugin must be caught by both
    checks above without further wiring — this pins that the expected-name
    source really is the same file both tests read, not a stale copy."""
    expected = _expected_plugin_names()
    assert expected, "build/marketplace.toml declared no plugins — nothing to check"
    # Named rather than merely non-empty: a stale copy of the manifest would
    # still parse and still yield names, so the pin has to be against plugins
    # this repository actually declares (specs/ARCHITECTURE.md's plugin table).
    assert {"ida", "pkb", "rbg"} <= expected
