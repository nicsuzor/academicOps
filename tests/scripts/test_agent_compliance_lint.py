"""Tests for aops-core/scripts/agent_compliance_lint.py."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT_PATH = REPO_ROOT / "aops-core" / "scripts" / "agent_compliance_lint.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agent_compliance_lint", LINT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_compliance_lint"] = mod
    spec.loader.exec_module(mod)
    return mod


lint = _load_module()


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

CLEAN_AGENT = """---
name: clean
tools:
  - Read
  - Edit
  - Bash
bash_scopes:
  - git:read
  - pytest
file_access:
  read:
    - "**/*.py"
  write:
    - "src/**/*.py"
---

Body text.
"""

BASH_NO_SCOPES = """---
name: bash-no-scope
tools:
  - Bash
---

body
"""

READ_NO_FA = """---
name: read-no-fa
tools:
  - Read
---

body
"""

EDIT_NO_WRITE_FA = """---
name: edit-no-write-fa
tools:
  - Read
  - Edit
file_access:
  read:
    - "**/*.py"
---

body
"""

UNKNOWN_SCOPE = """---
name: unknown-scope
tools:
  - Bash
bash_scopes:
  - foo:bar
---

body
"""

UNRESTRICTED = """---
name: unrestricted
tools:
  - Bash
bash_scopes:
  - unrestricted
---

body
"""

NO_TOOLS = """---
name: no-tools
description: an agent
---

body
"""

NO_FRONTMATTER = """This file has no frontmatter at all.

Body only.
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_passes_clean_agent(tmp_path: Path):
    f = _write(tmp_path, "clean", CLEAN_AGENT)
    violations = lint.lint_file(f)
    assert violations == [], f"expected no violations, got: {violations}"


def test_bash_without_scopes_fails(tmp_path: Path):
    f = _write(tmp_path, "a", BASH_NO_SCOPES)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R1", "error") in rules


def test_filesystem_without_file_access_fails(tmp_path: Path):
    f = _write(tmp_path, "a", READ_NO_FA)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R2", "error") in rules


def test_write_without_file_access_write_fails(tmp_path: Path):
    f = _write(tmp_path, "a", EDIT_NO_WRITE_FA)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R3", "error") in rules
    # R2 should NOT fire (read globs are present)
    assert ("R2", "error") not in rules


def test_unknown_bash_scope_fails(tmp_path: Path):
    f = _write(tmp_path, "a", UNKNOWN_SCOPE)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R4", "error") in rules


def test_unrestricted_warns(tmp_path: Path):
    f = _write(tmp_path, "a", UNRESTRICTED)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R5", "warning") in rules
    # No errors here
    assert not any(v.level == "error" for v in violations)

    # Exit code: normally 0, --strict makes it 1
    rc_normal = lint.main([str(f)])
    assert rc_normal == 0
    rc_strict = lint.main([str(f), "--strict"])
    assert rc_strict == 1


def test_missing_tools_fails(tmp_path: Path):
    f = _write(tmp_path, "a", NO_TOOLS)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R6", "error") in rules


def test_no_frontmatter_fails(tmp_path: Path):
    f = _write(tmp_path, "a", NO_FRONTMATTER)
    violations = lint.lint_file(f)
    rules = {(v.rule, v.level) for v in violations}
    assert ("R6", "error") in rules


def test_json_output_shape(tmp_path: Path):
    f = _write(tmp_path, "a", BASH_NO_SCOPES)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main([str(f), "--format", "json"])
    assert rc == 1
    payload = json.loads(buf.getvalue())
    assert "violations" in payload
    assert "summary" in payload
    assert set(payload["summary"].keys()) == {"errors", "warnings", "files_checked"}
    assert payload["summary"]["files_checked"] == 1
    assert payload["summary"]["errors"] >= 1
    # Each violation has expected keys
    for v in payload["violations"]:
        assert set(v.keys()) >= {"file", "line", "level", "rule", "msg"}


def test_default_paths_walked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Build a fake repo with the default-path layout
    (tmp_path / "aops-core" / "agents").mkdir(parents=True)
    (tmp_path / ".github" / "agents").mkdir(parents=True)
    a = tmp_path / "aops-core" / "agents" / "x.md"
    a.write_text(BASH_NO_SCOPES, encoding="utf-8")
    b = tmp_path / ".github" / "agents" / "y.agent.md"
    b.write_text(CLEAN_AGENT, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main(["--format", "json"])
    payload = json.loads(buf.getvalue())
    assert payload["summary"]["files_checked"] == 2
    # x.md should produce R1
    assert any("R1" == v["rule"] for v in payload["violations"])
    assert rc == 1


def test_quiet_text_suppresses_per_violation(tmp_path: Path):
    f = _write(tmp_path, "a", BASH_NO_SCOPES)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main([str(f), "--quiet"])
    assert rc == 1
    out = buf.getvalue()
    # No per-violation line should appear
    assert "R1" not in out
    assert "agent-compliance-lint:" in out


def test_violation_format_text(tmp_path: Path):
    f = _write(tmp_path, "a", BASH_NO_SCOPES)
    violations = lint.lint_file(f)
    assert violations
    line = violations[0].format_text()
    assert str(f) in line
    assert "error" in line or "warning" in line
    assert ":" in line


GHA_EXEMPT_MINIMAL = """---
name: merge-prep
description: A GitHub Actions runner agent.
runtime: github-actions
---

Body — has no `tools:` field, but is exempt from four-axes checks.
"""


GHA_EXEMPT_BAD_FRONTMATTER = """name: not-a-yaml-block
runtime: github-actions
"""


def test_runtime_github_actions_exempt(tmp_path: Path):
    """runtime: github-actions skips R1-R7 even with no tools, no scopes, etc."""
    f = _write(tmp_path, "merge-prep.agent", GHA_EXEMPT_MINIMAL)
    violations = lint.lint_file(f)
    assert violations == [], (
        f"runtime: github-actions should exempt all four-axes rules, "
        f"got: {[v.rule for v in violations]}"
    )


def test_runtime_exemption_still_requires_parseable_frontmatter(tmp_path: Path):
    """An exempt file still needs valid frontmatter — R6 broken-frontmatter applies."""
    f = _write(tmp_path, "broken", GHA_EXEMPT_BAD_FRONTMATTER)
    violations = lint.lint_file(f)
    assert any(v.rule == "R6" for v in violations), (
        "missing frontmatter should still trip R6 even for would-be exempt files"
    )
