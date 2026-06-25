"""Live hook-format conformance — Test Layer B of specs/hooks/CLIENT-TRANSLATION.md.

This is the DRIFT DETECTOR. It re-measures the real headless clients with the
probe harness (``scripts/verify_hook_formats.py``) and asserts each cell still
behaves the way the committed baseline
(``tests/hooks/fixtures/client_capabilities.json``) recorded. When an upstream
client changes a hook behaviour, a signal flips and the matching cell FAILS here
— that is the whole point: we find out the moment "what the client supports"
changes, instead of discovering it as a field regression weeks later.

This suite is OPT-IN and never runs in ordinary CI:
  * marked ``@pytest.mark.live`` and ``@pytest.mark.slow`` — the default
    ``addopts`` (``-m 'not slow and not integration and not demo'``) deselects
    it, so it only runs when explicitly selected with ``-m live``;
  * each cell is skipped if its client is unavailable/unauthenticated (the
    harness auto-detects via ``shutil.which`` + per-cell unavailable/unauthed
    notes), so a credential-less CI never drives a real client even if the
    marker filter were lifted.

Run it:  uv run pytest tests/hooks/test_live_conformance.py -m live -q

The fast, deterministic counterpart (router-vs-table) is the unit matrix; this
file is table-vs-reality.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "scripts" / "verify_hook_formats.py"
FIXTURE = REPO / "tests" / "hooks" / "fixtures" / "client_capabilities.json"

pytestmark = [pytest.mark.live, pytest.mark.slow]

# Signal fields that constitute the behavioural contract for a cell. A None in the
# committed baseline means "not measurable" (e.g. agy delivery while unauthed) and
# is not asserted.
_CONTRACT_FIELDS = ("accepted", "agent_saw", "blocked", "continued", "user_saw", "persisted")

# The audience/persistence columns each cell CLAIMS (from CLIENT-TRANSLATION.md),
# paired with the measured Signal field that proves it. The committed baseline
# carries both the claim and the measurement, so this assertion does NOT re-drive
# the clients — it enforces "the table cell == what the live harness measured",
# turning the matrix from prose assertion into test-enforced truth.
_CLAIM_PAIRS = (
    ("claim_user_saw", "user_saw"),
    ("claim_agent_saw", "agent_saw"),
    ("claim_persisted", "persisted"),
    ("claim_blocked", "blocked"),
)


def _load_fixture() -> dict:
    if not FIXTURE.exists():
        pytest.skip(f"no committed baseline at {FIXTURE} — run the harness first")
    return json.loads(FIXTURE.read_text())


def _baseline_cells() -> list[dict]:
    return _load_fixture().get("cells", [])


def _remeasure() -> dict[str, dict]:
    """Re-run the harness for all available clients; return {label: signal}."""
    # The harness now drives up to ~5 turns per cell (agent_saw + neutral user_saw
    # + >=2 persistence samples), each a cold-ish headless client turn, across all
    # cells — so the outer budget is large. The drift test is opt-in (@live) and
    # rarely run; the fast table==measurement enforcement reads the committed
    # baseline and does NOT re-drive clients.
    proc = subprocess.run(
        [sys.executable, "-u", str(HARNESS), "--out", "/dev/stdout"],
        capture_output=True,
        text=True,
        timeout=5400,
    )
    # The harness prints RUN lines then the JSON report (to --out=/dev/stdout, mixed
    # with the progress lines). Extract the trailing JSON object.
    text = proc.stdout
    start = text.find("{")
    if start < 0:
        pytest.skip(f"harness produced no JSON report; stderr={proc.stderr[-400:]}")
    report = json.loads(text[start:])
    return {c["label"]: c["signal"] for c in report.get("cells", [])}


@pytest.fixture(scope="session")
def remeasured() -> dict[str, dict]:
    # No env gate: selection is the ``@live`` marker (deselected by default
    # addopts) + the harness's own ``shutil.which`` availability detection and
    # per-cell unavailable/unauthenticated skips. A credential-less CI run that
    # somehow selected this suite still drives no real client.
    return _remeasure()


def _is_skip_note(note: str) -> bool:
    note = (note or "").lower()
    return "unavailable" in note or "unauthenticated" in note or "not implemented" in note


@pytest.mark.parametrize(
    "cell",
    _baseline_cells() or [pytest.param(None, marks=pytest.mark.skip(reason="no baseline fixture"))],
    ids=lambda c: c["label"] if isinstance(c, dict) else "no-baseline",
)
def test_client_behaviour_matches_baseline(cell: dict, remeasured: dict[str, dict]) -> None:
    """Each committed cell still behaves the way it was measured."""
    label = cell["label"]
    base = cell["signal"]
    if _is_skip_note(base.get("note", "")):
        pytest.skip(f"{label}: baseline not measurable ({base.get('note')})")
    now = remeasured.get(label)
    if now is None:
        pytest.skip(f"{label}: not re-measured (client unavailable this run)")
    if _is_skip_note(now.get("note", "")):
        pytest.skip(f"{label}: client unavailable/unauthed this run ({now.get('note')})")

    drift = {
        f: (base.get(f), now.get(f))
        for f in _CONTRACT_FIELDS
        if base.get(f) is not None and base.get(f) != now.get(f)
    }
    assert not drift, (
        f"UPSTREAM HOOK BEHAVIOUR CHANGED for {label!r}: {drift}. "
        f"A client updated its hook contract. Update client_spec.py + the renderer "
        f"+ re-baseline the fixture (scripts/verify_hook_formats.py). "
        f"hypothesis: {cell.get('hypothesis')}"
    )


@pytest.mark.parametrize(
    "cell",
    _baseline_cells() or [pytest.param(None, marks=pytest.mark.skip(reason="no baseline fixture"))],
    ids=lambda c: c["label"] if isinstance(c, dict) else "no-baseline",
)
def test_table_cell_matches_measurement(cell: dict) -> None:
    """Each CLIENT-TRANSLATION.md table cell's CLAIM == the LIVE measurement.

    This is the proof that turns the audience/persistence matrix from prose
    assertion into test-enforced truth. The committed baseline
    (``client_capabilities.json``, regenerated from a live authenticated run)
    carries, per cell, BOTH the table's claimed property (``claim_user_saw`` /
    ``claim_agent_saw`` / ``claim_persisted`` / ``claim_blocked``) AND the
    measured ``Signal``. A claim that disagrees with the measurement FAILS here —
    so an editor cannot quietly change a table cell to a value the live client
    does not exhibit, and a client behaviour change that contradicts the table is
    caught the next time the baseline is regenerated.

    A claim of ``None`` means "the table does not assert this column for this
    cell" (e.g. user-visibility of an interactive-TUI-only Claude banner, which
    is NOT headless-observable — an HONEST gap recorded as None, never faked to a
    pass) and is not asserted.
    """
    label = cell["label"]
    sig = cell["signal"]
    if _is_skip_note(sig.get("note", "")):
        pytest.skip(f"{label}: baseline not measurable ({sig.get('note')})")

    mismatches = {}
    for claim_field, measured_field in _CLAIM_PAIRS:
        claim = cell.get(claim_field)
        if claim is None:
            continue  # the table does not assert this column for this cell
        measured = sig.get(measured_field)
        if measured is None:
            # The table claims a value the live run could not observe this time.
            # Honest gap (e.g. unauthenticated/timeout); do not assert a pass.
            mismatches[measured_field] = (f"claim={claim}", "measured=None (unobserved)")
        elif measured != claim:
            mismatches[measured_field] = (f"claim={claim}", f"measured={measured}")

    assert not mismatches, (
        f"TABLE CELL CONTRADICTS LIVE MEASUREMENT for {label!r}: {mismatches}. "
        f"table_cell: {cell.get('table_cell')!r}. "
        f"Either the CLIENT-TRANSLATION.md cell is wrong, or the client changed. "
        f"Re-baseline (scripts/verify_hook_formats.py) and correct the table cell."
    )
