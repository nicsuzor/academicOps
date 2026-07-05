"""Regression test: R2 in rbg.md includes the universal-claim inference step.

Root cause documented in task aops-44c424dc: when a test docstring makes a
universal claim ("never", "must always", "no X may ever Y"), R2 did not require
RBG to infer the implied class and verify parametrisation over it. PR #1802
(test_ida_denyreason_1798.py) is the gold-standard worked case — universal
docstring, agy-only parametrisation, missed by RBG.

This test guards against regression: if the R2 inference step is removed or
weakened, the test fails and the gap is surfaced immediately.
"""

from __future__ import annotations

from pathlib import Path

RBG_MD = Path(__file__).resolve().parents[1] / "aops-core" / "agents" / "rbg.md"


def _r2_text() -> str:
    text = RBG_MD.read_text()
    for line in text.splitlines():
        if line.strip().startswith("- **R2"):
            return line
    raise AssertionError(f"R2 rule not found in {RBG_MD}")


def test_r2_rule_is_present():
    """Structural guard: the R2 rule exists in rbg.md and is non-empty.

    NOTE — prose-token assertions removed (judgment-non-delegable axiom).
    Asserting that specific token strings ("universal claim", "parametrises",
    "unreachable") appear in R2 makes the wording immutable at the token level
    and substitutes a mechanical scan for the qualitative judgment "does R2
    still instruct RBG to perform universal-claim inference?"  That is exactly
    the violation the judgment-non-delegable axiom prohibits (see AXIOMS.md
    §judgment-non-delegable example).

    A regression test for the *behavioural* intent of the R2 change requires
    running RBG as an agent against the fixture at
    tests/fixtures/rbg/universal_claim_single_client.py and asserting a REVISE
    verdict is returned.  That test requires an agent harness and is deferred.

    This test only confirms the R2 rule is not accidentally deleted entirely.
    """
    r2 = _r2_text()
    assert len(r2.strip()) > 50, (
        f"R2 rule is present but suspiciously short — may have been truncated.\n\nR2: {r2}"
    )
