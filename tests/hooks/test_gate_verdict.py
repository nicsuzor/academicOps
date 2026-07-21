"""Verdict merge rule: deny > warn > allow (None)."""

from gates.verdict import Verdict, deny, merge, warn


def test_warn_and_deny_construct_expected_shape():
    assert warn("careful") == Verdict("warn", "careful", None)
    assert deny("no") == Verdict("deny", "no", None)


def test_merge_all_allow_is_none():
    assert merge([None, None, None]) is None


def test_merge_warn_beats_allow():
    result = merge([None, warn("careful"), None])
    assert result == warn("careful")


def test_merge_deny_beats_warn_and_allow():
    result = merge([None, warn("careful"), deny("no")])
    assert result == deny("no")


def test_merge_deny_beats_warn_regardless_of_order():
    result = merge([deny("no"), warn("careful")])
    assert result == deny("no")


def test_merge_first_verdict_wins_ties():
    result = merge([warn("first"), warn("second")])
    assert result == warn("first")


def test_merge_empty_list_is_none():
    assert merge([]) is None
