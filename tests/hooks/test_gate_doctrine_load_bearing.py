#!/usr/bin/env python3
"""Guard test: junior.md must carry the WS7 gate composition & exit doctrine.

Failure mode being guarded: the precedence / never-block / enforcer-channel /
register / turn-vs-session doctrine drifts out of junior.md, leaving the
enforced code (gate_config.py, engine.py) undocumented and unreviewable. The
doctrine is the reviewable half of "gate hygiene" — if it disappears the model
is no longer auditable against the runtime.

Mirrors the load-bearing style of test_pkb_gap_halt_instruction.py.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JUNIOR_MD = REPO_ROOT / "aops-core/agents/junior.md"
AOPS_CORE = REPO_ROOT / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))


def _gates_section() -> str:
    """Return the text of the WS7 Gates section in junior.md."""
    content = JUNIOR_MD.read_text()
    start = content.index("### Gates — composition & exit semantics (WS7)")
    # Section ends at the next heading.
    nxt = content.find("\n### ", start + 1)
    return content[start : nxt if nxt != -1 else len(content)]


def test_gates_section_exists():
    assert "### Gates — composition & exit semantics (WS7)" in JUNIOR_MD.read_text()


def test_section_documents_precedence_order():
    """The documented precedence chain must name all five gates in order."""
    section = _gates_section()
    # Order must read sentinel → enforcer → qa → handover → ida.
    idx = [section.find(g) for g in ("sentinel", "enforcer", "qa", "handover", "ida")]
    assert all(i != -1 for i in idx), "precedence chain must name all five gates"
    assert idx == sorted(idx), "gates must appear in precedence order in the doctrine"


def test_precedence_doctrine_matches_runtime():
    """The doctrine order must match gate_config.GATE_PRECEDENCE (the runtime)."""
    from hooks.gate_config import GATE_PRECEDENCE

    section = _gates_section()
    idx = [section.find(g) for g in GATE_PRECEDENCE]
    assert all(i != -1 for i in idx)
    assert idx == sorted(idx), "junior.md precedence order must match gate_config.GATE_PRECEDENCE"


def test_section_documents_never_block_and_askuserquestion():
    section = _gates_section()
    assert "AskUserQuestion" in section
    assert "never" in section.lower()


def test_section_documents_enforcer_channel_sentinel():
    """The doctrine must name the actual sentinel literal, kept in sync with code."""
    from hooks.gate_config import ENFORCER_CHANNEL_SENTINEL

    assert ENFORCER_CHANNEL_SENTINEL in _gates_section()


def test_section_documents_register_scaling():
    section = _gates_section()
    assert "AOPS_SESSION_REGISTER" in section
    assert "capture" in section


def test_section_documents_turn_vs_session_signal():
    section = _gates_section()
    assert "/dump" in section
    assert "/end_session" in section


def test_section_records_goal_loop_termination_boundary():
    """Item 2's needs-decision boundary must be recorded, not silently dropped."""
    section = _gates_section()
    assert "done-pending-Nic" in section
    assert "no `/goal`/`/loop` continuation Stop hook" in section
