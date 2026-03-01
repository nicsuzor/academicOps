"""Reproduction test for install.py cron idempotency bug (P#82).

Before the fix, re-running install_cron_jobs() accumulated duplicate
'# aOps quick sync' / '# aOps full maintenance' crontab entries.
This test reproduces that defect scenario and verifies the fix holds.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parents[1].resolve()

# Ensure scripts/lib is importable so install.py can find build_utils
_scripts_lib = str(REPO_ROOT / "scripts" / "lib")
if _scripts_lib not in sys.path:
    sys.path.insert(0, _scripts_lib)


def _load_install():
    """Load scripts/install.py as a module."""
    install_path = REPO_ROOT / "scripts" / "install.py"
    spec = importlib.util.spec_from_file_location("install_script", install_path)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def install_mod():
    return _load_install()


def test_install_cron_jobs_idempotency(install_mod):
    """Re-running install_cron_jobs must not produce duplicate cron entries.

    Reproduces the defect: before scripts/install.py lines 77-80, calling
    install_cron_jobs() a second time appended new repo-sync-cron.sh entries
    on top of the existing ones, resulting in duplicate cron jobs.
    """
    aops_path = Path("/fake/aops")
    aca_data_path = "/fake/aca-data"

    # Simulate an already-populated crontab (output of a previous install)
    existing_crontab = (
        "\n".join(
            [
                "# some other cron",
                "0 0 * * * /usr/bin/true",
                "# aOps quick sync (brain + transcripts)",
                f"*/5 * * * * {aops_path}/scripts/repo-sync-cron.sh --quick >> /tmp/repo-sync-quick.log 2>&1",
                "# aOps full maintenance (viz + sessions)",
                f"0 * * * * {aops_path}/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1",
                "# aOps refinery",
                f"*/5 * * * * cd {aops_path} && ACA_DATA={aca_data_path} uv run python scripts/refinery.py > /dev/null 2>&1",
            ]
        )
        + "\n"
    )

    written: list[str] = []

    def fake_popen(cmd, stdin=None):
        mock = MagicMock()
        mock.communicate = lambda input=None: written.append(input.decode() if input else "")
        return mock

    with (
        patch("subprocess.check_output", return_value=existing_crontab.encode()),
        patch("subprocess.Popen", side_effect=fake_popen),
    ):
        install_mod.install_cron_jobs(aops_path, aca_data_path)

    assert len(written) == 1, "Expected exactly one crontab write"
    result_lines = written[0].splitlines()

    # Core assertion: only two repo-sync-cron.sh lines (quick + full)
    sync_lines = [line for line in result_lines if "repo-sync-cron.sh" in line]
    assert len(sync_lines) == 2, (
        f"Expected 2 repo-sync-cron.sh lines, got {len(sync_lines)}:\n" + "\n".join(sync_lines)
    )

    # Comment markers must not be duplicated
    quick_comments = [line for line in result_lines if "# aOps quick sync" in line]
    full_comments = [line for line in result_lines if "# aOps full maintenance" in line]
    assert len(quick_comments) == 1, f"Duplicate '# aOps quick sync' markers: {quick_comments}"
    assert len(full_comments) == 1, f"Duplicate '# aOps full maintenance' markers: {full_comments}"

    # Refinery must not be re-added (removed from install)
    refinery_lines = [
        line for line in result_lines if "# aOps refinery" in line or "scripts/refinery.py" in line
    ]
    assert not refinery_lines, f"Refinery should not be installed: {refinery_lines}"

    # Unrelated cron entries must be preserved
    assert "0 0 * * * /usr/bin/true" in result_lines, "Unrelated cron entry was incorrectly removed"
