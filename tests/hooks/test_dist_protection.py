"""Tests for credential path protection in policy_enforcer.py.

Verifies that validate_credential_protection() blocks Bash read commands
targeting sensitive credential paths while allowing normal commands.

Run with:
    uv run pytest tests/hooks/test_dist_protection.py -v
"""

import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.policy_enforcer import validate_credential_protection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _blocked(tool_name: str, command: str) -> bool:
    result = validate_credential_protection(tool_name, {"command": command})
    return result is not None and result.get("continue") is False


def _allowed(tool_name: str, command: str) -> bool:
    return validate_credential_protection(tool_name, {"command": command}) is None


# ---------------------------------------------------------------------------
# Acceptance criteria: commands that MUST be blocked
# ---------------------------------------------------------------------------


class TestCredentialPathsBlocked:
    def test_cat_gh_hosts(self):
        """cat ~/.config/gh/hosts.yml blocked with clear message."""
        result = validate_credential_protection("Bash", {"command": "cat ~/.config/gh/hosts.yml"})
        assert result is not None
        assert result.get("continue") is False
        msg = result.get("systemMessage", "")
        assert "BLOCKED" in msg
        assert "credential" in msg.lower() or "Read tool" in msg

    def test_grep_token_claude_settings(self):
        """grep token ~/.claude/settings.json blocked."""
        assert _blocked("Bash", "grep token ~/.claude/settings.json")

    def test_cat_gh_config_dir(self):
        assert _blocked("Bash", "cat ~/.config/gh/config.yml")

    def test_head_gh_hosts(self):
        assert _blocked("Bash", "head ~/.config/gh/hosts.yml")

    def test_tail_gh_hosts(self):
        assert _blocked("Bash", "tail -n 5 ~/.config/gh/hosts.yml")

    def test_less_gh_hosts(self):
        assert _blocked("Bash", "less ~/.config/gh/hosts.yml")

    def test_more_gh_hosts(self):
        assert _blocked("Bash", "more ~/.config/gh/hosts.yml")

    def test_strings_gh_hosts(self):
        assert _blocked("Bash", "strings ~/.config/gh/hosts.yml")

    def test_cat_claude_json(self):
        assert _blocked("Bash", "cat ~/.claude/settings.json")

    def test_cat_claude_json_absolute_home(self):
        assert _blocked("Bash", "cat /home/user/.claude/settings.json")

    def test_cat_ssh_key(self):
        assert _blocked("Bash", "cat ~/.ssh/id_rsa")

    def test_cat_ssh_dir_absolute(self):
        assert _blocked("Bash", "cat /home/worker/.ssh/id_ed25519")

    def test_grep_oauth_token_file(self):
        assert _blocked("Bash", "grep secret ./oauth_token")

    def test_cat_dot_oauth_file(self):
        assert _blocked("Bash", "cat .oauth_credentials")

    def test_cat_root_gh(self):
        assert _blocked("Bash", "cat /root/.config/gh/hosts.yml")

    def test_cat_root_ssh(self):
        assert _blocked("Bash", "cat /root/.ssh/id_rsa")


# ---------------------------------------------------------------------------
# Acceptance criteria: normal commands MUST be unaffected
# ---------------------------------------------------------------------------


class TestNormalCommandsAllowed:
    def test_ls_tmp(self):
        assert _allowed("Bash", "ls /tmp")

    def test_cat_project_file(self):
        assert _allowed("Bash", "cat /workspace/README.md")

    def test_git_status(self):
        assert _allowed("Bash", "git status")

    def test_grep_in_src(self):
        assert _allowed("Bash", "grep -r 'token' /workspace/src/")

    def test_cat_etc_hosts(self):
        # /etc/hosts is not a credential path
        assert _allowed("Bash", "cat /etc/hosts")

    def test_echo_command(self):
        assert _allowed("Bash", "echo hello")

    def test_python_script(self):
        assert _allowed("Bash", "python script.py")

    def test_grep_in_logs(self):
        assert _allowed("Bash", "grep error /var/log/app.log")

    def test_cat_relative_json(self):
        # A project-local .json that isn't a credential path
        assert _allowed("Bash", "cat ./config/app.json")


# ---------------------------------------------------------------------------
# Non-Bash tools are always allowed
# ---------------------------------------------------------------------------


class TestNonBashToolsIgnored:
    def test_read_tool_ignored(self):
        result = validate_credential_protection("Read", {"file_path": "~/.config/gh/hosts.yml"})
        assert result is None

    def test_write_tool_ignored(self):
        result = validate_credential_protection("Write", {"file_path": "~/.claude/settings.json"})
        assert result is None

    def test_edit_tool_ignored(self):
        result = validate_credential_protection("Edit", {"file_path": "~/.ssh/known_hosts"})
        assert result is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_command_raises(self):
        with pytest.raises(ValueError, match="command"):
            validate_credential_protection("Bash", {})

    def test_empty_command_allowed(self):
        # Empty command has no read utility, so should pass
        assert _allowed("Bash", "")

    def test_cat_inside_quoted_string_not_blocked(self):
        # "cat" inside a quoted echo argument doesn't execute, so it must be allowed
        assert _allowed("Bash", "echo 'cat ~/.config/gh/hosts.yml'")

    def test_semicolon_separator_blocked(self):
        # `; cat` is a real execution path — must be caught
        assert _blocked("Bash", "echo x; cat ~/.ssh/id_rsa")

    def test_and_separator_blocked(self):
        assert _blocked("Bash", "echo x && cat ~/.ssh/id_rsa")

    def test_pipe_separator_blocked(self):
        assert _blocked("Bash", "echo x | cat ~/.config/gh/hosts.yml")

    def test_multiline_bash_with_cat_at_start_of_line(self):
        # A multiline Bash command where cat is at the start of a new line
        assert _blocked("Bash", "ls /tmp\ncat ~/.config/gh/hosts.yml")

    def test_case_insensitive_command(self):
        # Shell commands are case-sensitive, but regex should match uppercase too
        # (defensive: regex uses IGNORECASE flag)
        assert _blocked("Bash", "CAT ~/.config/gh/hosts.yml")
