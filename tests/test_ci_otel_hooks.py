"""scripts/ci_otel_hooks.py: Claude Code settings that trace a GitHub Actions agent run to Phoenix."""

from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ci_otel_hooks.py"
TRACER = REPO_ROOT / "plugins" / "ida" / "hooks" / "claude_code_tracer.py"

_CONFIGURED = {
    "GENAI_ENGINE_TRACE_ENDPOINT": "https://otel.example.test/v1/traces",
    "GENAI_ENGINE_API_KEY": "CF-Access-Client-Id=abc,CF-Access-Client-Secret=s3cr3t'x",
    "GENAI_ENGINE_TRACE_PROTOCOL": "http/protobuf",
    "GITHUB_ACTIONS": "true",
    "GITHUB_REPOSITORY": "nicsuzor/academicOps",
    "GITHUB_RUN_ID": "42",
}

_EVENTS = {
    "UserPromptSubmit": "user_prompt_submit",
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_tool",
    "PostToolUseFailure": "post_tool_failure",
    "Stop": "stop",
}


def _run(tmp_path: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess:
    gh_output = tmp_path / "gh_output"
    base_env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(gh_output)}
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--aops-root",
            str(REPO_ROOT),
            "--out-dir",
            str(tmp_path / "otel"),
            "--python",
            sys.executable,
            *extra,
        ],
        env={**base_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def _settings(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "otel" / "settings.json").read_text())


def _gh_output(tmp_path: Path) -> str:
    return (tmp_path / "gh_output").read_text()


def test_unconfigured_writes_empty_settings_and_succeeds(tmp_path):
    proc = _run(tmp_path, {})

    assert proc.returncode == 0, proc.stderr
    assert _settings(tmp_path) == {}
    assert f"settings={tmp_path / 'otel' / 'settings.json'}" in _gh_output(tmp_path)
    assert "::notice::" in proc.stdout
    assert not (tmp_path / "otel" / "hook.sh").exists()


def test_unconfigured_keeps_base_settings(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"env": {"CLAUDE_CODE_ENABLE_TELEMETRY": "1"}}))

    proc = _run(tmp_path, {}, "--base-settings", str(base))

    assert proc.returncode == 0, proc.stderr
    assert _settings(tmp_path) == {"env": {"CLAUDE_CODE_ENABLE_TELEMETRY": "1"}}


def test_configured_registers_tracer_for_every_traced_event(tmp_path):
    proc = _run(tmp_path, _CONFIGURED)

    assert proc.returncode == 0, proc.stderr
    hooks = _settings(tmp_path)["hooks"]
    hook_sh = tmp_path / "otel" / "hook.sh"
    assert set(hooks) == set(_EVENTS)
    for event, tracer_event in _EVENTS.items():
        (entry,) = hooks[event]
        (command,) = entry["hooks"]
        assert command["type"] == "command"
        assert command["command"] == f"{shlex.quote(str(hook_sh))} {tracer_event}"
    assert hooks["PreToolUse"][0]["matcher"] == "*"


def test_configured_settings_never_contain_the_api_key(tmp_path):
    _run(tmp_path, _CONFIGURED)

    text = (tmp_path / "otel" / "settings.json").read_text()
    assert "s3cr3t" not in text
    assert "GENAI_ENGINE_API_KEY" not in text


def test_hook_wrapper_is_private_and_runs_a_copy_of_the_tracer(tmp_path):
    _run(tmp_path, _CONFIGURED)

    out = tmp_path / "otel"
    hook_sh = out / "hook.sh"
    mode = stat.S_IMODE(hook_sh.stat().st_mode)
    assert mode == 0o700
    copied = out / "claude_code_tracer.py"
    assert copied.read_bytes() == TRACER.read_bytes()
    assert str(copied) in hook_sh.read_text()


def test_hook_wrapper_exports_config_and_run_identity(tmp_path):
    _run(tmp_path, _CONFIGURED, "--project", "gh-test")
    hook_sh = tmp_path / "otel" / "hook.sh"

    probe = tmp_path / "probe.py"
    probe.write_text(
        "import json, os, sys\n"
        "keys = ['GENAI_ENGINE_TRACE_ENDPOINT', 'GENAI_ENGINE_API_KEY', 'GENAI_ENGINE_TRACE_PROTOCOL',"
        " 'PHOENIX_PROJECT_NAME', 'GITHUB_ACTIONS', 'GITHUB_REPOSITORY', 'GITHUB_RUN_ID']\n"
        "print(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read(),"
        " 'env': {k: os.environ.get(k) for k in keys}}))\n"
    )
    (tmp_path / "otel" / "claude_code_tracer.py").write_text(probe.read_text())

    proc = subprocess.run(
        [str(hook_sh), "stop"],
        input='{"session_id": "x"}',
        env={"PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    seen = json.loads(proc.stdout)
    assert seen["argv"] == ["stop"]
    assert seen["stdin"] == '{"session_id": "x"}'
    assert seen["env"] == {
        "GENAI_ENGINE_TRACE_ENDPOINT": _CONFIGURED["GENAI_ENGINE_TRACE_ENDPOINT"],
        "GENAI_ENGINE_API_KEY": _CONFIGURED["GENAI_ENGINE_API_KEY"],
        "GENAI_ENGINE_TRACE_PROTOCOL": "http/protobuf",
        "PHOENIX_PROJECT_NAME": "gh-test",
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "nicsuzor/academicOps",
        "GITHUB_RUN_ID": "42",
    }


def test_project_defaults_to_github_actions(tmp_path):
    _run(tmp_path, _CONFIGURED)

    assert "PHOENIX_PROJECT_NAME=github-actions" in (tmp_path / "otel" / "hook.sh").read_text()


def test_hook_wrapper_never_fails_the_agent(tmp_path):
    _run(tmp_path, _CONFIGURED)
    (tmp_path / "otel" / "claude_code_tracer.py").write_text("import sys\nsys.exit(3)\n")

    proc = subprocess.run(
        [str(tmp_path / "otel" / "hook.sh"), "pre_tool"],
        input="{}",
        env={"PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0


def test_configured_merges_hooks_into_base_settings(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"env": {"OTEL_LOGS_EXPORTER": "otlp"}, "model": "sonnet"}))

    _run(tmp_path, _CONFIGURED, "--base-settings", str(base))

    settings = _settings(tmp_path)
    assert settings["env"] == {"OTEL_LOGS_EXPORTER": "otlp"}
    assert settings["model"] == "sonnet"
    assert set(settings["hooks"]) == set(_EVENTS)


def test_missing_tracer_degrades_to_no_hooks(tmp_path):
    fake_root = tmp_path / "aops"
    fake_root.mkdir()
    gh_output = tmp_path / "gh_output"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--aops-root",
            str(fake_root),
            "--out-dir",
            str(tmp_path / "otel"),
            "--python",
            sys.executable,
        ],
        env={"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(gh_output), **_CONFIGURED},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "::warning::" in proc.stdout
    assert _settings(tmp_path) == {}


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_endpoint_counts_as_unconfigured(tmp_path, value):
    proc = _run(tmp_path, {**_CONFIGURED, "GENAI_ENGINE_TRACE_ENDPOINT": value})

    assert proc.returncode == 0, proc.stderr
    assert _settings(tmp_path) == {}


def test_missing_api_key_counts_as_unconfigured(tmp_path):
    # Fork PRs and callers that don't pass the secret: no hooks, rather than
    # every tool call waiting on a collector that will refuse the export.
    env = {k: v for k, v in _CONFIGURED.items() if k != "GENAI_ENGINE_API_KEY"}

    proc = _run(tmp_path, env)

    assert proc.returncode == 0, proc.stderr
    assert _settings(tmp_path) == {}
    assert "GENAI_ENGINE_API_KEY" in proc.stdout
