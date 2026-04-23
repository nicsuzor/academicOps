"""Regression test for the aops-crew Docker image.

Issue #520: Gemini CLI called ``pgrep`` inside the container, but the
base image was missing ``procps``. This caused stderr spam like
``/bin/sh: 1: pgrep: not found`` during polecat task runs.

This test verifies that ``pgrep`` is available on $PATH in the built
``aops-crew`` image. It skips cleanly when Docker or the image is
unavailable (local dev machines without the image built).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests.conftest import _docker_available  # noqa: E402


def _image_built() -> bool:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "aops-crew"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.integration
def test_procps_available() -> None:
    """``pgrep`` must resolve inside the aops-crew image (issue #520)."""
    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _image_built():
        pytest.skip("aops-crew image not built locally")

    result = subprocess.run(
        ["docker", "run", "--rm", "aops-crew", "which", "pgrep"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"`which pgrep` failed in aops-crew image "
        f"(exit={result.returncode}, stderr={result.stderr!r}). "
        "procps is likely missing from the Dockerfile apt-get install block."
    )
    assert "/pgrep" in result.stdout, (
        f"pgrep not found on PATH in aops-crew image; stdout={result.stdout!r}"
    )


@pytest.mark.integration
def test_playwright_chromium_runnable() -> None:
    """Playwright's Chromium must be baked into the aops-crew image.

    Marsha and other workers that run browser verification depend on
    ``playwright`` + Chromium being available without a network round-trip
    or an at-runtime ``install-deps`` that needs root. The fix bakes both
    the browser binaries and the system libraries (libnss3, libatk, fonts,
    ...) into the image at build time.

    This test asserts two things by actually running the installed
    Chromium headless-shell binary with ``--version``:

      1. The browser cache exists under ``~/.cache/ms-playwright`` with a
         ``chromium_headless_shell-*`` directory (proves ``playwright
         install chromium`` ran during build).
      2. That binary launches successfully — which would fail with a
         dynamic-linker error (missing libnss3 etc.) if ``install-deps``
         had not been run during build.

    Pre-fix both conditions fail; post-fix both pass.
    """
    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _image_built():
        pytest.skip("aops-crew image not built locally")

    # Single shell invocation: locate the installed headless-shell binary
    # under ~/.cache/ms-playwright and run it with --version. If the cache
    # dir doesn't exist, the glob expands to nothing and the command fails
    # fast. If the binary is missing system libs, the binary itself will
    # exit non-zero with a linker error on stderr.
    script = (
        "set -e; "
        'root="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"; '
        'shell=$(find "$root" -type f \\( -name chrome-headless-shell -o -name headless_shell \\) 2>/dev/null | head -n1); '
        'if [ -z "$shell" ]; then '
        '  echo "MISSING: no chromium headless shell binary under $root (playwright install chromium was not run at build time)" >&2; '
        "  exit 10; "
        "fi; "
        '"$shell" --version'
    )

    result = subprocess.run(
        ["docker", "run", "--rm", "aops-crew", "sh", "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        "Chromium headless-shell failed to run in aops-crew image "
        f"(exit={result.returncode}).\n"
        f"stdout={result.stdout!r}\n"
        f"stderr={result.stderr!r}\n"
        "Either the browser cache is missing (playwright install chromium "
        "not baked in) or system libraries are missing (playwright "
        "install-deps not baked in). Fix: add both RUN steps to the "
        "Dockerfile."
    )
    assert "HeadlessChrome" in result.stdout or "Chrome" in result.stdout, (
        f"Unexpected --version output from chromium: {result.stdout!r}"
    )


@pytest.mark.integration
def test_playwright_browsers_path_writable() -> None:
    """``/ms-playwright`` must be writable by the container user.

    The Playwright MCP server creates per-session cache subdirectories
    (e.g. ``/ms-playwright/mcp-chrome-<hash>``) at launch. Pre-fix the
    directory was root-owned ``a+rX``, so non-root users got EACCES
    trying to mkdir a subdir — blocking all MCP browser tool calls
    inside a crew container.
    """
    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _image_built():
        pytest.skip("aops-crew image not built locally")

    script = (
        "set -e; "
        'd="${PLAYWRIGHT_BROWSERS_PATH:-/ms-playwright}/mcp-chrome-testwrite"; '
        'mkdir "$d" && rmdir "$d" && echo WRITE_OK'
    )

    result = subprocess.run(
        ["docker", "run", "--rm", "--user", "1001:1001", "aops-crew", "sh", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0 and "WRITE_OK" in result.stdout, (
        "PLAYWRIGHT_BROWSERS_PATH is not writable by an arbitrary container UID "
        f"(exit={result.returncode}).\n"
        f"stdout={result.stdout!r}\n"
        f"stderr={result.stderr!r}\n"
        "Fix: ensure the Dockerfile chmods /ms-playwright writable "
        "(`chmod -R a+rwX /ms-playwright`) after `playwright install`."
    )


@pytest.mark.integration
def test_cc_can_link() -> None:
    """``cc`` must be able to link a trivial C program in the aops-crew image.

    Rust's cargo invokes ``cc`` as the default linker. Pre-fix, the image
    installed ``gcc`` (binary only) but not ``libc6-dev``, so linking failed
    with ``cannot find Scrt1.o`` / ``cannot find crti.o``. Cargo surfaced this
    as a missing-linker error and polecat workers skipped compilation checks
    on Rust PRs (the ``mem`` repo).

    The fix installs ``build-essential`` (which pulls in gcc, g++, make,
    libc6-dev, dpkg-dev). This test asserts that a minimal C source compiles
    and links end-to-end.
    """
    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _image_built():
        pytest.skip("aops-crew image not built locally")

    script = (
        "set -e; "
        'printf "int main(void){return 0;}\\n" > /tmp/t.c; '
        "cc /tmp/t.c -o /tmp/t && /tmp/t && echo LINK_OK"
    )

    result = subprocess.run(
        ["docker", "run", "--rm", "aops-crew", "sh", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0 and "LINK_OK" in result.stdout, (
        "cc failed to link a trivial C program in aops-crew image "
        f"(exit={result.returncode}).\n"
        f"stdout={result.stdout!r}\n"
        f"stderr={result.stderr!r}\n"
        "libc6-dev is likely missing — ensure the Dockerfile installs "
        "`build-essential` (not just `gcc`)."
    )
