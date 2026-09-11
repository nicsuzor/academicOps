"""Tests for Ida permission constraints, scratchpad write gate, and citation enforcement."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
PKB_HOOKS = REPO_ROOT / "plugins" / "pkb" / "hooks"

for p in (LIB_HOOKS, IDA_HOOKS, PKB_HOOKS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from citation_enforcement import citation_enforcement_gate
from dispatch import HookContext, Kind
from scratchpad_gate import is_allowed_scratchpad_path, scratchpad_write_gate

# --- Scratchpad Write Gate Tests ---


def test_is_allowed_scratchpad_path():
    # Canonical pattern: /opt/nic/tmp/claude-1000/<project>/<session>/scratchpad/...
    assert is_allowed_scratchpad_path(
        "/opt/nic/tmp/claude-1000/aops/session-123/scratchpad/notes.md"
    )
    assert is_allowed_scratchpad_path(
        "/opt/nic/tmp/claude-1000/myproj/sess456/scratchpad/sub/scratch.txt"
    )
    # Container /scratch
    assert is_allowed_scratchpad_path("/scratch/notes.txt")
    # Path with scratchpad component
    assert is_allowed_scratchpad_path("/tmp/session/scratchpad/foo.txt")

    # Disallowed paths:
    assert not is_allowed_scratchpad_path("/workspace/plugins/ida/agents/ida.md")
    assert not is_allowed_scratchpad_path("/tmp/malicious.txt")
    assert not is_allowed_scratchpad_path(
        "/opt/nic/tmp/claude-1000/aops/session-123/not_scratchpad/file.txt"
    )
    assert not is_allowed_scratchpad_path("")


def test_scratchpad_gate_blocks_bash_for_ida():
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        agent_type="ida:ida",
        raw={"tool_name": "Bash", "tool_input": {"command": "echo test"}},
    )
    res = scratchpad_write_gate(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "Tool 'Bash' is prohibited for Ida" in res.inject_text


def test_scratchpad_gate_blocks_edit_for_ida():
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Edit",
        agent_type="aops:ida",
        raw={"tool_name": "Edit", "tool_input": {"file_path": "/workspace/README.md"}},
    )
    res = scratchpad_write_gate(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "Tool 'Edit' is prohibited for Ida" in res.inject_text


def test_scratchpad_gate_blocks_pkb_writes_for_ida():
    write_tools = [
        "pkb__create",
        "pkb__create_task",
        "pkb__update_task",
        "pkb__update_body",
        "pkb__edit_body",
        "pkb__append",
        "pkb__delete",
        "pkb__batch_update",
        "pkb__batch_merge",
        "pkb__decompose_task",
        "pkb__claim_task",
        "mcp__plugin_pkb_services__pkb__create_task",
        "mcp__plugin_pkb_services__pkb__update_task",
    ]
    for tool_name in write_tools:
        ctx = HookContext(
            client="claude",
            event="PreToolUse",
            tool=tool_name,
            agent_type="ida:ida",
            raw={"tool_name": tool_name, "tool_input": {"id": "task_123"}},
        )
        res = scratchpad_write_gate(ctx)
        assert res is not None, f"Expected refusal for {tool_name}"
        assert res.kind is Kind.REFUSE
        assert f"PKB write tool '{tool_name}' is prohibited for Ida" in res.inject_text


def test_scratchpad_gate_blocks_write_outside_scratchpad():
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Write",
        agent_type="ida:ida",
        raw={
            "tool_name": "Write",
            "tool_input": {"file_path": "/workspace/test.txt", "content": "bad"},
        },
    )
    res = scratchpad_write_gate(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "Writing outside session scratchpad directory" in res.inject_text


def test_scratchpad_gate_allows_write_inside_scratchpad():
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Write",
        agent_type="ida:ida",
        raw={
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/opt/nic/tmp/claude-1000/aops/session-test/scratchpad/plan.md",
                "content": "ok",
            },
        },
    )
    res = scratchpad_write_gate(ctx)
    assert res is None


def test_scratchpad_gate_ignores_non_ida_agents():
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        agent_type="aops:james",
        raw={"tool_name": "Bash", "tool_input": {"command": "echo test"}},
    )
    res = scratchpad_write_gate(ctx)
    assert res is None


# --- Citation Enforcement Hook Tests ---


def test_citation_enforcement_blocks_unverified_pkb_id(tmp_path: Path):
    # Empty transcript: no tool calls made
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": "What is the status?"}}) + "\n"
    )

    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={
            "last_assistant_message": "Per task_206a0832, we should investigate the hook performance.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is not None
    assert res.kind is Kind.BLOCK
    assert "Citation enforcement violation" in res.inject_text
    assert "task_206a0832" in res.inject_text


def test_citation_enforcement_blocks_unverified_path_line(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": "Where is the bug?"}}) + "\n"
    )

    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={
            "last_assistant_message": "Look at plugins/ida/agents/ida.md:25 for dispatch rules.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is not None
    assert res.kind is Kind.BLOCK
    assert "Citation enforcement violation" in res.inject_text
    assert "plugins/ida/agents/ida.md:25" in res.inject_text


def test_citation_enforcement_allows_verified_pkb_id(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"type": "user", "message": {"content": "What is the status of task_206a0832?"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "pkb__get_task",
                        "input": {"id": "task_206a0832"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": '{"id": "task_206a0832", "title": "Measure performance"}',
                    }
                ]
            },
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={
            "last_assistant_message": "Per task_206a0832 (Measure performance), the task is in inbox.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is None


def test_citation_enforcement_allows_verified_path_line(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"type": "user", "message": {"content": "Check the code."}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/workspace/lib/polecat/cli.py"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "content": "123: def _build_inner_command():"}]
            },
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={
            "last_assistant_message": "See lib/polecat/cli.py:123 for inner command construction.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is None


def test_citation_enforcement_allows_delegate_report_citations(tmp_path: Path):
    # When James investigates and reports back to Ida within the same turn
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"type": "user", "message": {"content": "Investigate mem_ce1f917d"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Agent",
                        "input": {"prompt": "Check mem_ce1f917d in pkb"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "James here: I checked mem_ce1f917d and verified tests/test_core.py:55.",
                    }
                ]
            },
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={
            "last_assistant_message": "James confirmed mem_ce1f917d per tests/test_core.py:55.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is None


def test_citation_enforcement_ignores_non_ida_agents(tmp_path: Path):
    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="aops:james",
        raw={
            "last_assistant_message": "Per task_unretrieved, this should not be checked for James.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is None


def test_citation_enforcement_ignores_generic_placeholders():
    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        raw={
            "last_assistant_message": "Please supply the task_id or note_id for this request.",
        },
    )
    res = citation_enforcement_gate(ctx)
    assert res is None


# --- PKB Injection Hook Tests ---


def test_pkb_injection_skips_ida():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pkb_handlers_direct", PKB_HOOKS / "handlers.py")
    assert spec is not None and spec.loader is not None
    pkb_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pkb_mod)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        raw={"prompt": "what is academicOps?"},
    )
    res = pkb_mod.search_the_pkb(ctx)
    assert res is None
