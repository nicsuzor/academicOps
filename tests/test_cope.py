"""Tests for the CoPE rule check, which ships in the rbg plugin (plugins/rbg/).

The plugin directory was `plugins/cope/` until it was renamed to `plugins/rbg/`
(e3a8bd39, 8edff6fa); the three modules under test — rules.py, evaluator.py,
handlers.py — moved with it unchanged in name and surface. The environment
variables, the `DEGRADED_*` kind strings, and the message files are still
CoPE's, so the vocabulary below is unchanged.

The `PreToolUse` hook is advisory-only rule enforcement — nothing in-session
blocks on its verdict (specs/ARCHITECTURE.md, Enforcement). The judgment itself
is a small language model's, reached over the Reflexes evaluator contract: one
rule in, one label back. The plugin composes the question and reports the
answer; it never decides what a rule means by matching text against a pattern.

These tests exercise the real plugin source: rules.py's three-layer loading and
its graceful degradation, evaluator.py's configuration gate and both wire
protocols, handlers.py's advisory composition and its fail-open behaviour, and
the whole thing end to end through lib/hooks/dispatch.py against a real
loopback HTTP evaluator — simulating build stage 1's shared injection, where
lib/hooks/*.py and plugins/rbg/hooks/*.py land in one directory.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_LIB_AXIOMS = _REPO_ROOT / "lib" / "axioms"
_COPE_HOOKS = _REPO_ROOT / "plugins" / "rbg" / "hooks"

for _dir in (_LIB_HOOKS, _COPE_HOOKS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import evaluator  # noqa: E402  (plugins/rbg/hooks/evaluator.py)
import evaluator_otel_trace  # noqa: E402  (plugins/rbg/hooks/evaluator_otel_trace.py)
import evaluator_trace  # noqa: E402  (plugins/rbg/hooks/evaluator_trace.py)
import handlers  # noqa: E402  (plugins/rbg/hooks/handlers.py)
import rules  # noqa: E402  (plugins/rbg/hooks/rules.py)
from dispatch import HookContext, Kind, warn  # noqa: E402

# Every environment variable cope reads for its evaluator, named once because
# both the isolation fixture and the README-truthfulness test need the set.
_COPE_ENV = (
    "COPE_EVALUATOR_URL",
    "COPE_EVALUATOR_PROTOCOL",
    "COPE_EVALUATOR_MODEL",
    "COPE_EVALUATOR_API_KEY",
    "COPE_EVALUATOR_TIMEOUT",
    "COPE_EVALUATOR_TRACE_PATH",
    "COPE_EVALUATOR_OTEL_TRACE_PATH",
)

# A port nothing listens on. Every in-process test that uses it also replaces
# the transport, so reaching it at all is the bug the assertion catches.
_DEAD_URL = "http://127.0.0.1:1/label"


# Both routes a value can arrive by: the plain variable, and the userConfig
# option Claude Code exports as CLAUDE_PLUGIN_OPTION_<KEY>.
_COPE_ENV_ALL = _COPE_ENV + tuple(f"CLAUDE_PLUGIN_OPTION_{name}" for name in _COPE_ENV)


@pytest.fixture(autouse=True)
def _isolate_cope_environment(monkeypatch):
    """No test inherits a developer's real evaluator configuration, and none
    leaks one to the next. Unconfigured is the default state under test, by
    both routes."""
    for name in _COPE_ENV_ALL:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _isolate_temp_directory(monkeypatch, tmp_path):
    """Nothing this plugin writes may land in the shared OS temp directory,
    where it could cross into another test or another run. Kept as a floor even
    though the current runtime keeps no on-disk state of its own: a subprocess
    below that starts writing one must not do it in a shared location."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))


@pytest.fixture(autouse=True)
def _reset_handlers_cache():
    """handlers.py caches the loaded rule set at module scope for the life
    of one hook process (see its docstring). In-process tests must reset
    that cache between cases or they'd see the previous test's rule set."""
    handlers._rules_cache = None
    yield
    handlers._rules_cache = None


def _ctx(
    hooks_dir: Path,
    *,
    tool: str = "",
    command: str = "",
    raw: dict | None = None,
    cwd: Path | None = None,
    client: str = "claude",
    event: str = "PreToolUse",
) -> HookContext:
    raw = dict(raw or {})
    raw.setdefault("tool_name", tool)
    if command:
        raw.setdefault("tool_input", {"command": command})
    if cwd is not None:
        raw.setdefault("cwd", str(cwd))
    return HookContext(
        client=client,
        event=event,
        tool=tool,
        command=command,
        session_id="test-session",
        raw=raw,
        hooks_dir=hooks_dir,
    )


def _configure(monkeypatch, **overrides) -> None:
    """Set a complete, syntactically valid evaluator configuration."""
    settings = {
        "COPE_EVALUATOR_URL": _DEAD_URL,
        "COPE_EVALUATOR_PROTOCOL": "cope",
        "COPE_EVALUATOR_MODEL": "test-model",
        **overrides,
    }
    for name, value in settings.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


# ---------------------------------------------------------------------------
# rules.py: three-layer loading + graceful degradation
# ---------------------------------------------------------------------------


@pytest.fixture()
def plugin_root(tmp_path):
    root = tmp_path / "plugin"
    (root / "axioms").mkdir(parents=True)
    (root / "axioms" / "bounded-execution.md").write_text(
        "---\ntrigger: always_on\ndescription: floor rule\n---\n\nFloor body.\n"
    )
    return root


def test_layer1_axioms_always_loads(plugin_root, tmp_path):
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert "bounded-execution" in loaded
    assert loaded["bounded-execution"].layer == 1


def test_rule_carries_its_body_with_frontmatter_stripped(plugin_root, tmp_path):
    """The body is the policy sent to the evaluator. Reflexes sends the whole
    document with frontmatter stripped, so the loader has to strip it — a
    policy carrying `trigger: always_on` would be asking the model to classify
    our own bookkeeping."""
    loaded = rules.load(plugin_root, tmp_path / "project")
    body = loaded["bounded-execution"].body
    assert body == "Floor body."
    assert "trigger:" not in body
    assert "description:" not in body


def test_rule_body_survives_frontmatter_carrying_only_the_marker(plugin_root, tmp_path):
    """Frontmatter with no description still strips cleanly — the body is the
    policy, and it must not arrive with a stray `---` or the marker line."""
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "house-style.md").write_text(
        "---\ntrigger: always_on\n---\n\nSentence case in headings.\n"
    )
    loaded = rules.load(plugin_root, cwd)
    assert loaded["house-style"].body == "Sentence case in headings."


def test_every_real_axiom_has_a_non_empty_body(tmp_path):
    """Against the real lib/axioms/: an axiom loaded with an empty body would
    be sent to the evaluator as an empty policy and silently classify nothing."""
    root = tmp_path / "plugin"
    shutil.copytree(_LIB_AXIOMS, root / "axioms")
    loaded = rules.load(root, tmp_path / "project")
    assert loaded
    for rule in loaded.values():
        assert rule.body.strip(), f"{rule.slug} loaded with an empty body"


def test_layer2_and_layer3_absent_degrades_to_layer1_only(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    loaded = rules.load(plugin_root, tmp_path / "project")  # no .agents/rules dir at all
    assert set(loaded) == {"bounded-execution"}


def test_layer2_project_rules_add_new_slugs(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "costly-ops-approval.md").write_text(
        "---\ntrigger: always_on\ndescription: project rule\n---\n\nBody.\n"
    )
    loaded = rules.load(plugin_root, cwd)
    assert set(loaded) == {"bounded-execution", "costly-ops-approval"}
    assert loaded["costly-ops-approval"].layer == 2


def test_layer3_user_rules_require_aca_data_env(plugin_root, tmp_path, monkeypatch):
    aca_data = tmp_path / "pkb"
    (aca_data / ".agents" / "rules").mkdir(parents=True)
    (aca_data / ".agents" / "rules" / "data-boundaries.md").write_text(
        "---\ntrigger: always_on\ndescription: user rule\n---\n\nBody.\n"
    )
    monkeypatch.setenv("ACA_DATA", str(aca_data))
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert "data-boundaries" in loaded
    assert loaded["data-boundaries"].layer == 3


def test_missing_aca_data_env_is_not_an_error(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert loaded  # layer 1 still loaded — no exception


def test_layer_cannot_override_an_axiom(plugin_root, tmp_path, monkeypatch):
    """A project-local file reusing an axiom's filename cannot replace the
    axiom's entry — layer 1 always wins a slug collision, so a later layer
    can only add obligations, never weaken one."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "bounded-execution.md").write_text(
        "---\ntrigger: always_on\ndescription: attempted override\n---\n\nWeaker body.\n"
    )
    loaded = rules.load(plugin_root, cwd)
    assert loaded["bounded-execution"].layer == 1
    assert loaded["bounded-execution"].description == "floor rule"
    assert loaded["bounded-execution"].body == "Floor body."


def test_layer1_skips_axiom_dir_files_that_are_not_always_on(plugin_root, tmp_path, monkeypatch):
    """The shipped axioms/ directory also carries index and companion docs
    (README.md, AXIOMS-REVIEW.md). They are reference material, not rules —
    the same line build/axioms.py draws — so they must never reach the
    evaluator as policies."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    (plugin_root / "axioms" / "README.md").write_text(
        "---\ndescription: Index of the axioms.\n---\n\nNot a rule.\n"
    )
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert set(loaded) == {"bounded-execution"}


def test_layer1_loads_only_always_on_from_the_real_axioms_dir(tmp_path, monkeypatch):
    """Against the real lib/axioms/, not a synthetic one: every rule loaded at
    layer 1 declares trigger: always_on, and the index docs are absent."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    plugin_root = tmp_path / "plugin"
    shutil.copytree(_LIB_AXIOMS, plugin_root / "axioms")
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert loaded
    assert all(rule.trigger == "always_on" for rule in loaded.values())
    assert "README" not in loaded
    assert "AXIOMS-REVIEW" not in loaded


def test_layer2_requires_always_on_and_names_what_it_skipped(
    plugin_root, tmp_path, monkeypatch, capsys
):
    """A project's .agents/rules/ holds reference material as well as policies
    — a path table, a note-taking convention, an empty stub. Only a policy can
    be classified, so only the marked file is sent to the evaluator. The rest
    are named on stderr: the drop is the point, being quiet about it is not."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    rules_dir = cwd / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "costly-ops-approval.md").write_text(
        "---\ntrigger: always_on\ndescription: project rule\n---\n\nAsk first.\n"
    )
    (rules_dir / "where-things-live.md").write_text("| dir | holds |\n| --- | ----- |\n")
    (rules_dir / "empty.md").write_text("")

    loaded = rules.load(plugin_root, cwd)
    assert set(loaded) == {"bounded-execution", "costly-ops-approval"}

    err = capsys.readouterr().err
    assert "where-things-live.md" in err
    assert "empty.md" in err
    assert "trigger: always_on" in err
    assert str(rules_dir) in err
    assert "costly-ops-approval.md" not in err  # the rule that loaded is not a complaint


def test_layer3_requires_always_on_and_names_what_it_skipped(
    plugin_root, tmp_path, monkeypatch, capsys
):
    """Same contract in the user's own layer, which is where the reference
    documents actually accumulate."""
    aca_data = tmp_path / "pkb"
    rules_dir = aca_data / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "data-boundaries.md").write_text(
        "---\ntrigger: always_on\ndescription: user rule\n---\n\nBody.\n"
    )
    (rules_dir / "note-conventions.md").write_text("---\ndescription: how I file notes\n---\n\nx\n")
    monkeypatch.setenv("ACA_DATA", str(aca_data))

    loaded = rules.load(plugin_root, tmp_path / "project")
    assert set(loaded) == {"bounded-execution", "data-boundaries"}

    err = capsys.readouterr().err
    assert "note-conventions.md" in err
    assert str(rules_dir) in err


def test_layer1_skipped_index_docs_are_not_reported(plugin_root, tmp_path, monkeypatch, capsys):
    """The shipped axioms/ directory's non-rule files are a known, curated set
    nobody in the session can act on. Naming them on every tool call would be
    noise, which is how a real report gets ignored."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    (plugin_root / "axioms" / "README.md").write_text(
        "---\ndescription: Index of the axioms.\n---\n\nNot a rule.\n"
    )
    rules.load(plugin_root, tmp_path / "project")
    assert capsys.readouterr().err == ""


def test_aca_data_set_but_rules_directory_missing_is_reported(
    plugin_root, tmp_path, monkeypatch, capsys
):
    """Setting ACA_DATA is a claim that the layer exists. A path that names no
    .agents/rules/ directory is a configuration mistake — the layer vanishing
    without a word is how a whole rules layer gets lost."""
    aca_data = tmp_path / "pkb"
    aca_data.mkdir()  # exists, but carries no .agents/rules/
    monkeypatch.setenv("ACA_DATA", str(aca_data))

    loaded = rules.load(plugin_root, tmp_path / "project")
    assert set(loaded) == {"bounded-execution"}  # still fails open to what did load

    err = capsys.readouterr().err
    assert str(aca_data / ".agents" / "rules") in err
    assert "ACA_DATA" in err


def test_absent_layers_that_are_not_mistakes_stay_silent(
    plugin_root, tmp_path, monkeypatch, capsys
):
    """ACA_DATA unset is a layer the user never had, and most projects carry no
    .agents/rules/ at all. Reporting either would put a line on every tool call
    for a state that is nobody's error."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    rules.load(plugin_root, tmp_path / "project")
    assert capsys.readouterr().err == ""


def test_unreadable_layer_directory_degrades_not_crashes(plugin_root, tmp_path):
    cwd = tmp_path / "project"
    (cwd / ".agents").mkdir(parents=True)
    (cwd / ".agents" / "rules").write_text("a file, not a directory")
    loaded = rules.load(plugin_root, cwd)  # must not raise
    assert set(loaded) == {"bounded-execution"}


# ---------------------------------------------------------------------------
# evaluator.py: the configuration gate
# ---------------------------------------------------------------------------


def test_unconfigured_resolves_to_nothing_and_says_nothing(capsys):
    """The common case. cope ships with no endpoint, so a session that never
    configured one has its tool-call evaluation switched off — silently, on
    every tool call, because a line per call would be noise, not information."""
    assert evaluator.resolve() is None
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "missing", ["COPE_EVALUATOR_URL", "COPE_EVALUATOR_PROTOCOL", "COPE_EVALUATOR_MODEL"]
)
def test_partial_configuration_names_what_is_missing_then_stands_down(monkeypatch, capsys, missing):
    """Half-configured is someone's intent that did not land. It gets one line
    naming the gap — and still no evaluation, because guessing the missing
    value is exactly the default this plugin may not have."""
    _configure(monkeypatch, **{missing: None})
    assert evaluator.resolve() is None
    assert missing in capsys.readouterr().err


def test_unknown_protocol_is_refused_rather_than_guessed(monkeypatch, capsys):
    _configure(monkeypatch, COPE_EVALUATOR_PROTOCOL="telepathy")
    assert evaluator.resolve() is None
    err = capsys.readouterr().err
    assert "telepathy" in err
    assert "cope" in err and "openai" in err


@pytest.mark.parametrize("protocol", evaluator.PROTOCOLS)
def test_full_configuration_resolves(monkeypatch, protocol):
    _configure(monkeypatch, COPE_EVALUATOR_PROTOCOL=protocol, COPE_EVALUATOR_API_KEY="secret")
    config = evaluator.resolve()
    assert config is not None
    assert config.protocol == protocol
    assert config.model == "test-model"
    assert config.api_key == "secret"
    assert config.timeout == evaluator.DEFAULT_TIMEOUT_SECONDS


def test_api_key_is_optional_because_a_local_server_needs_none(monkeypatch):
    _configure(monkeypatch)
    config = evaluator.resolve()
    assert config is not None
    assert config.api_key is None


@pytest.mark.parametrize("raw", ["1.5", "0.25"])
def test_timeout_is_configurable(monkeypatch, raw):
    _configure(monkeypatch, COPE_EVALUATOR_TIMEOUT=raw)
    config = evaluator.resolve()
    assert config is not None
    assert config.timeout == float(raw)


@pytest.mark.parametrize("raw", ["soon", "-1", "0"])
def test_unusable_timeout_falls_back_loudly_not_silently(monkeypatch, capsys, raw):
    _configure(monkeypatch, COPE_EVALUATOR_TIMEOUT=raw)
    config = evaluator.resolve()
    assert config is not None
    assert config.timeout == evaluator.DEFAULT_TIMEOUT_SECONDS
    assert raw in capsys.readouterr().err


def test_a_user_config_option_reaches_the_hook(monkeypatch):
    """Claude Code exports each declared `userConfig` option to a hook process
    as `CLAUDE_PLUGIN_OPTION_<KEY>`, the option key uppercased. cope's hook
    command is shell form, which rejects `${user_config.*}` substitution
    outright, so this environment export is the ONLY route a userConfig value
    can take to reach the evaluator."""
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_URL", _DEAD_URL)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_PROTOCOL", "cope")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_MODEL", "configured-model")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_API_KEY", "configured-key")
    config = evaluator.resolve()
    assert config is not None
    assert config.model == "configured-model"
    assert config.api_key == "configured-key"


def test_a_user_config_option_beats_a_plain_environment_variable(monkeypatch):
    """Claude Code refuses to read `pluginConfigs` from a project's own settings
    files precisely so a cloned repository cannot supply one, which makes the
    userConfig value the more trustworthy of the two. It wins."""
    _configure(monkeypatch, COPE_EVALUATOR_MODEL="ambient-model")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_MODEL", "configured-model")
    config = evaluator.resolve()
    assert config is not None
    assert config.model == "configured-model"


def test_a_plain_environment_variable_still_works_alone(monkeypatch):
    """agy and container sessions have no userConfig at all, so the plain
    variable can never become a second-class path."""
    _configure(monkeypatch, COPE_EVALUATOR_MODEL="ambient-model")
    config = evaluator.resolve()
    assert config is not None
    assert config.model == "ambient-model"


def test_a_blank_user_config_option_falls_through_rather_than_blanking_the_value(monkeypatch):
    """Claude Code exports every declared option, including ones the user left
    empty. An empty export must not shadow a plain variable that does have a
    value — that would make declaring an option actively break agy parity."""
    _configure(monkeypatch, COPE_EVALUATOR_MODEL="ambient-model")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_MODEL", "   ")
    config = evaluator.resolve()
    assert config is not None
    assert config.model == "ambient-model"


def test_every_option_the_manifest_declares_is_one_the_code_reads():
    """The coupling that silently breaks: Claude Code derives the environment
    variable from the option KEY, so renaming one side leaves the other reading
    a variable nobody sets — and cope's failure mode for missing configuration
    is a clean no-op, which would look exactly like working correctly.

    The manifest currently declares no options at all, so every value travels
    by plain environment variable. That is a supported configuration, not a
    broken one — ``_setting`` reads the option first and the plain variable
    second, and the second route alone is what agy and container sessions have
    always used. What this pins is the coupling, in whichever direction it
    exists: an option that is declared must name a variable the code reads, and
    it must carry no default and no unmarked credential.
    """
    manifest = json.loads(
        (_REPO_ROOT / "plugins" / "rbg" / "manifest" / "plugin.template.json").read_text()
    )
    declared = manifest["clients"]["claude"].get("userConfig", {})
    assert {key.upper() for key in declared} <= set(_COPE_ENV), (
        "an option whose key does not uppercase to a variable evaluator.py reads "
        "is a setting nobody can supply"
    )
    if "cope_evaluator_api_key" in declared:
        assert declared["cope_evaluator_api_key"]["sensitive"] is True, (
            "the API key must be marked sensitive so it goes to secure storage "
            "rather than settings.json"
        )
    for key, option in declared.items():
        assert "default" not in option, f"{key} declares a default; cope may not have one"
        for field in ("type", "title", "description"):
            assert option.get(field), f"{key} is missing the required {field!r} field"


def test_no_endpoint_or_model_is_compiled_into_the_plugin():
    """The binding constraint, asserted at the source: not a URL, host, or
    vendor model name anywhere in what cope's hooks ship (specs/ARCHITECTURE.md,
    "No defaults"). Configuration arrives from the environment or not at all."""
    offenders = []
    for path in sorted(_COPE_HOOKS.rglob("*")):
        if not path.is_file() or path.suffix not in (".py", ".md"):
            continue
        text = path.read_text(encoding="utf-8")
        for needle in ("http://", "https://", "zentropi", "cope-latest", "gpt-", "localhost"):
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert offenders == []


# ---------------------------------------------------------------------------
# evaluator.py: the two wire protocols, against a recorded transport
# ---------------------------------------------------------------------------


@pytest.fixture()
def transport(monkeypatch):
    """Replace the HTTP call with a recorder. The tests below assert on the
    request cope actually composes — the wire shape is the integration
    contract with Reflexes, so a silent change to it is a real break."""

    class Transport:
        def __init__(self):
            self.requests: list[tuple[str, dict, float]] = []
            self.respond = lambda payload: {"label": 0, "confidence": 0.1}

        def __call__(self, config, payload, timeout):
            self.requests.append((config.url, payload, timeout))
            return self.respond(payload)

    recorder = Transport()
    monkeypatch.setattr(evaluator, "_post", recorder)
    return recorder


@pytest.fixture()
def hooks_dir(tmp_path):
    """A hooks dir carrying the real message files — verdict.md and the
    classifier prompt are loaded from disk, never from a literal."""
    path = tmp_path / "plugin" / "hooks"
    path.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", path / "messages")
    return path


def test_cope_protocol_sends_the_reflexes_label_request(monkeypatch, transport, hooks_dir):
    """CoPE's label API: content_text + criteria_text + model, one policy per
    call (the Reflexes evaluator contract, SPEC.md §4.1)."""
    _configure(monkeypatch)
    evaluator.check(
        evaluator.resolve(), [("halt-on-failure", "Do not bypass a gate.")], "Tool: Bash", hooks_dir
    )
    _, payload, _ = transport.requests[0]
    assert payload == {
        "content_text": "Tool: Bash",
        "criteria_text": "Do not bypass a gate.",
        "model": "test-model",
    }


def test_openai_protocol_sends_a_chat_completion_carrying_the_policy(
    monkeypatch, transport, hooks_dir
):
    """The local-inference path: any OpenAI-compatible server, with the
    classifier instruction taken from messages/classifier-prompt.md rather
    than a string literal in the code."""
    _configure(monkeypatch, COPE_EVALUATOR_PROTOCOL="openai")
    transport.respond = lambda payload: {
        "choices": [{"message": {"content": '{"label": 0, "confidence": 0.2}'}}]
    }
    evaluator.check(
        evaluator.resolve(), [("closure", "Finish what you start.")], "Tool: Bash", hooks_dir
    )
    _, payload, _ = transport.requests[0]
    prompt = (_COPE_HOOKS / "messages" / "classifier-prompt.md").read_text().strip()
    system, user = payload["messages"]
    assert payload["model"] == "test-model"
    assert system["content"] == prompt
    assert "Finish what you start." in user["content"]
    assert "Tool: Bash" in user["content"]


def test_every_live_rule_is_evaluated_not_a_chosen_subset(monkeypatch, transport, hooks_dir):
    """One policy per request, all of them. A rule silently left out of the
    check is a rule silently switched off."""
    _configure(monkeypatch)
    policies = [(f"rule-{i}", f"body {i}") for i in range(12)]
    evaluator.check(evaluator.resolve(), policies, "Tool: Bash", hooks_dir)
    assert {payload["criteria_text"] for _, payload, _ in transport.requests} == {
        body for _, body in policies
    }


def test_only_a_label_of_one_is_a_match(monkeypatch, transport, hooks_dir):
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if payload["criteria_text"] == "flag me" else 0,
        "confidence": 0.9,
        "explanation": "because",
    }
    matches, failures = evaluator.check(
        evaluator.resolve(),
        [("flagged", "flag me"), ("clean", "leave me")],
        "Tool: Bash",
        hooks_dir,
    )
    assert [verdict.slug for verdict in matches] == ["flagged"]
    assert matches[0].confidence == 0.9
    assert matches[0].reason == "because"
    assert failures == []


def test_an_openai_response_wrapped_in_a_code_fence_still_parses(monkeypatch, transport, hooks_dir):
    """Chat models fence their JSON. That is ordinary, not a failure."""
    _configure(monkeypatch, COPE_EVALUATOR_PROTOCOL="openai")
    transport.respond = lambda payload: {
        "choices": [{"message": {"content": '```json\n{"label": 1, "confidence": 0.8}\n```'}}]
    }
    matches, failures = evaluator.check(
        evaluator.resolve(), [("closure", "body")], "Tool: Bash", hooks_dir
    )
    assert [verdict.slug for verdict in matches] == ["closure"]
    assert failures == []


@pytest.mark.parametrize(
    "broken",
    [
        {"confidence": 0.9},  # no label at all
        {"label": "yes"},  # a label that is not an integer
        {"label": 1, "confidence": "very"},  # unparseable confidence
        {"label": 1, "confidence": {}},  # a confidence of the wrong JSON type
        {"label": 1, "confidence": True},  # bool is an int subclass — must not become 1.0
        {},
    ],
)
def test_a_malformed_response_fails_open_and_is_reported(monkeypatch, transport, hooks_dir, broken):
    """The Reflexes contract, §4.3: an evaluator that cannot produce a verdict
    is an evaluator error, distinct from label=0. cope treats both as "no
    advisory", but the error is reported rather than swallowed."""
    _configure(monkeypatch)
    transport.respond = lambda payload: broken
    matches, failures = evaluator.check(
        evaluator.resolve(), [("closure", "body")], "Tool: Bash", hooks_dir
    )
    assert matches == []
    assert len(failures) == 1
    assert "closure" in failures[0]


def test_a_transport_error_fails_open(monkeypatch, hooks_dir):
    _configure(monkeypatch)

    def explode(config, payload, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(evaluator, "_post", explode)
    matches, failures = evaluator.check(
        evaluator.resolve(), [("closure", "body")], "Tool: Bash", hooks_dir
    )
    assert matches == []
    assert "connection refused" in failures[0]


def test_a_slow_evaluator_cannot_hold_the_tool_call_past_the_budget(monkeypatch, hooks_dir):
    """The whole check runs inside one deadline, not one per rule, and a
    transport that ignores the timeout it was handed cannot extend it."""

    def hang(config, payload, timeout):
        time.sleep(10)
        return {"label": 1}

    _configure(monkeypatch, COPE_EVALUATOR_TIMEOUT="0.3")
    monkeypatch.setattr(evaluator, "_post", hang)
    started = time.monotonic()
    matches, failures = evaluator.check(
        evaluator.resolve(), [("a", "body a"), ("b", "body b")], "Tool: Bash", hooks_dir
    )
    elapsed = time.monotonic() - started
    assert matches == []
    assert len(failures) == 2
    assert elapsed < 3, f"check() blocked for {elapsed:.1f}s despite a 0.3s budget"


def test_the_remaining_budget_is_handed_down_as_the_request_timeout(
    monkeypatch, transport, hooks_dir
):
    """Belt to the shutdown's braces: no single request may be allowed to
    outlive the budget, so the socket timeout is the budget, not a constant."""
    _configure(monkeypatch, COPE_EVALUATOR_TIMEOUT="2")
    evaluator.check(evaluator.resolve(), [("closure", "body")], "Tool: Bash", hooks_dir)
    _, _, timeout = transport.requests[0]
    assert 0 < timeout <= 2


def test_the_evaluated_content_is_the_tool_call():
    rendered = evaluator.render_content("Bash", {"command": "git push --force"})
    assert "Bash" in rendered
    assert "git push --force" in rendered


def test_an_enormous_tool_input_is_truncated_before_it_is_sent():
    """A Write carries its whole file body. Sending it would be neither
    affordable nor necessary to judge the call."""
    rendered = evaluator.render_content("Write", {"content": "x" * 100_000})
    assert len(rendered) < evaluator.MAX_CONTENT_CHARS + 200
    assert "truncated" in rendered


# ---------------------------------------------------------------------------
# evaluator.py: on_outcome — the research trace's whole hook into check()
# ---------------------------------------------------------------------------


def test_on_outcome_fires_for_every_policy_matched_and_clean_alike(
    monkeypatch, transport, hooks_dir
):
    """The tuning data check() itself never returns: a rule check() decided was
    clean (label 0) never reaches `matches`, but a trace sink must still see
    it — a false positive and a true negative are equally load-bearing."""
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if payload["criteria_text"] == "flag me" else 0,
        "confidence": 0.7,
    }
    seen: list[evaluator.EvalOutcome] = []
    matches, failures = evaluator.check(
        evaluator.resolve(),
        [("flagged", "flag me"), ("clean", "leave me")],
        "Tool: Bash",
        hooks_dir,
        on_outcome=seen.append,
    )
    assert failures == []
    assert {o.slug for o in seen} == {"flagged", "clean"}
    by_slug = {o.slug: o for o in seen}
    assert by_slug["flagged"].label == 1
    assert by_slug["clean"].label == 0
    assert by_slug["clean"].error is None
    assert [m.slug for m in matches] == ["flagged"], (
        "on_outcome must not change check()'s own return"
    )


def test_on_outcome_fires_with_the_error_for_a_failed_policy(monkeypatch, hooks_dir):
    _configure(monkeypatch)

    def explode(config, payload, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(evaluator, "_post", explode)
    seen: list[evaluator.EvalOutcome] = []
    evaluator.check(
        evaluator.resolve(), [("closure", "body")], "Tool: Bash", hooks_dir, on_outcome=seen.append
    )
    assert len(seen) == 1
    assert seen[0].label is None
    assert seen[0].confidence is None
    assert "connection refused" in seen[0].error


def test_on_outcome_reports_a_positive_latency(monkeypatch, transport, hooks_dir):
    _configure(monkeypatch)
    seen: list[evaluator.EvalOutcome] = []
    evaluator.check(
        evaluator.resolve(),
        [("closure", "body")],
        "Tool: Bash",
        hooks_dir,
        on_outcome=seen.append,
    )
    assert seen[0].latency_s >= 0


def test_on_outcome_fires_for_a_rule_that_never_got_a_slot_within_the_budget(
    monkeypatch, hooks_dir
):
    """A rule cancelled before the budget ran out still needs a trace record —
    otherwise a timed-out rule is simply missing from the tuning data rather
    than present and marked as unanswered."""

    def hang(config, payload, timeout):
        time.sleep(10)
        return {"label": 1}

    _configure(monkeypatch, COPE_EVALUATOR_TIMEOUT="0.2")
    monkeypatch.setattr(evaluator, "_post", hang)
    seen: list[evaluator.EvalOutcome] = []
    evaluator.check(
        evaluator.resolve(),
        [("a", "body a"), ("b", "body b")],
        "Tool: Bash",
        hooks_dir,
        on_outcome=seen.append,
    )
    assert {o.slug for o in seen} == {"a", "b"}
    assert all(o.label is None and o.error for o in seen)


def test_a_broken_on_outcome_sink_does_not_break_the_sweep(monkeypatch, transport, hooks_dir):
    """A trace sink is a side channel with its own module (evaluator_trace.py)
    to fail in; check() itself must never let a broken sink turn a working
    evaluation into a failed one."""
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1, "confidence": 0.9}

    def broken_sink(outcome):
        raise RuntimeError("boom")

    matches, failures = evaluator.check(
        evaluator.resolve(),
        [("closure", "body")],
        "Tool: Bash",
        hooks_dir,
        on_outcome=broken_sink,
    )
    assert [m.slug for m in matches] == ["closure"]
    assert failures == []


# ---------------------------------------------------------------------------
# evaluator_trace.py: the durable input/rule/verdict tuple
# ---------------------------------------------------------------------------


def test_trace_resolve_is_none_when_unset():
    assert evaluator_trace.resolve() is None


def test_trace_resolve_reads_the_plain_variable(monkeypatch, tmp_path):
    path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(path))
    config = evaluator_trace.resolve()
    assert config is not None
    assert config.path == path


def test_trace_resolve_reads_the_plugin_option_over_the_plain_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(tmp_path / "ambient.jsonl"))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_TRACE_PATH", str(tmp_path / "opt.jsonl")
    )
    config = evaluator_trace.resolve()
    assert config is not None
    assert config.path == tmp_path / "opt.jsonl"


def test_sweep_temperature_is_cold_then_warm_for_the_same_session():
    session_id = "sweep-temp-session"
    assert evaluator_trace.sweep_temperature(session_id) == "cold"
    assert evaluator_trace.sweep_temperature(session_id) == "warm"
    assert evaluator_trace.sweep_temperature(session_id) == "warm"


def test_sweep_temperature_is_unknown_for_an_empty_session_id():
    assert evaluator_trace.sweep_temperature("") == "unknown"


def test_sink_for_is_none_when_tracing_is_unconfigured(hooks_dir_with_axioms):
    hooks, cwd = hooks_dir_with_axioms
    ctx = _bash_ctx(hooks, cwd)
    assert evaluator_trace.sink_for(None, ctx, evaluator.resolve() or object(), {}) is None


def test_sink_for_writes_one_record_per_rule_including_clean_ones(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch, COPE_EVALUATOR_API_KEY="super-secret")
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.8,
        "explanation": "why",
    }
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(trace_path))

    ctx = _bash_ctx(hooks, cwd, "git commit --no-verify -m x")
    result = handlers.evaluate(ctx)
    assert result is not None  # sanity: this call really did flag something

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    live = rules.load(hooks.parent, cwd)
    assert len(lines) == len(live), "one trace record per live rule, not only the flagged ones"
    records = [json.loads(line) for line in lines]
    labels = {r["label"] for r in records}
    assert 1 in labels and 0 in labels, "both matches and clean verdicts must be traced"

    matched = next(r for r in records if r["rule_slug"] == "halt-on-failure")
    assert matched["label"] == 1
    assert matched["confidence"] == 0.8
    assert matched["reason"] == "why"
    assert matched["rule_layer"] == 1
    assert matched["rule_text"] == live["halt-on-failure"].body
    assert matched["model"] == "test-model"
    assert matched["protocol"] == "cope"
    assert matched["concurrency"] == evaluator.MAX_CONCURRENCY
    assert matched["session_id"] == "test-session"
    assert matched["tool"] == "Bash"
    assert "git commit --no-verify -m x" in matched["content"]
    assert matched["sweep_temperature"] == "cold"

    dump = json.dumps(records)
    assert "super-secret" not in dump
    assert "api_key" not in dump.lower()

    sweep_ids = {r["sweep_id"] for r in records}
    assert len(sweep_ids) == 1, "every rule in one tool call shares one sweep_id"


def test_sink_for_appends_across_sweeps_never_rewriting(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 0, "confidence": 0.1}
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(trace_path))

    handlers.evaluate(_bash_ctx(hooks, cwd, "git status"))
    first_count = len(trace_path.read_text(encoding="utf-8").splitlines())
    handlers.evaluate(_bash_ctx(hooks, cwd, "git status"))
    second_count = len(trace_path.read_text(encoding="utf-8").splitlines())

    assert second_count == first_count * 2, (
        "the second sweep appended, it did not replace the first"
    )

    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    temperatures = {r["sweep_id"]: r["sweep_temperature"] for r in records}
    assert set(temperatures.values()) == {"cold", "warm"}, "first sweep cold, second sweep warm"


def test_trace_destination_that_cannot_be_written_does_not_break_the_tool_call(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    """A trace failure must never surface as a failed evaluation — the tool
    call this sweep judges must proceed exactly as it would with no tracing
    configured at all."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.8,
    }
    # A file where the trace's parent directory needs to be: mkdir(parents=True)
    # on this path must fail, which is exactly what an unwritable destination
    # looks like from evaluator_trace.py's side.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(blocker / "sub" / "trace.jsonl"))

    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert "halt-on-failure" in result.inject_text


def test_no_evaluator_configured_means_no_trace_is_attempted(
    monkeypatch, hooks_dir_with_axioms, tmp_path
):
    """Tracing rides on evaluate() already having a configured evaluator; an
    unconfigured session must not write a trace file at all, mirroring the
    no-network-call guarantee for the evaluator itself."""
    hooks, cwd = hooks_dir_with_axioms
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(trace_path))
    assert handlers.evaluate(_bash_ctx(hooks, cwd)) is None
    assert not trace_path.exists()


# ---------------------------------------------------------------------------
# evaluator_otel_trace.py: the same records, as OTel spans in OTLP JSON
# ---------------------------------------------------------------------------


def _otlp_spans(path) -> list[dict]:
    """Every span out of every ``resourceSpans``/``scopeSpans`` entry across
    every appended OTLP JSON line, flattened for easy assertion."""
    spans = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        for resource_spans in record.get("resourceSpans", []):
            for scope_spans in resource_spans.get("scopeSpans", []):
                spans.extend(scope_spans.get("spans", []))
    return spans


def _span_attrs(span: dict) -> dict:
    """OTLP JSON's ``AnyValue`` is tagged by type (``stringValue``,
    ``doubleValue``, ``intValue``, ``boolValue``). ``intValue`` is itself a
    JSON *string* in the wire format — the OTLP JSON mapping avoids the
    precision loss a 64-bit int would take as a bare JSON number — so it is
    decoded back to ``int`` here rather than compared as a string."""
    out = {}
    for attr in span.get("attributes", []):
        value = attr["value"]
        if "intValue" in value:
            out[attr["key"]] = int(value["intValue"])
        else:
            out[attr["key"]] = next(iter(value.values()))
    return out


def test_otel_trace_resolve_is_none_when_unset():
    assert evaluator_otel_trace.resolve() is None


def test_otel_trace_resolve_reads_the_plain_variable(monkeypatch, tmp_path):
    path = tmp_path / "trace.otel.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(path))
    config = evaluator_otel_trace.resolve()
    assert config is not None
    assert config.path == path


def test_otel_trace_resolve_reads_the_plugin_option_over_the_plain_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(tmp_path / "ambient.jsonl"))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_OPTION_COPE_EVALUATOR_OTEL_TRACE_PATH", str(tmp_path / "opt.jsonl")
    )
    config = evaluator_otel_trace.resolve()
    assert config is not None
    assert config.path == tmp_path / "opt.jsonl"


def test_otel_sink_for_is_none_when_tracing_is_unconfigured(hooks_dir_with_axioms):
    hooks, cwd = hooks_dir_with_axioms
    ctx = _bash_ctx(hooks, cwd)
    assert evaluator_otel_trace.sink_for(None, ctx, evaluator.resolve() or object(), {}) is None


def test_otel_sink_for_writes_one_span_per_rule_including_clean_ones(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch, COPE_EVALUATOR_API_KEY="super-secret")
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.8,
        "explanation": "why",
    }
    trace_path = tmp_path / "trace.otel.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))

    ctx = _bash_ctx(hooks, cwd, "git commit --no-verify -m x")
    result = handlers.evaluate(ctx)
    assert result is not None  # sanity: this call really did flag something

    spans = _otlp_spans(trace_path)
    live = rules.load(hooks.parent, cwd)
    assert len(spans) == len(live), "one span per live rule, not only the flagged ones"

    by_slug = {_span_attrs(s)["rule_slug"]: (s, _span_attrs(s)) for s in spans}
    span, attrs = by_slug["halt-on-failure"]
    assert attrs["label"] == 1
    assert attrs["confidence"] == 0.8
    assert attrs["reason"] == "why"
    assert attrs["rule_layer"] == 1
    assert attrs["rule_text"] == live["halt-on-failure"].body
    assert attrs["model"] == "test-model"
    assert attrs["protocol"] == "cope"
    assert attrs["concurrency"] == evaluator.MAX_CONCURRENCY
    assert attrs["session_id"] == "test-session"
    assert attrs["tool"] == "Bash"
    assert "git commit --no-verify -m x" in attrs["content"]
    assert attrs["sweep_temperature"] == "cold"
    assert "latency_ms" in attrs
    assert int(span["endTimeUnixNano"]) >= int(span["startTimeUnixNano"])
    assert span["status"]["code"] == 1  # STATUS_CODE_OK

    labels = {a["label"] for _, a in by_slug.values()}
    assert 1 in labels and 0 in labels, "both matches and clean verdicts must be traced"

    dump = json.dumps(spans)
    assert "super-secret" not in dump
    assert "api_key" not in dump.lower()

    sweep_ids = {a["sweep_id"] for _, a in by_slug.values()}
    assert len(sweep_ids) == 1, "every rule in one tool call shares one sweep_id"


def test_otel_sink_for_sets_error_status_for_a_failed_rule(monkeypatch, hooks_dir_with_axioms, tmp_path):
    """``error`` maps onto the span's own status, not only an attribute —
    the OTel-native way a reader would filter for failed evaluations."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    trace_path = tmp_path / "trace.otel.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))
    ctx = _bash_ctx(hooks, cwd)
    loaded = rules.load(hooks.parent, cwd)
    sink = evaluator_otel_trace.sink_for(
        evaluator_otel_trace.resolve(), ctx, evaluator.resolve(), loaded
    )
    outcome = evaluator.EvalOutcome(
        slug=next(iter(loaded)),
        label=None,
        confidence=None,
        reason=None,
        error="transport error",
        latency_s=0.01,
    )
    sink(outcome)
    spans = _otlp_spans(trace_path)
    assert len(spans) == 1
    assert spans[0]["status"]["code"] == 2  # STATUS_CODE_ERROR
    assert _span_attrs(spans[0])["error"] == "transport error"


def test_both_trace_sinks_write_independently_when_both_configured(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    """The JSON Lines trace and the OTel trace are additive, not exclusive —
    configuring both must not disable, replace, or interfere with either."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 0, "confidence": 0.1}
    json_path = tmp_path / "trace.jsonl"
    otel_path = tmp_path / "trace.otel.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_TRACE_PATH", str(json_path))
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(otel_path))

    handlers.evaluate(_bash_ctx(hooks, cwd, "git status"))

    live = rules.load(hooks.parent, cwd)
    json_lines = json_path.read_text(encoding="utf-8").splitlines()
    assert len(json_lines) == len(live)
    assert len(_otlp_spans(otel_path)) == len(live)


def test_otel_trace_destination_that_cannot_be_written_does_not_break_the_tool_call(
    monkeypatch, transport, hooks_dir_with_axioms, tmp_path
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.8,
    }
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(blocker / "sub" / "trace.jsonl"))

    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert "halt-on-failure" in result.inject_text


def test_no_evaluator_configured_means_no_otel_span_is_attempted(
    monkeypatch, hooks_dir_with_axioms, tmp_path
):
    hooks, cwd = hooks_dir_with_axioms
    trace_path = tmp_path / "trace.otel.jsonl"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))
    assert handlers.evaluate(_bash_ctx(hooks, cwd)) is None
    assert not trace_path.exists()


# ---------------------------------------------------------------------------
# handlers.py: what the agent actually sees
# ---------------------------------------------------------------------------


@pytest.fixture()
def hooks_dir_with_axioms(tmp_path):
    """A hooks_dir + sibling axioms/ dir carrying the real floor axioms, plus
    the real message files — mirrors build stage 1's injection layout (axioms/
    and hooks/ are plugin-root siblings). Also returns an empty, isolated
    project cwd so layer 2 never accidentally picks up this repo's own real
    .agents/rules/ during the test run."""
    plugin_root = tmp_path / "plugin"
    hooks = plugin_root / "hooks"
    hooks.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", hooks / "messages")
    shutil.copytree(_LIB_AXIOMS, plugin_root / "axioms")
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    return hooks, project_cwd


def _bash_ctx(hooks, cwd, command="git push --force origin main"):
    return _ctx(hooks, tool="Bash", command=command, cwd=cwd)


def test_evaluate_is_a_no_op_when_no_evaluator_is_configured(hooks_dir_with_axioms, monkeypatch):
    """The unconfigured session, which is most of them: no advisory, and — the
    part that matters in front of every tool call — no network call at all."""
    hooks, cwd = hooks_dir_with_axioms

    def forbidden(*args, **kwargs):
        raise AssertionError("cope reached the network with no evaluator configured")

    monkeypatch.setattr(evaluator, "_post", forbidden)
    assert handlers.evaluate(_bash_ctx(hooks, cwd)) is None


def test_evaluate_injects_the_rule_the_evaluator_flagged(
    hooks_dir_with_axioms, transport, monkeypatch
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.95,
    }
    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert "halt-on-failure" in result.inject_text


def test_the_advisory_hands_back_the_rule_text_not_just_its_name(
    hooks_dir_with_axioms, transport, monkeypatch
):
    """Reflexes' whole correction mechanism is handing the agent the policy it
    matched. A named rule with no text is a scolding the agent cannot act on."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1, "confidence": 1.0}
    result = handlers.evaluate(_bash_ctx(hooks, cwd))
    assert result is not None
    body = (_LIB_AXIOMS / "halt-on-failure.md").read_text().split("\n---\n", 1)[1].strip()
    first_line = next(line for line in body.splitlines() if len(line.strip()) > 40)
    assert first_line in result.inject_text


def test_the_advisory_echoes_the_call_that_was_judged(
    hooks_dir_with_axioms, transport, monkeypatch
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1}
    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git push --force origin main"))
    assert result is not None
    assert "git push --force origin main" in result.inject_text
    assert "{call}" not in result.inject_text
    assert "{rules}" not in result.inject_text


def test_the_evaluators_own_reasoning_is_surfaced_when_it_gives_one(
    hooks_dir_with_axioms, transport, monkeypatch
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.9,
        "explanation": "the --no-verify flag skips the pre-commit gate",
    }
    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert "the --no-verify flag skips the pre-commit gate" in result.inject_text


def test_nothing_flagged_is_a_clean_no_op(hooks_dir_with_axioms, transport, monkeypatch):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 0, "confidence": 0.05}
    assert handlers.evaluate(_bash_ctx(hooks, cwd, "git status")) is None


def test_evaluate_fails_open_when_the_evaluator_errors(hooks_dir_with_axioms, monkeypatch, capsys):
    """A broken endpoint must never manufacture a rule verdict and must never
    raise into dispatch. It costs the agent a stderr line on every occurrence,
    and — the first time in the session — a one-time outage notice on the
    wire (`evaluator.claim_outage_once`); see the block comment above these
    tests for the current contract."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)

    def explode(config, payload, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(evaluator, "_post", explode)
    result = handlers.evaluate(_bash_ctx(hooks, cwd))
    assert result is not None  # first outage this session: the one-time notice
    assert result.kind is Kind.ADVISE
    assert "rule evaluator is not answering" in result.inject_text
    assert "connection refused" in capsys.readouterr().err


def test_evaluate_fails_open_on_a_malformed_response(hooks_dir_with_axioms, transport, monkeypatch):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"nothing": "useful"}
    result = handlers.evaluate(_bash_ctx(hooks, cwd))
    assert result is not None  # first outage this session: the one-time notice
    assert result.kind is Kind.ADVISE
    assert "rule evaluator is not answering" in result.inject_text


def test_evaluate_says_nothing_when_there_is_no_tool_call(
    hooks_dir_with_axioms, transport, monkeypatch
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1}
    assert handlers.evaluate(_ctx(hooks, cwd=cwd)) is None
    assert transport.requests == []


# ---------------------------------------------------------------------------
# The second reader: the person watching the session
# ---------------------------------------------------------------------------
#
# A flagged rule injects a full advisory into the agent's context. The other
# party to the session is the person whose rules these are, and on Claude Code
# they see exactly one thing: `systemMessage`, rendered from `Result.user_text`
# (lib/hooks/clients.py). A verdict that fills in only the agent's half fires
# invisibly — the rule check runs, the agent is corrected or not, and nobody
# gets the chance to intervene. These pin that cope uses the pair.


def _flag_workarounds(transport) -> None:
    transport.respond = lambda payload: {
        "label": 1 if "workaround" in payload["criteria_text"].lower() else 0,
        "confidence": 0.95,
    }


def test_a_flagged_rule_produces_a_line_for_the_person_watching(
    hooks_dir_with_axioms, transport, monkeypatch
):
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    _flag_workarounds(transport)
    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert result.user_text, "a flagged rule reached the agent and nobody else"
    assert "halt-on-failure" in result.user_text
    assert "{rules}" not in result.user_text


def test_the_user_line_is_a_line_not_a_second_copy_of_the_advisory(
    hooks_dir_with_axioms, transport, monkeypatch
):
    """The two readers need opposite things. The agent's copy carries the rule
    text because that is the correction; the user's carries the rule's name
    because that is the decision — whether this is one of theirs worth stopping
    for. Dumping the advisory into the status line serves neither."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    _flag_workarounds(transport)
    result = handlers.evaluate(_bash_ctx(hooks, cwd, "git commit --no-verify -m x"))
    assert result is not None
    assert "\n" not in result.user_text
    assert len(result.user_text) < len(result.inject_text)
    body = (_LIB_AXIOMS / "halt-on-failure.md").read_text().split("\n---\n", 1)[1].strip()
    first_line = next(line for line in body.splitlines() if len(line.strip()) > 40)
    assert first_line not in result.user_text


def test_the_user_line_names_every_rule_that_was_flagged(
    hooks_dir_with_axioms, transport, monkeypatch
):
    """One call can match several rules at once. A line that named only the
    first would be worse than no line: it tells the reader which rule fired,
    and would be wrong about it."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1, "confidence": 1.0}
    result = handlers.evaluate(_bash_ctx(hooks, cwd))
    assert result is not None
    live = rules.load(hooks.parent, cwd)
    assert len(live) > 1, "the fixture must load more than one rule for this to test anything"
    missing = [slug for slug in live if slug not in result.user_text]
    assert missing == []


def test_the_verdict_ships_a_user_facing_sibling():
    """The wording lives in messages/verdict.user.md, beside the agent's copy,
    and carries the rule-name placeholder the handler fills in. A sibling that
    lost the placeholder would ship a line that names nothing."""
    source = (_COPE_HOOKS / "messages" / "verdict.user.md").read_text().strip()
    assert source
    assert "{rules}" in source
    assert "{call}" not in source, "the call that was judged is the agent's copy, not a status line"
    assert len(source.splitlines()) == 1


# ---------------------------------------------------------------------------
# inject_ruleset: the turn-level advisory, and the client scope that keeps it
# off Claude
# ---------------------------------------------------------------------------


def _prompt_ctx(hooks_dir: Path, cwd: Path, *, client: str) -> HookContext:
    return _ctx(
        hooks_dir,
        raw={"prompt": "what did we decide about the build?"},
        cwd=cwd,
        client=client,
        event="UserPromptSubmit",
    )


def test_inject_ruleset_is_declared_agy_only():
    """The scope is declared on the handler, not inferred from a hooks.json —
    dispatch.py reads this attribute, and so does test_shipped_hooks.py."""
    assert handlers.inject_ruleset.only_on_clients == frozenset({"agy"})


def test_inject_ruleset_names_every_live_rule(hooks_dir_with_axioms):
    hooks, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks, cwd, client="agy"))
    assert result is not None
    for slug in ("halt-on-failure", "judgment-non-delegable", "closure"):
        assert f"**{slug}** (1)" in result.inject_text


def test_inject_ruleset_marks_the_layer_a_rule_came_from(hooks_dir_with_axioms, monkeypatch):
    """A project-local rule is the thing agy's own static rules/ directory
    cannot know about, so the layer marker is the load-bearing part."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    hooks, cwd = hooks_dir_with_axioms
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "house-style.md").write_text(
        "---\ntrigger: always_on\ndescription: Sentence case in headings.\n---\n\nBody.\n"
    )
    result = handlers.inject_ruleset(_prompt_ctx(hooks, cwd, client="agy"))
    assert result is not None
    assert "**house-style** (2) — Sentence case in headings." in result.inject_text


def test_inject_ruleset_is_one_line_per_rule_not_the_rule_bodies(hooks_dir_with_axioms):
    """Compressed, and cheap enough to pay every turn: the digest carries each
    rule's own one-line description, never the axiom body shipped alongside it."""
    hooks, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks, cwd, client="agy"))
    assert result is not None
    body = (_LIB_AXIOMS / "halt-on-failure.md").read_text().split("\n---\n", 1)[1]
    body_line = next(
        line for line in body.splitlines() if len(line.strip()) > 40 and not line.startswith("#")
    )
    assert body_line not in result.inject_text


def test_inject_ruleset_silent_when_no_rules_load(tmp_path):
    plugin_root = tmp_path / "plugin"
    hooks = plugin_root / "hooks"
    hooks.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", hooks / "messages")
    (plugin_root / "axioms").mkdir()  # empty — nothing loaded
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    assert handlers.inject_ruleset(_prompt_ctx(hooks, project_cwd, client="agy")) is None


def test_ruleset_message_file_carries_the_placeholder_and_no_leftovers(hooks_dir_with_axioms):
    """The wording lives in messages/ruleset.md; the handler only fills in the
    generated roster. A renamed placeholder would silently ship un-substituted."""
    source = (_COPE_HOOKS / "messages" / "ruleset.md").read_text()
    assert "{rules}" in source
    hooks, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks, cwd, client="agy"))
    assert result is not None
    assert "{rules}" not in result.inject_text


def test_the_verdict_message_file_carries_both_placeholders():
    source = (_COPE_HOOKS / "messages" / "verdict.md").read_text()
    assert "{rules}" in source
    assert "{call}" in source


# ---------------------------------------------------------------------------
# Result shape: the rule check may never refuse a tool call
# ---------------------------------------------------------------------------
#
# The shared runtime carries three dispositions (lib/hooks/dispatch.py `Kind`).
# `REFUSE` denies a tool call outright and is reserved for structural
# impossibility — the session as configured cannot carry the call out. A rule
# verdict from a small model is never that, permanently, so the guarantee is
# asserted about this plugin's source rather than about the type.
#
# `BLOCK` is a different disposition and is deliberately NOT banned here: it
# withholds a *stop*, not a tool call, and `rule_check` legitimately returns one
# (plugins/rbg/hooks/handlers.py). What may never happen is a rule verdict
# denying the call it was asked to judge.


def test_warn_never_produces_a_refusal():
    result = warn("x")
    assert {f.name for f in dataclasses.fields(result)} == {
        "inject_text",
        "user_text",
        "kind",
    }
    # `==`, not `is`: dispatch.py is loaded twice in a live hook, so a member
    # built handler-side is never identical to the renderer's. See `Kind`.
    assert result.kind == Kind.ADVISE


# Every way this plugin's own source could reach the refusal outcome. `refuse`
# is the obvious one; the other two are not, and matter more.
#
# `refuse` (lowercase) does not match `Kind.REFUSE`, so a grep for the helper
# alone sails past `Result("blocked", None, Kind.REFUSE)`, which dispatch.py
# renders as `permissionDecision: deny` exactly like a refuse() call would.
# Constructing a `Result` positionally evades both. Banning construction is what
# actually closes it: handlers.py legitimately imports `Result` for its return
# annotation, and `Result | None` contains no `(`.
_BLOCKING_TOKENS = ("refuse", "Kind.REFUSE", "Result(")


def test_cope_source_can_never_reach_the_blocking_outcome():
    """The rule check may only ever advise or withhold a stop — never deny the
    tool call. Checked at the source, so a future handler cannot acquire a
    refusal path without this failing; a payload that happens not to trigger one
    would not notice.

    An LLM verdict is exactly the kind of thing that grows a "deny on high
    confidence" branch later. This is the test that has to fail when it does.
    """
    offenders = [
        f"{path.name}: {token}"
        for path in sorted(_COPE_HOOKS.glob("*.py"))
        for token in _BLOCKING_TOKENS
        if token in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_the_blocking_token_list_would_actually_catch_a_violation(tmp_path):
    """The guard above is a string search, so it is only worth what its token
    list catches. Prove each token catches the construction it exists for —
    otherwise a passing suite means nothing more than that nobody wrote the one
    spelling that was checked."""
    for source in (
        "return refuse('no')",
        "return Result('no', None, Kind.REFUSE)",
        "return Result('no', kind=Kind.REFUSE)",
    ):
        assert any(token in source for token in _BLOCKING_TOKENS), (
            f"a handler could ship {source!r} without the guard noticing"
        )
    # ...and that the legitimate shapes cope actually uses stay clean.
    for allowed in ("def evaluate(ctx: HookContext) -> Result | None:", "return warn(advisory)"):
        assert not any(token in allowed for token in _BLOCKING_TOKENS), (
            f"the guard would false-positive on {allowed!r}"
        )


def test_every_cope_handler_returns_an_advisory_or_nothing(
    hooks_dir_with_axioms, transport, monkeypatch
):
    """Behavioural counterpart: run every registered cope handler on a payload
    each is known to fire on, and require a non-refusal result."""
    hooks, cwd = hooks_dir_with_axioms
    _configure(monkeypatch)
    transport.respond = lambda payload: {"label": 1, "confidence": 1.0}
    fired = 0
    for event, hooked in handlers.HANDLERS.items():
        for handler in hooked:
            client = "agy" if getattr(handler, "only_on_clients", None) else "claude"
            ctx = _ctx(
                hooks,
                tool="Bash",
                command="git commit --no-verify -m x",
                cwd=cwd,
                client=client,
                event=event,
            )
            result = handler(ctx)
            if result is None:
                continue
            assert result.kind != Kind.REFUSE, f"{handler.__name__} refused on {event}"
            fired += 1
    assert fired > 0, "no cope handler produced a result; the assertion checked nothing"


# ---------------------------------------------------------------------------
# End to end through lib/hooks/dispatch.py, against a real HTTP evaluator
# ---------------------------------------------------------------------------


class _StubEvaluator(BaseHTTPRequestHandler):
    """A loopback CoPE label endpoint. Flags whichever policy carries the
    marker the test planted, so the end-to-end assertions cover a real HTTP
    round trip — headers, JSON, urllib, the lot — not a patched call."""

    marker = "workaround"
    seen: list[dict] = []

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        type(self).seen.append({"payload": payload, "auth": self.headers.get("Authorization")})
        label = 1 if type(self).marker in payload.get("criteria_text", "").lower() else 0
        body = json.dumps({"label": label, "confidence": 0.9}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the default stderr access log
        pass


@pytest.fixture()
def stub_evaluator():
    _StubEvaluator.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubEvaluator)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1/label"
    server.shutdown()
    server.server_close()


@pytest.fixture()
def built_cope_plugin(tmp_path):
    """Assembles the plugin the way build stage 1 would: lib/hooks/*.py and
    plugins/rbg/hooks/*.py copied into one hooks/ dir, plus a sibling
    axioms/ dir carrying lib/axioms/ verbatim — index docs included, because
    that is what ships, and a fixture that filtered them would hide whether
    the loader distinguishes a rule from a reference doc."""
    plugin_root = tmp_path / "plugin"
    hooks = plugin_root / "hooks"
    hooks.mkdir(parents=True)
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks / py_file.name)
    for py_file in _COPE_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks / py_file.name)
    shutil.copytree(_COPE_HOOKS / "messages", hooks / "messages")
    # Any wording the shared runtime ships of its own is merged into the same
    # messages/ directory at build time (build/shared.py, `from = "hooks"`).
    # It currently ships none — the condition tracks that rather than assuming
    # it, so re-introducing shared wording does not silently bypass the build
    # step this fixture is standing in for.
    if (_LIB_HOOKS / "messages").is_dir():
        shutil.copytree(_LIB_HOOKS / "messages", hooks / "messages", dirs_exist_ok=True)
    shutil.copytree(_LIB_AXIOMS, plugin_root / "axioms")
    return hooks


def _dispatch_env(**overrides) -> dict:
    env = dict(os.environ)
    env.pop("ACA_DATA", None)  # keep layer 3 out of content assertions
    for name in _COPE_ENV_ALL:
        env.pop(name, None)
    env.update(overrides)
    return env


def _configured_env(url: str, **overrides) -> dict:
    return _dispatch_env(
        COPE_EVALUATOR_URL=url,
        COPE_EVALUATOR_PROTOCOL="cope",
        COPE_EVALUATOR_MODEL="stub-model",
        **overrides,
    )


def _run_dispatch(hooks: Path, client: str, event: str, raw: dict, *, cwd: Path, env: dict):
    return subprocess.run(
        [sys.executable, str(hooks / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
        timeout=60,
    )


_PRETOOLUSE = {
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "git commit --no-verify -m x"},
}


@pytest.fixture()
def project_cwd(tmp_path):
    path = tmp_path / "project"
    path.mkdir()
    return path


def test_dispatch_end_to_end_injects_the_flagged_rule_advisory_only(
    built_cope_plugin, stub_evaluator, project_cwd
):
    """The whole path, as Claude Code runs it: shipped hook, real HTTP
    evaluator, real rule set. It names the rule, echoes the call, and carries
    no permission decision of any kind."""
    env = _configured_env(stub_evaluator, COPE_EVALUATOR_API_KEY="test-key")
    raw = {**_PRETOOLUSE, "cwd": str(project_cwd)}
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)
    assert result.returncode == 0, f"stderr: {result.stderr!r}"

    out = json.loads(result.stdout)
    advisory = out["hookSpecificOutput"]["additionalContext"]
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert "decision" not in out
    assert "halt-on-failure" in advisory
    assert "--no-verify" in advisory

    assert _StubEvaluator.seen, "the shipped hook never reached the evaluator"
    assert all(row["auth"] == "Bearer test-key" for row in _StubEvaluator.seen)
    assert all("content_text" in row["payload"] for row in _StubEvaluator.seen)


def test_dispatch_end_to_end_shows_the_user_that_a_rule_was_flagged(
    built_cope_plugin, stub_evaluator, project_cwd
):
    """`hookSpecificOutput` reaches the agent; `systemMessage` is the only
    field the person watching ever sees. Both must be on the wire, from the
    real hook process — an advisory composed in-process proves nothing about
    what dispatch renders."""
    raw = {**_PRETOOLUSE, "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin,
        "claude",
        "PreToolUse",
        raw,
        cwd=project_cwd,
        env=_configured_env(stub_evaluator),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"

    out = json.loads(result.stdout)
    assert "systemMessage" in out, "the flagged rule reached the agent and nobody else"
    assert "halt-on-failure" in out["systemMessage"]
    assert "\n" not in out["systemMessage"]
    assert len(out["systemMessage"]) < len(out["hookSpecificOutput"]["additionalContext"])


def test_dispatch_end_to_end_is_silent_when_nothing_is_flagged(
    built_cope_plugin, stub_evaluator, project_cwd
):
    _StubEvaluator.marker = "\x00nothing matches this\x00"
    try:
        raw = {**_PRETOOLUSE, "cwd": str(project_cwd)}
        result = _run_dispatch(
            built_cope_plugin,
            "claude",
            "PreToolUse",
            raw,
            cwd=project_cwd,
            env=_configured_env(stub_evaluator),
        )
        assert result.returncode == 0, f"stderr: {result.stderr!r}"
        assert result.stdout.strip() == ""
    finally:
        _StubEvaluator.marker = "workaround"


def test_dispatch_end_to_end_unconfigured_is_a_silent_no_op(built_cope_plugin, project_cwd):
    """The shipped default: no evaluator configured, so the hook says nothing,
    exits clean, and does not complain on every tool call."""
    raw = {**_PRETOOLUSE, "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=_dispatch_env()
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


# A misconfiguration (evaluator.DEGRADED_CONFIG, via `_note`) is reported on
# stderr only, on every occurrence — see plugins/rbg/hooks/evaluator.py's
# module docstring. An unreachable evaluator (evaluator.DEGRADED_EVALUATOR) is
# different: it can recur on every tool call for a session's whole duration,
# so it additionally gets one hook-response notice per session
# (`evaluator.claim_outage_once`, plugin-local — not the modular
# lib/hooks/degraded.py that commit 89733bf8 removed repo-wide; this is a
# smaller, single-plugin mechanism built for aops_b62f583d). The assertions
# below read both channels accordingly: stderr on every call, the wire only
# on the first call of a session.


def test_dispatch_end_to_end_unreachable_evaluator_fails_open(built_cope_plugin, project_cwd):
    """A configured endpoint that is not listening must not take the session
    down with it: exit 0, no rule verdict — and the failure named on stderr,
    naming the rules that went unchecked. It is the first call of this
    session, so the one-time outage notice is on the wire too; that is not a
    rule verdict either, and it carries no `decision`/`permissionDecision`."""
    env = _configured_env(_DEAD_URL, COPE_EVALUATOR_TIMEOUT="2")
    raw = {**_PRETOOLUSE, "session_id": "unreachable-evaluator", "cwd": str(project_cwd)}
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert "rule evaluator did not answer" in result.stderr
    assert "not being checked" in result.stderr

    out = json.loads(result.stdout)
    assert "rule evaluator is not answering" in out["hookSpecificOutput"]["additionalContext"]
    assert "decision" not in out
    assert "permissionDecision" not in out["hookSpecificOutput"]


def test_dispatch_end_to_end_partial_configuration_says_so_and_stands_down(
    built_cope_plugin, project_cwd
):
    """Half a configuration is a mistake someone made, and the report has to
    name the variable they still have to set — not just that something is
    wrong."""
    env = _dispatch_env(COPE_EVALUATOR_URL=_DEAD_URL)
    raw = {**_PRETOOLUSE, "session_id": "partial-configuration", "cwd": str(project_cwd)}
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)
    assert result.returncode == 0
    assert "COPE_EVALUATOR_MODEL" in result.stderr
    assert "not evaluating" in result.stderr
    assert result.stdout.strip() == ""


def test_dispatch_end_to_end_reports_a_rule_file_that_could_not_be_read(
    built_cope_plugin, stub_evaluator, project_cwd
):
    """A rule that cannot be read is a rule that is not being enforced. The
    report has to name the file — the only person who can fix it needs to know
    which one — and the rest of the rule set has to keep working."""
    rules_dir = project_cwd / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "unreadable.md").mkdir()  # a rule file that is not a file

    raw = {**_PRETOOLUSE, "session_id": "unreadable-rule", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin,
        "claude",
        "PreToolUse",
        raw,
        cwd=project_cwd,
        env=_configured_env(stub_evaluator),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"

    assert "unreadable.md" in result.stderr
    assert "not being checked" in result.stderr
    assert "IsADirectoryError" in result.stderr

    # The flagged rule is still delivered — one unreadable file displaces
    # nothing else, which is the fail-open guarantee this case exists for.
    out = json.loads(result.stdout)
    assert "halt-on-failure" in out["hookSpecificOutput"]["additionalContext"]
    assert "decision" not in out
    assert "permissionDecision" not in out["hookSpecificOutput"]


def test_dispatch_end_to_end_reports_a_rule_file_that_is_never_evaluated(
    built_cope_plugin, stub_evaluator, project_cwd
):
    """A project rule with no `trigger: always_on` marker is read by agents and
    never sent to the evaluator. Its author has no way to tell from inside the
    session, which is how a rule quietly stops being enforced — so the report
    names both the file and the frontmatter line that would fix it."""
    rules_dir = project_cwd / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "costly-ops-approval.md").write_text("---\ndescription: no marker\n---\n\nAsk.\n")

    raw = {**_PRETOOLUSE, "session_id": "unmarked-rule", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin,
        "claude",
        "PreToolUse",
        raw,
        cwd=project_cwd,
        env=_configured_env(stub_evaluator),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"

    assert "costly-ops-approval.md" in result.stderr
    assert "trigger: always_on" in result.stderr


def test_dispatch_end_to_end_reports_the_same_fault_on_every_tool_call(
    built_cope_plugin, project_cwd
):
    """One hook invocation is one process, so stderr carries the same fault
    on every occurrence — never rate-limited or dropped, because the log is
    not the channel a person is watching. The hook-response channel is
    different on purpose: it is rate-limited to once per session
    (`evaluator.claim_outage_once`), so the first call gets the notice and the
    second — same session, same recurring fault — gets none. Pinned both
    calls so a reader can see which contract each channel follows."""
    env = _configured_env(_DEAD_URL, COPE_EVALUATOR_TIMEOUT="2")
    raw = {**_PRETOOLUSE, "session_id": "repeated-fault", "cwd": str(project_cwd)}
    first = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)
    second = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)

    assert "rule evaluator did not answer" in first.stderr
    assert "rule evaluator did not answer" in second.stderr
    # First call this session: the one-time notice is on the wire.
    assert "rule evaluator is not answering" in first.stdout
    # Second call, same session: already announced, so nothing on the wire.
    assert second.stdout.strip() == ""


def test_dispatch_end_to_end_an_unconfigured_session_is_never_called_degraded(
    built_cope_plugin, project_cwd
):
    """The line evaluator.resolve() draws, held on the wire: nothing
    configured is a legitimate state, not a fault, and gets no line anywhere."""
    raw = {**_PRETOOLUSE, "session_id": "unconfigured", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=_dispatch_env()
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_dispatch_agy_preinvocation_injects_the_live_ruleset(built_cope_plugin, project_cwd):
    """agy's only usable phase carries a prompt, not a tool call. cope fires
    there and states the rule set — the whole reason the hook is wired."""
    raw = {"prompt": "ship the release", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "agy", "PreInvocation", raw, cwd=project_cwd, env=_dispatch_env()
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    injected = json.loads(result.stdout)["injectSteps"][0]["ephemeralMessage"]
    assert "**halt-on-failure** (1)" in injected
    assert "**judgment-non-delegable** (1)" in injected
    # the axioms/ index docs ship alongside the rules and are not rules
    assert "**README**" not in injected
    assert "**AXIOMS-REVIEW**" not in injected


def test_dispatch_agy_preinvocation_is_advisory_only(built_cope_plugin, project_cwd):
    """agy's wire shape has one non-empty form — an ephemeral message. There is
    no decision, no permission field, nothing that could stop the turn."""
    raw = {"prompt": "ship the release", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "agy", "PreInvocation", raw, cwd=project_cwd, env=_dispatch_env()
    )
    out = json.loads(result.stdout)
    assert set(out) == {"injectSteps"}
    assert set(out["injectSteps"][0]) == {"ephemeralMessage"}


def test_dispatch_claude_userpromptsubmit_stays_silent(built_cope_plugin, project_cwd):
    """Claude fires both UserPromptSubmit and PreToolUse, and cope covers it at
    PreToolUse; the pkb plugin owns Claude's UserPromptSubmit. Even reached
    directly, cope's turn-level advisory must produce nothing here."""
    raw = {"hook_event_name": "UserPromptSubmit", "prompt": "hello", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "claude", "UserPromptSubmit", raw, cwd=project_cwd, env=_dispatch_env()
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert result.stdout.strip() == ""


def test_dispatch_agy_never_evaluates_a_tool_call(built_cope_plugin, stub_evaluator, project_cwd):
    """A tool payload delivered on agy's phase still yields the ruleset
    advisory, not a verdict — there is no PreToolUse on agy, so cope must not
    pretend it evaluated a tool call it never saw."""
    raw = {
        "prompt": "commit it",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify -m x"},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(
        built_cope_plugin,
        "agy",
        "PreInvocation",
        raw,
        cwd=project_cwd,
        env=_configured_env(stub_evaluator),
    )
    injected = json.loads(result.stdout)["injectSteps"][0]["ephemeralMessage"]
    assert "The call that was evaluated" not in injected
    assert _StubEvaluator.seen == []


def test_dispatch_falls_back_to_process_cwd_when_payload_omits_it(
    built_cope_plugin, stub_evaluator, project_cwd
):
    result = _run_dispatch(
        built_cope_plugin,
        "claude",
        "PreToolUse",
        _PRETOOLUSE,  # no "cwd" key in the payload
        cwd=project_cwd,
        env=_configured_env(stub_evaluator),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    out = json.loads(result.stdout)
    assert "halt-on-failure" in out["hookSpecificOutput"]["additionalContext"]
