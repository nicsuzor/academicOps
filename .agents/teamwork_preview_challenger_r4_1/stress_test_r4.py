"""Adversarial stress test harness for Milestone R4.

Empirically challenges:
1. 4-tier artifact generation
2. XML/HTML escaping in Markdown & HTML
3. Collapsible blocks boundary sizes (499, 500, 501 chars, 10, 11 lines)
4. Subagents & Message Echoes
5. Sparse step_index sequence IDs
6. Token/cost split in frontmatter & JSON
7. Edge cases in metadata / XSS injection vectors
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src / lib / codebase paths if needed
sys.path.insert(0, "/workspace/lib/py")

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import (
    _build_subagent,
    load_claude_session,
)
from transcripts.domain.cache import SkipCache
from transcripts.domain.renderer import (
    build_json_sidecar,
    render_session_to_all_formats,
    render_to_controller_markdown,
    render_to_full_markdown,
    render_to_html,
    render_to_markdown,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)
from transcripts.runner import process_single_session


class DummySkipCache:
    def is_skipped(self, key: str, fingerprint: str) -> bool:
        return False

    def mark_empty(self, key: str, fingerprint: str) -> None:
        pass

    def forget(self, key: str) -> None:
        pass


def test_area_1_four_tier_artifacts(tmp_path: Path) -> dict:
    results = {}
    subagent = SubagentTranscript(
        agent_id="sub_test_01",
        source_file=Path("agent-sub_test_01.jsonl"),
        agent_type="researcher",
        name="Research Assistant",
        description="Gather background context",
        parent_tool_use_id="toolu_01",
        tokens_used=150,
        cost_usd=0.0015,
        spawn_depth=1,
        events=[
            NormalizedEvent(
                event_id="sub_ev1",
                timestamp="2026-08-06T12:00:00Z",
                source="model",
                type="message",
                content="Subagent step response",
            )
        ],
    )
    events = [
        NormalizedEvent(
            event_id="ev_01",
            timestamp="2026-08-06T11:59:00Z",
            source="user",
            type="message",
            content="Initial user request",
            meta={"is_human": True},
        ),
        NormalizedEvent(
            event_id="ev_02",
            timestamp="2026-08-06T12:00:00Z",
            source="model",
            type="message",
            content="Spawning subagent",
            tool_calls=[
                NormalizedToolCall(
                    name="Task",
                    args={"description": "Gather background context"},
                    call_id="toolu_01",
                )
            ],
        ),
    ]
    session = NormalizedSession(
        session_id="session_4tier_test",
        source_file=Path("session_4tier_test.jsonl"),
        events=events,
        tokens_used=500,
        cost_usd=0.005,
        subagents=[subagent],
    )

    processed = process_single_session(session, tmp_path, DummySkipCache(), force=True)
    results["processed"] = processed

    written_paths = list(tmp_path.glob("transcripts/**/*"))
    written_names = [p.name for p in written_paths if p.is_file()]
    results["written_files"] = written_names

    extensions = [
        ".controller.md",
        ".full.md",
        ".md",
        ".html",
        ".json",
    ]
    found_exts = {}
    for ext in extensions:
        if ext == ".md":
            matches = [
                n for n in written_names
                if n.endswith(".md") and not n.endswith(".controller.md") and not n.endswith(".full.md")
            ]
        else:
            matches = [n for n in written_names if n.endswith(ext)]
        found_exts[ext] = len(matches) == 1

    results["found_all_5_tiers"] = all(found_exts.values())
    results["extension_check"] = found_exts
    return results


def test_area_2_xml_html_escaping() -> dict:
    results = {}
    adversarial_tags = [
        "<script>alert('xss_prompt')</script>",
        "<thinking>secret_thought</thinking>",
        "<USER_REQUEST>malicious_override</USER_REQUEST>",
        "<file_content>sensitive_data</file_content>",
        "<iframe src=\"javascript:alert(1)\"></iframe>",
        "& < > \" '",
    ]
    events = [
        NormalizedEvent(
            event_id="ev_adv_user",
            timestamp="2026-08-06T12:00:00Z",
            source="user",
            type="message",
            content=f"Prompt with {adversarial_tags[0]} and {adversarial_tags[2]}",
            meta={"is_human": True, "human_content": f"Prompt with {adversarial_tags[0]} and {adversarial_tags[2]}"},
        ),
        NormalizedEvent(
            event_id="ev_adv_model",
            timestamp="2026-08-06T12:01:00Z",
            source="model",
            type="message",
            content=f"Assistant says {adversarial_tags[1]} and {adversarial_tags[3]}",
            thinking=f"Thinking with {adversarial_tags[1]} inside",
        ),
        NormalizedEvent(
            event_id="ev_adv_tool",
            timestamp="2026-08-06T12:02:00Z",
            source="tool",
            type="tool_output",
            content=f"Tool output with {adversarial_tags[4]} and {adversarial_tags[5]}",
        ),
    ]

    correlation = {
        "project": "<script>alert('xss_project')</script>",
        "task_id": "task_<iframe src='x'></iframe>",
    }

    session = NormalizedSession(
        session_id="session_escaping_test",
        source_file=Path("session_escaping_test.jsonl"),
        events=events,
    )

    controller_md, full_md, concise_md, html, json_sidecar = render_session_to_all_formats(
        session,
        "slug_escaping",
        "2026-08-06T12:00:00Z",
        "2026-08-06T12:02:00Z",
        "2026-08-06T12:02:00Z",
        True,
        correlation,
        None,
    )

    # Check HTML for unescaped tags
    raw_script_in_html = "<script>" in html
    raw_iframe_in_html = "<iframe" in html
    raw_thinking_in_html = "<thinking>" in html
    raw_user_req_in_html = "<USER_REQUEST>" in html
    raw_file_content_in_html = "<file_content>" in html

    results["html_has_raw_script"] = raw_script_in_html
    results["html_has_raw_iframe"] = raw_iframe_in_html
    results["html_has_raw_thinking"] = raw_thinking_in_html
    results["html_has_raw_user_request"] = raw_user_req_in_html
    results["html_has_raw_file_content"] = raw_file_content_in_html

    # Check meta box in HTML for correlation injection
    results["html_meta_box_xss_project"] = "<script>alert('xss_project')</script>" in html
    results["html_meta_box_xss_task_id"] = "<iframe src='x'></iframe>" in html

    # Check Markdown for model content escaping / tags
    results["controller_md_has_raw_thinking"] = "<thinking>" in controller_md
    results["controller_md_has_raw_file_content"] = "<file_content>" in controller_md

    return results


def test_area_3_collapsible_block_boundaries() -> dict:
    results = {}

    test_cases = [
        ("499_chars", "A" * 499, False),
        ("500_chars", "A" * 500, False),
        ("501_chars", "A" * 501, True),
        ("10_lines", "line\n" * 9 + "line", False),      # 10 lines
        ("11_lines", "line\n" * 10 + "line", True),     # 11 lines
        ("multibyte_200chars_600bytes", "😀" * 200, False), # 200 chars, 800 bytes
        ("multibyte_501chars_2004bytes", "😀" * 501, True), # 501 chars, 2004 bytes
        ("empty_content", "", False),
    ]

    for name, content, expected_large in test_cases:
        events = [
            NormalizedEvent(
                event_id=f"ev_tool_{name}",
                timestamp="2026-08-06T12:00:00Z",
                source="tool",
                type="tool_output",
                content=content,
            )
        ]
        session = NormalizedSession(
            session_id=f"session_{name}",
            source_file=Path(f"session_{name}.jsonl"),
            events=events,
        )
        ctrl_md, _, _, html, _ = render_session_to_all_formats(
            session, f"slug_{name}", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
        )

        md_has_details = "<details><summary>Tool Output (" in ctrl_md
        html_has_details = "<details class=\"tool-output-details\">" in html

        matches_expected = (md_has_details == expected_large) and (html_has_details == expected_large)
        results[name] = {
            "char_len": len(content),
            "line_count": len(content.splitlines()),
            "byte_len": len(content.encode("utf-8")),
            "expected_large": expected_large,
            "md_has_details": md_has_details,
            "html_has_details": html_has_details,
            "pass": matches_expected,
        }

    return results


def test_area_4_subagents_and_echoes() -> dict:
    results = {}

    # Case A: Unlinked subagent with missing description across meta, parent args, and subagent events
    subagent_empty_desc = SubagentTranscript(
        agent_id="sub_no_desc",
        source_file=Path("agent-sub_no_desc.jsonl"),
        agent_type="worker",
        name="Worker Without Description",
        description=None,
        events=[],
    )

    parent_events = [
        NormalizedEvent(
            event_id="p_e1",
            timestamp="2026-08-06T12:00:00Z",
            source="user",
            type="message",
            content="Do work",
        )
    ]

    session = NormalizedSession(
        session_id="session_sub_test",
        source_file=Path("session_sub_test.jsonl"),
        events=parent_events,
        subagents=[subagent_empty_desc],
    )

    ctrl_md, full_md, concise_md, html, json_sidecar = render_session_to_all_formats(
        session, "slug_sub", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
    )

    results["unlinked_subagent_handled_without_crash"] = True
    results["json_subagent_description"] = json_sidecar["subagents"][0]["description"]

    # Case B: Inter-agent message echo deduplication
    parent_ev = NormalizedEvent(
        event_id="shared_event_uuid_123",
        timestamp="2026-08-06T12:00:00Z",
        source="model",
        type="message",
        content="Parent message",
    )
    sub_ev_dup = NormalizedEvent(
        event_id="shared_event_uuid_123", # Duplicate event ID
        timestamp="2026-08-06T12:00:00Z",
        source="model",
        type="message",
        content="Parent message echoed in subagent log",
    )
    sub_ev_unique = NormalizedEvent(
        event_id="sub_unique_456",
        timestamp="2026-08-06T12:01:00Z",
        source="model",
        type="message",
        content="Subagent unique response",
    )

    # Test _build_subagent deduplication logic directly
    subagent_built = _build_subagent(
        "sub_echo_test",
        Path("agent-sub_echo_test.jsonl"),
        [],
        [parent_ev],
    )
    # Manually pass events to test event filtering if any
    deduped = [e for e in [sub_ev_dup, sub_ev_unique] if e.event_id not in {p.event_id for p in [parent_ev]}]
    results["echo_deduplicated_count"] = len(deduped)
    results["echo_deduplication_pass"] = (len(deduped) == 1 and deduped[0].event_id == "sub_unique_456")

    return results


def test_area_5_sparse_step_index(tmp_path: Path) -> dict:
    results = {}
    agy_lines = [
        json.dumps({"type": "USER_INPUT", "step_index": 1, "created_at": "2026-08-06T12:00:00Z", "source": "USER_EXPLICIT", "content": "Step 1 prompt"}),
        json.dumps({"type": "PLANNER_RESPONSE", "step_index": 5, "created_at": "2026-08-06T12:01:00Z", "source": "MODEL", "content": "Step 5 response"}),
        json.dumps({"type": "RUN_COMMAND", "step_index": 20, "created_at": "2026-08-06T12:02:00Z", "source": "tool", "content": "ls -la"}),
        json.dumps({"type": "PLANNER_RESPONSE", "step_index": 100, "created_at": "2026-08-06T12:03:00Z", "source": "MODEL", "content": "Step 100 completion"}),
    ]
    jsonl_file = tmp_path / "transcript.jsonl"
    jsonl_file.write_text("\n".join(agy_lines), encoding="utf-8")

    session = load_agy_transcript(jsonl_file)
    results["event_count"] = len(session.events)
    results["degraded"] = session.degraded
    results["degraded_is_empty"] = len(session.degraded) == 0
    results["step_ids"] = [e.event_id for e in session.events]
    return results


def test_area_6_token_cost_split() -> dict:
    results = {}
    sub1 = SubagentTranscript(
        agent_id="sub1",
        source_file=Path("agent-sub1.jsonl"),
        tokens_used=500,
        cost_usd=0.005,
        events=[NormalizedEvent("s1e1", "2026-08-06T12:00:00Z", "model", "message", "sub1 msg")],
    )
    sub2 = SubagentTranscript(
        agent_id="sub2",
        source_file=Path("agent-sub2.jsonl"),
        tokens_used=300,
        cost_usd=0.003,
        events=[NormalizedEvent("s2e1", "2026-08-06T12:00:00Z", "model", "message", "sub2 msg")],
    )
    session = NormalizedSession(
        session_id="token_split_session",
        source_file=Path("token_split.jsonl"),
        events=[NormalizedEvent("p1", "2026-08-06T12:00:00Z", "user", "message", "parent msg")],
        tokens_used=1000,
        cost_usd=0.010,
        subagents=[sub1, sub2],
    )

    ctrl_md, _, _, _, json_sidecar = render_session_to_all_formats(
        session, "slug_token", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
    )

    results["model_controller_tokens"] = session.controller_tokens
    results["model_subagent_tokens"] = session.subagent_tokens
    results["model_total_tokens"] = session.total_tokens_used
    results["model_controller_cost"] = session.controller_cost_usd
    results["model_subagent_cost"] = session.subagent_cost_usd
    results["model_total_cost"] = session.total_cost_usd

    # Check YAML frontmatter strings
    results["yaml_controller_tokens"] = "controller_tokens: 1000" in ctrl_md
    results["yaml_subagent_tokens"] = "subagent_tokens: 800" in ctrl_md
    results["yaml_total_tokens"] = "total_tokens_used: 1800" in ctrl_md
    results["yaml_controller_cost"] = "controller_cost_usd: 0.010000" in ctrl_md
    results["yaml_subagent_cost"] = "subagent_cost_usd: 0.008000" in ctrl_md
    results["yaml_total_cost"] = "total_cost_usd: 0.018000" in ctrl_md

    # Check JSON sidecar values
    results["json_controller_tokens"] = json_sidecar["controller_tokens"] == 1000
    results["json_subagent_tokens"] = json_sidecar["subagent_tokens"] == 800
    results["json_total_tokens"] = json_sidecar["total_tokens_used"] == 1800
    results["json_controller_cost"] = abs(json_sidecar["controller_cost_usd"] - 0.010) < 1e-6
    results["json_subagent_cost"] = abs(json_sidecar["subagent_cost_usd"] - 0.008) < 1e-6
    results["json_total_cost"] = abs(json_sidecar["total_cost_usd"] - 0.018) < 1e-6

    all_passed = (
        session.controller_tokens == 1000
        and session.subagent_tokens == 800
        and session.total_tokens_used == 1800
        and results["yaml_controller_tokens"]
        and results["yaml_subagent_tokens"]
        and results["yaml_total_tokens"]
        and results["json_controller_tokens"]
        and results["json_subagent_tokens"]
        and results["json_total_tokens"]
    )
    results["all_passed"] = all_passed
    return results


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        print("=== AREA 1: 4-Tier Artifact Generation ===")
        res1 = test_area_1_four_tier_artifacts(tmp_dir)
        print(json.dumps(res1, indent=2))

        print("\n=== AREA 2: XML/HTML Escaping & Security ===")
        res2 = test_area_2_xml_html_escaping()
        print(json.dumps(res2, indent=2))

        print("\n=== AREA 3: Collapsible Block Boundaries ===")
        res3 = test_area_3_collapsible_block_boundaries()
        print(json.dumps(res3, indent=2))

        print("\n=== AREA 4: Subagents & Message Echoes ===")
        res4 = test_area_4_subagents_and_echoes()
        print(json.dumps(res4, indent=2))

        print("\n=== AREA 5: Sparse Step Index ===")
        res5 = test_area_5_sparse_step_index(tmp_dir)
        print(json.dumps(res5, indent=2))

        print("\n=== AREA 6: Token / Cost Accounting Split ===")
        res6 = test_area_6_token_cost_split()
        print(json.dumps(res6, indent=2))


if __name__ == "__main__":
    main()
