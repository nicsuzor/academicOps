"""Tests for the axiom detector."""

from __future__ import annotations

from lib.axiom_detector import P8FallbackDetector


def test_p8_env_get_default():
    detector = P8FallbackDetector()
    code = 'aops_path = os.environ.get("AOPS", "/home/nic/src/aops")'
    violations = detector.detect(code)
    # Both env_get_default and dict_get_default match
    assert len(violations) >= 1
    patterns = {v.pattern_name for v in violations}
    assert "env_get_default" in patterns


def test_p8_except_pass():
    detector = P8FallbackDetector()
    code = """
try:
    do_something()
except Exception:
    pass
"""
    violations = detector.detect(code)
    assert len(violations) == 1
    assert violations[0].pattern_name == "except_pass"


def test_p8_dict_get_default():
    detector = P8FallbackDetector()
    code = 'config.get("timeout", 30)'
    violations = detector.detect(code)
    assert len(violations) == 1
    assert violations[0].pattern_name == "dict_get_default"

    # Should NOT trigger for None or empty containers (per regex)
    code_ok = 'config.get("timeout", None)'
    assert len(detector.detect(code_ok)) == 0


def test_p8_or_fallback():
    detector = P8FallbackDetector()
    code = 'path = custom_path or "/tmp"'
    violations = detector.detect(code)
    assert len(violations) == 1
    assert violations[0].pattern_name == "or_fallback"


def test_multiple_violations():
    detector = P8FallbackDetector()
    code = """
def setup():
    try:
        path = os.getenv("PATH", "/usr/bin")
    except:
        pass
    return path or "/bin"
"""
    violations = detector.detect(code)
    # env_get_default, except_pass, assign_or_fallback
    assert len(violations) == 3
    patterns = {v.pattern_name for v in violations}
    assert "env_get_default" in patterns
    assert "except_pass" in patterns
    assert "or_fallback" in patterns
    
