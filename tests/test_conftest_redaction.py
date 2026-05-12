from tests.conftest import _redact_cmd


def test_redact_env_vars():
    cmd = [
        "docker",
        "run",
        "-e",
        "GH_TOKEN=ghp_secret_token",
        "-e",
        "ANTHROPIC_API_KEY=sk-ant-api03-secret",
        "-e",
        "OTHER_VAR=public_value",
        "ghcr.io/nicsuzor/aops-crew",
    ]
    redacted = _redact_cmd(cmd)

    assert "GH_TOKEN=[REDACTED]" in redacted
    assert "ANTHROPIC_API_KEY=[REDACTED]" in redacted
    assert "OTHER_VAR=public_value" in redacted
    assert "ghp_secret_token" not in " ".join(redacted)
    assert "sk-ant-api03" not in " ".join(redacted)


def test_redact_mount_paths():
    cmd = [
        "docker",
        "run",
        "-v",
        "/home/user/.claude/.credentials.json:/home/worker/.claude/.credentials.json:ro",
        "-v",
        "/tmp/tmp-claude.json:/home/worker/.claude.json",
        "-v",
        "/home/user/workspace:/workspace",
        "ghcr.io/nicsuzor/aops-crew",
    ]
    redacted = _redact_cmd(cmd)

    # Check that host paths are redacted for sensitive destinations
    assert "[REDACTED_PATH]:/home/worker/.claude/.credentials.json:ro" in redacted
    assert "[REDACTED_PATH]:/home/worker/.claude.json" in redacted
    # Public workspace should NOT be redacted
    assert "/home/user/workspace:/workspace" in redacted

    assert "/home/user/.claude" not in " ".join(redacted)
    assert "/tmp/tmp-claude" not in " ".join(redacted)


def test_redact_gemini_mounts():
    cmd = [
        "docker",
        "run",
        "-v",
        "/Users/nic/.gemini/settings.json:/home/worker/.gemini/settings.json:ro",
        "ghcr.io/nicsuzor/aops-crew",
    ]
    redacted = _redact_cmd(cmd)
    assert "[REDACTED_PATH]:/home/worker/.gemini/settings.json:ro" in redacted
