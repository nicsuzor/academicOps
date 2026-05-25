import pytest

from polecat.bootstrap import BootstrapError, validate_bootstrap
from polecat.cli import _require_pkb_url_or_exit


def test_require_pkb_url_exits_4_with_friendly_message(monkeypatch, capsys):
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        _require_pkb_url_or_exit()
    assert exc.value.code == 4
    err = capsys.readouterr().err
    assert "PKB_MCP_URL is not set" in err
    assert "export PKB_MCP_URL=" in err
    assert "Traceback" not in err


def test_require_pkb_url_noop_when_set(monkeypatch):
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    _require_pkb_url_or_exit()  # should not raise


def test_validate_bootstrap_missing_aops(tmp_path, monkeypatch):
    monkeypatch.delenv("AOPS", raising=False)
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    with pytest.raises(BootstrapError) as exc:
        validate_bootstrap(aops_path=None)

    assert "Missing required environment variable: AOPS" in str(exc.value)


def test_validate_bootstrap_missing_polecat_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS", str(tmp_path))
    monkeypatch.delenv("POLECAT_HOME", raising=False)
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    with pytest.raises(BootstrapError) as exc:
        validate_bootstrap()

    assert "Missing required environment variable: POLECAT_HOME" in str(exc.value)


def test_validate_bootstrap_missing_pkb_url(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS", str(tmp_path))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    with pytest.raises(BootstrapError) as exc:
        validate_bootstrap()

    assert "Missing required environment variable: PKB_MCP_URL" in str(exc.value)


def test_validate_bootstrap_missing_axioms(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS", str(tmp_path))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    # Mock socket connection to avoid real network calls
    import socket
    from unittest.mock import MagicMock

    monkeypatch.setattr(socket, "create_connection", lambda address, timeout=None: MagicMock())

    # Mock pkb_bridge client initialization
    import polecat.pkb_bridge

    monkeypatch.setattr(polecat.pkb_bridge, "_get_client", lambda: MagicMock())

    with pytest.raises(BootstrapError) as exc:
        validate_bootstrap()

    assert "Axioms file missing" in str(exc.value)


def test_validate_bootstrap_missing_skills(tmp_path, monkeypatch):
    aops_dir = tmp_path / "aops"
    aops_dir.mkdir()
    (aops_dir / "aops-core").mkdir()
    (aops_dir / "aops-core" / "AXIOMS.md").touch()

    monkeypatch.setenv("AOPS", str(aops_dir))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    # Mock socket connection
    import socket
    from unittest.mock import MagicMock

    monkeypatch.setattr(socket, "create_connection", lambda addr, timeout=None: MagicMock())

    # Mock pkb_bridge client initialization
    import polecat.pkb_bridge

    monkeypatch.setattr(polecat.pkb_bridge, "_get_client", lambda: MagicMock())

    with pytest.raises(BootstrapError) as exc:
        validate_bootstrap()

    assert "Skills directory missing" in str(exc.value)


def test_validate_bootstrap_success(tmp_path, monkeypatch):
    aops_dir = tmp_path / "aops"
    aops_dir.mkdir()
    (aops_dir / "aops-core").mkdir()
    (aops_dir / "aops-core" / "AXIOMS.md").touch()
    (aops_dir / "aops-core" / "skills").mkdir()
    (aops_dir / "aops-core" / "skills" / "sleep").mkdir()
    (aops_dir / "aops-core" / "skills" / "sleep" / "SKILL.md").touch()

    monkeypatch.setenv("AOPS", str(aops_dir))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "fake-token")

    # Mock socket connection
    import socket
    from unittest.mock import MagicMock

    monkeypatch.setattr(socket, "create_connection", lambda addr, timeout=None: MagicMock())

    # Mock pkb_bridge client initialization
    import polecat.pkb_bridge

    monkeypatch.setattr(polecat.pkb_bridge, "_get_client", lambda: MagicMock())

    # Should not raise
    validate_bootstrap()
