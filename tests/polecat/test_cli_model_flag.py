#!/usr/bin/env python3
"""Tests for the unified ``--model <name>`` flag and its alias resolver.

The ``--model`` flag is the single canonical mechanism for selecting both
the agent client (claude vs gemini) AND the model id used inside that client.
It replaces the legacy ``--gemini``/``-g`` flag.

These tests cover ``_resolve_model_flag`` directly (the resolver function)
and the CLI surface (``polecat run --help`` / ``polecat crew --help``) to
verify the legacy flag was actually removed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

# Path setup mirrors other tests under tests/polecat/.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from polecat.cli import _resolve_model_flag, main  # noqa: E402


class TestResolveModelFlagAliases:
    """Client-name aliases — primary CORE.md-documented invocation form."""

    def test_none_returns_default_client_no_override(self):
        client, model = _resolve_model_flag(None)
        assert client == "claude"
        assert model is None

    def test_none_with_explicit_default_client(self):
        client, model = _resolve_model_flag(None, default_client="gemini")
        assert client == "gemini"
        assert model is None

    def test_gemini_alias_selects_gemini_client_no_override(self):
        # --model gemini → switch client to gemini, use polecat.yaml gemini_model.
        # This is the canonical CORE.md form.
        client, model = _resolve_model_flag("gemini")
        assert client == "gemini"
        assert model is None  # no override — defer to session_defaults.gemini_model

    def test_claude_alias_selects_claude_client_no_override(self):
        client, model = _resolve_model_flag("claude")
        assert client == "claude"
        assert model is None

    def test_alias_is_case_insensitive(self):
        # Users type whatever — accept both.
        client, model = _resolve_model_flag("Gemini")
        assert client == "gemini"
        client, model = _resolve_model_flag("CLAUDE")
        assert client == "claude"


class TestResolveModelFlagLiteralIds:
    """Literal model ids pass through verbatim with client inferred from prefix."""

    @pytest.mark.parametrize(
        "literal_id,expected_client",
        [
            ("claude-opus-4-7", "claude"),
            ("claude-sonnet-4-6", "claude"),
            ("claude-haiku-4-5", "claude"),
            ("opus-4-7", "claude"),  # post-rebrand short form
            ("sonnet-4-6", "claude"),
            ("haiku-4-5", "claude"),
            ("gemini-2.5-pro", "gemini"),
            ("gemini-1.5-flash", "gemini"),
        ],
    )
    def test_literal_id_infers_client_from_prefix(self, literal_id, expected_client):
        client, model = _resolve_model_flag(literal_id)
        assert client == expected_client
        assert model == literal_id  # passed through verbatim


class TestResolveModelFlagErrors:
    """A8 (no skip / no drift): unknown values must error fast, not silently fall back."""

    def test_empty_string_rejected(self):
        with pytest.raises(click.UsageError) as exc:
            _resolve_model_flag("")
        msg = str(exc.value)
        assert "non-empty" in msg
        assert "claude" in msg  # available aliases mentioned
        assert "gemini" in msg

    def test_whitespace_only_rejected(self):
        with pytest.raises(click.UsageError):
            _resolve_model_flag("   ")

    def test_unknown_alias_rejected_with_available_aliases(self):
        # The previous bug (aops-c54097aa): --opus silently downgraded to default sonnet.
        # The fix: unknown aliases must error and tell the caller what's valid.
        with pytest.raises(click.UsageError) as exc:
            _resolve_model_flag("opus")  # bare 'opus' (no trailing version) is ambiguous
        msg = str(exc.value)
        assert "claude" in msg
        assert "gemini" in msg
        # The error message should name the literal-id prefix convention so
        # the caller knows how to recover.
        assert "claude-" in msg or "opus-" in msg

    def test_unknown_provider_prefix_rejected(self):
        with pytest.raises(click.UsageError):
            _resolve_model_flag("gpt-4")  # OpenAI; not supported by polecat

    def test_garbage_value_rejected(self):
        with pytest.raises(click.UsageError):
            _resolve_model_flag("not-a-real-model")

    def test_model_in_interactive_shell_rejected(self):
        # ``polecat crew -i`` drops into bash — no agent CLI to bind a model to.
        with pytest.raises(click.UsageError) as exc:
            _resolve_model_flag("gemini", interactive_shell=True)
        assert "interactive" in str(exc.value).lower()

    def test_model_none_in_interactive_shell_is_fine(self):
        # No --model flag + -i: legitimate, returns default client and no override.
        client, model = _resolve_model_flag(None, interactive_shell=True)
        assert client == "claude"
        assert model is None


class TestCLISurfaceLegacyFlagRemoved:
    """The legacy ``--gemini``/``-g`` flag is removed (breaking change)."""

    def test_run_help_no_longer_lists_gemini_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        # The OLD flag is gone from the Options section. The literal string
        # `--gemini` may still appear in help body (e.g. "Replaces the
        # legacy --gemini/-g flag") so we check for the option-listing form
        # specifically — click renders options as "  -g, --gemini" or
        # "  --gemini  " at column 2, never inside prose.
        assert "  -g, --gemini" not in result.output
        assert "  --gemini  " not in result.output
        # The NEW flag is documented.
        assert "--model" in result.output

    def test_crew_help_no_longer_lists_gemini_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["crew", "--help"])
        assert result.exit_code == 0
        assert "  -g, --gemini" not in result.output
        assert "  --gemini  " not in result.output
        assert "--model" in result.output

    def test_run_help_documents_alias_resolution(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        # The help text must call out the alias-resolution semantics so a
        # caller reading --help understands what 'claude'/'gemini' do.
        assert "polecat.yaml" in result.output
        assert "claude" in result.output
        assert "gemini" in result.output

    def test_run_rejects_old_gemini_flag(self):
        # Belt and braces: even though the option is gone, this asserts the
        # invocation actually fails (click won't silently accept it).
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--gemini", "-t", "any-task"])
        # Click rejects unknown options with exit code 2.
        assert result.exit_code != 0
        assert "no such option" in result.output.lower() or "--gemini" in result.output
