"""Tests for user-scoped rule loading via COPE_USER_RULES_DIR.

Guards the behaviour specified in specs/enforcement/user-rules.md:
- AC-BUILD-1: Valid user rules with trigger: always_on load with layer=3
- AC-BUILD-2: Unset environment variable is silent with 0 user rules
- AC-BUILD-3: Non-existent directory warns on stderr with DEGRADED: cope-rules
- AC-BUILD-4: User rules cannot shadow or override axioms or project rules
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RBG_PLUGIN_ROOT = REPO_ROOT / "plugins" / "rbg"
RULES_PY = RBG_PLUGIN_ROOT / "hooks" / "rules.py"
POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"


def _load_rules_module():
    spec = importlib.util.spec_from_file_location("rbg_rules_test", RULES_PY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rbg_rules_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_user_rules_env_var() -> str:
    policy = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
    return policy["rbg"]["rules"]["user_rules_env"]


@pytest.fixture
def rules_mod():
    return _load_rules_module()


def test_user_rules_load_when_dir_configured(rules_mod, tmp_path, monkeypatch):
    """AC-BUILD-1: Given COPE_USER_RULES_DIR points to an existing directory

    containing Markdown files with trigger: always_on, when rules.load() runs,
    all such rules are returned with layer=3.
    """
    env_var = _get_user_rules_env_var()
    user_rules_dir = tmp_path / "user_rules"
    user_rules_dir.mkdir()
    rule_file = user_rules_dir / "custom-user-rule.md"
    rule_file.write_text(
        "---\ntrigger: always_on\ndescription: A user rule\n---\nUser rule body policy.",
        encoding="utf-8",
    )

    monkeypatch.setenv(env_var, str(user_rules_dir))
    # Ensure legacy env is clean
    monkeypatch.delenv("ACA_DATA", raising=False)

    loaded = rules_mod.load(RBG_PLUGIN_ROOT, tmp_path)
    assert "custom-user-rule" in loaded
    rule = loaded["custom-user-rule"]
    assert rule.layer == 3
    assert rule.trigger == "always_on"
    assert rule.body == "User rule body policy."


def test_user_rules_silent_when_unset(rules_mod, tmp_path, monkeypatch, capsys):
    """AC-BUILD-2: Given COPE_USER_RULES_DIR is unset, when rules.load() runs,

    then zero layer-3 rules are returned and stderr contains no degradation warnings.
    """
    env_var = _get_user_rules_env_var()
    monkeypatch.delenv(env_var, raising=False)
    monkeypatch.delenv("ACA_DATA", raising=False)

    loaded = rules_mod.load(RBG_PLUGIN_ROOT, tmp_path)
    user_rules = [r for r in loaded.values() if r.layer == 3]
    assert user_rules == []

    captured = capsys.readouterr()
    assert "DEGRADED:" not in captured.err


def test_user_rules_degraded_when_nonexistent_dir(rules_mod, tmp_path, monkeypatch, capsys):
    """AC-BUILD-3: Given COPE_USER_RULES_DIR is set to a non-existent path,

    when rules.load() runs, then stderr contains DEGRADED: cope-rules and
    rules.load() returns loaded axioms and project rules without raising exceptions.
    """
    env_var = _get_user_rules_env_var()
    nonexistent = tmp_path / "does_not_exist"
    monkeypatch.setenv(env_var, str(nonexistent))
    monkeypatch.delenv("ACA_DATA", raising=False)

    loaded = rules_mod.load(RBG_PLUGIN_ROOT, tmp_path)
    # Axioms should still be loaded
    assert "proportionate" in loaded
    # User rules are empty
    assert [r for r in loaded.values() if r.layer == 3] == []

    captured = capsys.readouterr()
    assert "DEGRADED:" in captured.err
    assert "cope-rules" in captured.err


def test_user_rules_precedence_cannot_override_earlier_scopes(rules_mod, tmp_path, monkeypatch):
    """AC-BUILD-4: Given a rule in COPE_USER_RULES_DIR shares a slug with an

    axiom or project rule, the axiom or project rule wins and user rule does not override.
    """
    env_var = _get_user_rules_env_var()
    user_rules_dir = tmp_path / "user_rules"
    user_rules_dir.mkdir()

    # Collision with an axiom: "proportionate"
    shadow_axiom = user_rules_dir / "proportionate.md"
    shadow_axiom.write_text("---\ntrigger: always_on\n---\nShadowed axiom body.", encoding="utf-8")

    # Collision with a project rule: "local-rule"
    project_rules_dir = tmp_path / ".agents" / "rules"
    project_rules_dir.mkdir(parents=True)
    local_rule = project_rules_dir / "local-rule.md"
    local_rule.write_text("---\ntrigger: always_on\n---\nProject rule body.", encoding="utf-8")
    shadow_local = user_rules_dir / "local-rule.md"
    shadow_local.write_text(
        "---\ntrigger: always_on\n---\nShadowed project body.", encoding="utf-8"
    )

    monkeypatch.setenv(env_var, str(user_rules_dir))
    monkeypatch.delenv("ACA_DATA", raising=False)

    loaded = rules_mod.load(RBG_PLUGIN_ROOT, tmp_path)
    assert loaded["proportionate"].layer == 1
    assert loaded["proportionate"].body != "Shadowed axiom body."

    assert loaded["local-rule"].layer == 2
    assert loaded["local-rule"].body == "Project rule body."


def test_zero_legacy_references_in_governed_surfaces():
    """AC-BUILD-5: A recursive search across plugins/rbg/, specs/enforcement/

    (excluding user-rules.md), specs/ENFORCEMENT-MAP.md, and
    plugins/ida/skills/workflow-library/workflows/wf-rbg.md returns zero occurrences
    of the legacy ACA_DATA variable.
    """
    surfaces = [
        REPO_ROOT / "plugins" / "rbg",
        REPO_ROOT / "specs" / "ENFORCEMENT-MAP.md",
        REPO_ROOT / "plugins" / "ida" / "skills" / "workflow-library" / "workflows" / "wf-rbg.md",
    ]
    for path in surfaces:
        if path.is_file():
            assert "ACA_DATA" not in path.read_text(encoding="utf-8"), f"Legacy reference in {path}"
        elif path.is_dir():
            for f in path.rglob("*"):
                if f.is_file() and not f.name.endswith((".pyc", ".pyo")):
                    assert "ACA_DATA" not in f.read_text(encoding="utf-8"), (
                        f"Legacy reference in {f}"
                    )

    for f in (REPO_ROOT / "specs" / "enforcement").glob("*.md"):
        if f.name != "user-rules.md":
            assert "ACA_DATA" not in f.read_text(encoding="utf-8"), f"Legacy reference in {f}"
