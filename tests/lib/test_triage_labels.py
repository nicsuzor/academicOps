import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

# Add aops-core to path for `lib.*` imports
REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib.triage_labels import TRIAGE_LABELS, ensure_triage_labels


def test_canonical_label_set_matches_apply_triage():
    """The labels used by apply_triage in dump_pr_state.py must be canonical."""
    names = {label.name for label in TRIAGE_LABELS}
    assert names == {
        "triage:escalate",
        "triage:stale",
        "triage:auto-mergeable",
        "triage:pipeline",
        "triage:needs-judgment",
    }


def test_each_label_has_name_color_description():
    for label in TRIAGE_LABELS:
        assert label.name.startswith("triage:")
        assert len(label.color) == 6
        # Valid hex (no leading '#')
        int(label.color, 16)
        assert label.description


def test_ensure_triage_labels_invokes_gh_label_create_force_per_label(tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        result = subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return result

    with patch("lib.triage_labels.subprocess.run", side_effect=fake_run):
        failures = ensure_triage_labels(tmp_path)

    assert failures == []
    assert len(calls) == len(TRIAGE_LABELS)
    for cmd, label in zip(calls, TRIAGE_LABELS, strict=False):
        assert cmd[:3] == ["gh", "label", "create"]
        assert cmd[3] == label.name
        assert "--force" in cmd
        assert "--color" in cmd
        assert label.color in cmd
        assert "--description" in cmd
        assert label.description in cmd


def test_ensure_triage_labels_continues_past_individual_failures(tmp_path, capsys):
    """A failure on one label must not abort provisioning of the rest."""

    def fake_run(cmd, **kwargs):
        if "triage:stale" in cmd:
            err = subprocess.CalledProcessError(1, cmd)
            err.stderr = "HTTP 403: insufficient scope"
            raise err
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    with patch("lib.triage_labels.subprocess.run", side_effect=fake_run):
        failures = ensure_triage_labels(tmp_path)

    assert failures == ["triage:stale"]
    captured = capsys.readouterr()
    assert "Warning: ensure_triage_labels failed" in captured.err
    assert "triage:stale" in captured.err
