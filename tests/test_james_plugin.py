"""Behavioral tests for the standalone `james` plugin."""

from __future__ import annotations

import http.server
import json
import os
import stat
import subprocess
import sys
import threading
import tomllib
from pathlib import Path
from typing import Any

import pytest

from build.build import build_all

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / "build" / "marketplace.toml"
VERSION = "0.0.0.dev0"

VALID_REPORT_MD = """# Worker Report

Verified target behavior directly.

```argdown
===
title: Verified behavior
asks:
  task-1/AC1: Confirm test output passes
answers:
  task-1/AC1: 3
===

(1) Executed test check and observed exit code 0 in stdout (run: exit_code = 0).
(2) Rule says exit code 0 proves check passage (spec/check.md:10).
-- Exit Code Warrant: Exit code 0 establishes test check passage. Unless: check skipped tests; ruled out by explicit pass count in stdout. --
(3) So, task-1/AC1 is verified complete.
```
"""

INVALID_ARGDOWN_MD = """# Broken Report

```argdown
===
asks:
  task-1/AC1: Confirm test output passes
answers:
  task-1/AC1: 99
===

(1) Missing conclusion 99 and inference bar.
```
"""

MISSING_ASKS_ARGDOWN_MD = """```argdown
===
title: No asks frontmatter
===

(1) Statement without asks map.
```
"""

VALID_PASS_REASON = """Judged: task-1; asks task-1/AC1
Valid: (3) holds -- exit code warrant yields (3) from (1) and (2)
Supported: weakest I read it -- (1) cites direct run exit code 0
Answered: task-1/AC1 ← (3)
Sufficient: (3) material; direct execution evidence answers ask
Waived: none
Relay: Verified task-1/AC1 passes per direct run ← (3)
"""


@pytest.fixture(scope="session")
def james_dist_root(build_once) -> Path:
    """Build plugins once per session using the real build pipeline."""
    return build_once(
        "shipped-dist",
        lambda root: build_all(REPO_ROOT, root, marketplace_path=MARKETPLACE, version=VERSION),
    )


def _base_hook_env(
    tmp_path: Path, overrides: dict[str, str | None] | None = None
) -> dict[str, str]:
    env = dict(os.environ)
    for k in (
        "CLAUDE_CODE_IS_COWORK",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_REMOTE",
        "AOPS_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "SESSION_ID",
        "ANTIGRAVITY_SESSION_ID",
        "GEMINI_SESSION_ID",
        "CLAUDE_ENV_FILE",
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TRACE_PROTOCOL",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "AOPS_TELEMETRY_FAILURE_MODE",
        "AOPS_IMAGE_STALE",
        "AOPS_IMAGE_STALENESS_WARNING",
    ):
        env.pop(k, None)
    env["HOME"] = str(tmp_path)
    env["PKB_MCP_URL"] = "http://127.0.0.1:19999/mcp"
    env["AOPS_TRACER_STATE_DIR"] = str(tmp_path / "tracer_state")
    env["AOPS_SESSION_POINTER_DIR"] = str(tmp_path / "session_pointer")
    env["AOPS_PREMISE_GATE_DIR"] = str(tmp_path / "gate_state")
    if overrides:
        for k, v in overrides.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
    return env


def _run_dist_python(
    build_dir: Path,
    script_rel: str,
    args: list[str],
    *,
    stdin_payload: dict[str, Any] | None = None,
    env: dict[str, str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(build_dir / script_rel), *args],
        input=json.dumps(stdin_payload) if stdin_payload is not None else "",
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or build_dir,
        timeout=60,
    )


def _start_recording_http_server() -> tuple[
    http.server.HTTPServer, list[dict[str, Any]], threading.Thread
]:
    recorded: list[dict[str, Any]] = []

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""
            recorded.append({"method": "POST", "path": self.path, "body": body})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"")

        def do_GET(self) -> None:
            recorded.append({"method": "GET", "path": self.path, "body": b""})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"")

        def log_message(self, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, recorded, thread


def _parse_env_exports(env_file: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("export "):
            continue
        k, _, v = line[len("export ") :].partition("=")
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1]
        parsed[k] = v
    return parsed


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_session_start_injects_core_isolates_credentials_and_writes_session_id(
    james_dist_root: Path, tmp_path: Path, client: str
) -> None:
    build_dir = james_dist_root / f"james-{client}"
    env_file = tmp_path / "claude-env.sh"
    session_id = f"sess-start-{client}-001"
    id_key = "session_id" if client == "claude" else "conversationId"
    payload = {id_key: session_id, "cwd": str(tmp_path)}
    if client == "claude":
        payload["hook_event_name"] = "SessionStart"

    env = _base_hook_env(
        tmp_path,
        {
            "CLAUDE_ENV_FILE": str(env_file),
            "AOPS_BOT_GH_TOKEN": "ghp_secret_value",
            "PKB_MCP_URL": "https://pkb.example.test/mcp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318",
        },
    )

    res = _run_dist_python(
        build_dir,
        "hooks/dispatch.py",
        [client, "SessionStart"],
        stdin_payload=payload,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)

    if client == "claude":
        injected = out["hookSpecificOutput"]["additionalContext"]
    else:
        injected = "\n".join(
            step.get("ephemeralMessage", "")
            for step in out.get("injectSteps", [])
            if isinstance(step, dict)
        )
    assert "james Plugin Core" in injected
    assert "james:premise-check" in injected

    assert env_file.is_file()
    if os.name == "posix":
        assert (env_file.stat().st_mode & 0o777) == stat.S_IMODE(0o600)
    exported = _parse_env_exports(env_file)
    assert exported["AOPS_SESSION_ID"] == session_id
    assert exported["PKB_MCP_URL"] == "https://pkb.example.test/mcp"
    assert exported["AOPS_BOT_GH_TOKEN"] == "ghp_secret_value"


@pytest.mark.parametrize(
    ("client", "wire_event"), [("claude", "UserPromptSubmit"), ("agy", "PreInvocation")]
)
def test_prompt_hooks_make_zero_pkb_http_calls(
    james_dist_root: Path, tmp_path: Path, client: str, wire_event: str
) -> None:
    build_dir = james_dist_root / f"james-{client}"
    server, requests_seen, thread = _start_recording_http_server()
    try:
        env = _base_hook_env(
            tmp_path,
            {"PKB_MCP_URL": f"http://127.0.0.1:{server.server_port}/mcp"},
        )
        id_key = "session_id" if client == "claude" else "conversationId"
        res = _run_dist_python(
            build_dir,
            "hooks/dispatch.py",
            [client, wire_event],
            stdin_payload={
                id_key: f"sess-no-hydrate-{client}",
                "prompt": "Search the PKB for all recent project decisions and task notes",
            },
            env=env,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert res.returncode == 0, res.stderr
    assert requests_seen == [], f"Unexpected PKB HTTP calls during prompt hook: {requests_seen}"


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_handback_and_peer_reports_never_arm_hearsay_gate(
    james_dist_root: Path, tmp_path: Path, client: str
) -> None:
    build_dir = james_dist_root / f"james-{client}"
    gate_dir = tmp_path / "gate_state"
    env = _base_hook_env(tmp_path, {"AOPS_PREMISE_GATE_DIR": str(gate_dir)})
    session_id = f"sess-no-hearsay-{client}"
    handback_msg = (
        '<subagent-handback from="rbg">All rules checked; no issues found.</subagent-handback>'
    )

    if client == "claude":
        sequence = [
            ("UserPromptSubmit", {"session_id": session_id, "prompt": handback_msg}),
            (
                "SubagentStop",
                {
                    "session_id": session_id,
                    "agent_type": "rbg",
                    "last_assistant_message": handback_msg,
                },
            ),
            (
                "PreToolUse",
                {"session_id": session_id, "tool_name": "Agent", "tool_input": {"prompt": "next"}},
            ),
            (
                "PreToolUse",
                {
                    "session_id": session_id,
                    "tool_name": "SendMessage",
                    "tool_input": {"message": "ok"},
                },
            ),
            (
                "PostToolBatch",
                {
                    "session_id": session_id,
                    "tool_calls": [{"tool_name": "Agent", "tool_use_id": "t1"}],
                },
            ),
            ("Stop", {"session_id": session_id}),
        ]
    else:
        sequence = [
            ("PreInvocation", {"conversationId": session_id, "prompt": handback_msg}),
            (
                "PreToolUse",
                {
                    "conversationId": session_id,
                    "toolCall": {"name": "invoke_subagent", "args": {"Prompt": "next"}},
                },
            ),
            (
                "PostToolUse",
                {"conversationId": session_id, "toolCall": {"name": "invoke_subagent", "args": {}}},
            ),
            ("Stop", {"conversationId": session_id}),
        ]

    for wire_event, payload in sequence:
        res = _run_dist_python(
            build_dir,
            "hooks/dispatch.py",
            [client, wire_event],
            stdin_payload=payload,
            env=env,
        )
        assert res.returncode == 0, f"{client} {wire_event}: {res.stderr}"
        if res.stdout.strip():
            out = json.loads(res.stdout)
            assert out.get("decision") not in ("block", "deny"), out
            assert (out.get("hookSpecificOutput") or {}).get("permissionDecision") != "deny", out

    assert not list(gate_dir.glob("*")), "Expected zero gate state files without hearsay hooks"


SESSION_SERVERS: tuple[str, ...] = tuple(
    tomllib.loads((REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))["hooks"][
        "mcp_caller_session"
    ]["session_servers"]
)


@pytest.mark.parametrize("server_name", SESSION_SERVERS)
def test_mcp_caller_session_injects_session_on_configured_servers(
    james_dist_root: Path, tmp_path: Path, server_name: str
) -> None:
    build_dir = james_dist_root / "james-claude"
    env = _base_hook_env(tmp_path)
    res = _run_dist_python(
        build_dir,
        "hooks/mcp_caller_session.py",
        [],
        stdin_payload={
            "session_id": "sess-mcp-123",
            "prompt_id": "prompt-456",
            "tool_name": f"mcp__{server_name}__sample_action",
            "tool_input": {"title": "Test"},
        },
        env=env,
    )
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    updated = out["hookSpecificOutput"]["updatedInput"]
    assert updated["title"] == "Test"
    assert updated["_session"]["session_id"] == "sess-mcp-123"
    assert updated["_session"]["prompt_id"] == "prompt-456"


def test_mcp_caller_session_skips_unconfigured_servers(
    james_dist_root: Path, tmp_path: Path
) -> None:
    assert "playwright" not in SESSION_SERVERS
    build_dir = james_dist_root / "james-claude"
    env = _base_hook_env(tmp_path)
    res = _run_dist_python(
        build_dir,
        "hooks/mcp_caller_session.py",
        [],
        stdin_payload={
            "session_id": "sess-mcp-123",
            "prompt_id": "prompt-456",
            "tool_name": "mcp__playwright__browser_snapshot",
            "tool_input": {},
        },
        env=env,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == ""


def test_verdict_script_validates_judged_file_and_exports_otel_span(
    james_dist_root: Path, tmp_path: Path
) -> None:
    build_dir = james_dist_root / "james-claude"
    valid_report = tmp_path / "valid_report.md"
    valid_report.write_text(VALID_REPORT_MD, encoding="utf-8")
    broken_report = tmp_path / "broken_report.md"
    broken_report.write_text(INVALID_ARGDOWN_MD, encoding="utf-8")
    pass_reason = tmp_path / "pass_reason.txt"
    pass_reason.write_text(VALID_PASS_REASON, encoding="utf-8")
    revise_reason = tmp_path / "revise_reason.txt"
    revise_reason.write_text(
        "Judged: task-1; asks task-1/AC1\n"
        "Valid: (2) fails #missing -- missing warrant bar\n"
        "Answered: task-1/AC1 unanswered\n",
        encoding="utf-8",
    )

    server, recorded, thread = _start_recording_http_server()
    try:
        env = _base_hook_env(
            tmp_path,
            {
                "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
                "AOPS_SESSION_ID": "sess-verdict-test",
            },
        )
        verdict_script = "skills/premise-check/scripts/verdict.py"

        # 1. Missing --judged-file on PASS fails loudly before exporting any span.
        missing_judged = _run_dist_python(
            build_dir,
            verdict_script,
            ["--claim", "task-1", "--verdict", "PASS", "--reason-file", str(pass_reason)],
            env=env,
        )
        assert missing_judged.returncode != 0
        assert "--judged-file" in missing_judged.stderr
        assert len(recorded) == 0

        # 2. Invalid Argdown syntax in --judged-file fails PASS loudly.
        bad_argdown = _run_dist_python(
            build_dir,
            verdict_script,
            [
                "--claim",
                "task-1",
                "--verdict",
                "PASS",
                "--judged-file",
                str(broken_report),
                "--reason-file",
                str(pass_reason),
            ],
            env=env,
        )
        assert bad_argdown.returncode != 0
        assert len(recorded) == 0

        # 3. Valid Argdown + matching 7-line reason passes and emits OTel span.
        good_pass = _run_dist_python(
            build_dir,
            verdict_script,
            [
                "--claim",
                "task-1",
                "--verdict",
                "PASS",
                "--judged-file",
                str(valid_report),
                "--reason-file",
                str(pass_reason),
            ],
            env=env,
        )
        assert good_pass.returncode == 0, good_pass.stderr
        pass_out = json.loads(good_pass.stdout)
        assert pass_out["ok"] is True
        assert pass_out["verdict"] == "PASS"
        assert pass_out["span_emitted"] is True
        assert pass_out["verification_id"].startswith("verdict-")
        assert len(recorded) == 1
        assert b"premise_check_verdict" in recorded[0]["body"]

        # 4. REVISE without --judged-file succeeds and emits OTel span.
        good_revise = _run_dist_python(
            build_dir,
            verdict_script,
            ["--claim", "task-1", "--verdict", "REVISE", "--reason-file", str(revise_reason)],
            env=env,
        )
        assert good_revise.returncode == 0, good_revise.stderr
        revise_out = json.loads(good_revise.stdout)
        assert revise_out["ok"] is True
        assert revise_out["verdict"] == "REVISE"
        assert len(recorded) == 2
        assert b"premise_check_verdict" in recorded[1]["body"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_file_claims_script_exports_claim_span_and_rejects_invalid_block(
    james_dist_root: Path, tmp_path: Path
) -> None:
    build_dir = james_dist_root / "james-claude"
    valid_report = tmp_path / "valid_report.md"
    valid_report.write_text(VALID_REPORT_MD, encoding="utf-8")
    no_asks_report = tmp_path / "no_asks.md"
    no_asks_report.write_text(MISSING_ASKS_ARGDOWN_MD, encoding="utf-8")

    server, recorded, thread = _start_recording_http_server()
    try:
        env = _base_hook_env(
            tmp_path,
            {
                "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
                "AOPS_SESSION_ID": "sess-claim-test",
            },
        )
        claims_script = "skills/dump/scripts/file_claims.py"

        invalid = _run_dist_python(
            build_dir,
            claims_script,
            ["--claim", "task-1", "--argdown-file", str(no_asks_report)],
            env=env,
        )
        assert invalid.returncode != 0
        assert len(recorded) == 0

        valid = _run_dist_python(
            build_dir,
            claims_script,
            ["--claim", "task-1", "--argdown-file", str(valid_report), "--title", "Verified check"],
            env=env,
        )
        assert valid.returncode == 0, valid.stderr
        out = json.loads(valid.stdout)
        assert out["ok"] is True
        assert out["status"] == "to_be_verified"
        assert out["ask_ids"] == ["task-1/AC1"]
        assert out["span_emitted"] is True
        assert len(recorded) == 1
        assert b"premise_check_claim" in recorded[0]["body"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.integration
def test_shipped_hook_commands_via_uv_run(james_dist_root: Path, tmp_path: Path) -> None:
    """Exercise the built hooks.json uv run commands for both claude and agy."""
    for client in ("claude", "agy"):
        build_dir = james_dist_root / f"james-{client}"
        hooks_path = build_dir / ("hooks/hooks.json" if client == "claude" else "hooks.json")
        cfg = json.loads(hooks_path.read_text(encoding="utf-8"))
        if client == "claude":
            cmd = cfg["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(build_dir))
            id_key = "session_id"
        else:
            spec = next(iter(cfg.values()))
            cmd = spec["SessionStart"][0]["command"]
            id_key = "conversationId"

        env = _base_hook_env(tmp_path)
        env.pop("VIRTUAL_ENV", None)
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=tmp_path if client == "claude" else build_dir,
            input=json.dumps({id_key: f"uv-run-{client}", "cwd": str(tmp_path)}),
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        assert res.returncode == 0, f"{client} uv run failed: {res.stderr}"
        assert "james:premise-check" in res.stdout
