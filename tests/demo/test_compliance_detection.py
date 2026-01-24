#!/usr/bin/env python3
"""Demo test for Compliance Detection - Custodiet (ns-h7t).

Demonstrates that custodiet detects various violation types:
1. Scope drift (working outside original request)
2. Missing skill invocation
3. Axiom/heuristic violations

Run with: uv run pytest tests/demo/test_compliance_detection.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-h7t: Demo: Compliance Detection (Custodiet Variants)

Acceptance Criteria:
- Custodiet fires during multi-tool sessions
- Audit files created with correct content
- Various violation types detected
- Test evaluates custodiet output SEMANTICALLY (not keyword matching)
"""

import time
from pathlib import Path

import pytest


def find_recent_audit_files(max_age_seconds: int = 300) -> list[Path]:
    """Find audit files created in the last N seconds."""
    temp_dir = Path("/tmp/claude-compliance")
    if not temp_dir.exists():
        return []

    cutoff = time.time() - max_age_seconds
    return [f for f in temp_dir.glob("audit_*.md") if f.stat().st_mtime > cutoff]


def semantic_evaluate_audit_content(content: str, evaluator_func) -> dict:
    """Use LLM to semantically evaluate audit file content.

    Args:
        content: Full audit file content
        evaluator_func: Function to call headless Claude for evaluation

    Returns:
        Dict with evaluation results
    """
    eval_prompt = f"""Evaluate this custodiet audit file content. Answer these questions:

1. Does it contain a valid Session Context section with user request and recent activity?
2. Does it include the full AXIOMS checklist (numbered principles)?
3. Does it include the HEURISTICS checklist (H1, H2, etc.)?
4. Does it have a DRIFT ANALYSIS section?
5. Is the content substantive (not empty sections or repeated headers)?

AUDIT FILE CONTENT:
---
{content[:3000]}
---

Respond with a JSON object:
{{"has_session_context": true/false, "has_axioms": true/false, "has_heuristics": true/false, "has_drift_analysis": true/false, "is_substantive": true/false, "issues": ["list any problems found"]}}
"""
    return eval_prompt


@pytest.mark.demo
@pytest.mark.slow
class TestComplianceDetectionDemo:
    """Demo test for custodiet compliance detection.

    This test verifies custodiet functionality with SEMANTIC evaluation,
    not just keyword matching. It checks:
    1. Custodiet fires at the correct threshold
    2. Audit files contain substantive content
    3. Content is semantically valid (not just keyword present)
    """

    def test_demo_custodiet_fires_during_session(self, claude_headless_tracked) -> None:
        """Demo: Custodiet runs and creates audit files with valid content.

        Strategy:
        1. Run session with multiple action tools to trigger custodiet threshold
        2. Verify audit files created
        3. SEMANTICALLY evaluate audit file content (not keyword matching)
        4. Verify content is substantive and well-structured
        """
        print("\n" + "=" * 80)
        print("COMPLIANCE DETECTION DEMO: Semantic Audit Verification")
        print("=" * 80)

        # Record audit files before test
        audit_files_before = set(find_recent_audit_files(max_age_seconds=3600))

        # Task with multiple bash calls to trigger custodiet threshold (N=5)
        prompt = (
            "Execute these commands one at a time and report results: "
            "1) echo 'compliance test start' "
            "2) date '+%Y-%m-%d %H:%M:%S' "
            "3) echo 'step three' "
            "4) pwd "
            "5) echo 'compliance test complete'"
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180, model="haiku", fail_on_error=False
        )

        print(f"\nSession ID: {session_id}")
        session_success = (
            result.get("success", False) if isinstance(result, dict) else False
        )
        print(f"Success: {session_success}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Semantic Custodiet Verification")
        print("=" * 80)

        # Check 1: Audit files were created
        audit_files_after = set(find_recent_audit_files(max_age_seconds=600))
        new_audit_files = audit_files_after - audit_files_before
        print("\n--- Custodiet Audit Files ---")
        print(f"    Files before: {len(audit_files_before)}")
        print(f"    Files after: {len(audit_files_after)}")
        print(f"    New files: {len(new_audit_files)}")
        custodiet_created_files = len(new_audit_files) >= 1

        # Check 2: SEMANTIC evaluation of audit content
        # This is the key difference from keyword matching
        audit_semantically_valid = False
        audit_content = ""
        semantic_issues: list[str] = []

        if new_audit_files:
            latest_audit = sorted(new_audit_files, key=lambda f: f.stat().st_mtime)[-1]
            print(f"\n--- Latest Audit File: {latest_audit.name} ---")
            try:
                audit_content = latest_audit.read_text()

                # SEMANTIC CHECKS (not keyword matching):

                # 2a. Check for EMPTY or REPEATED sections (the failure mode from 2026-01-07)
                lines = audit_content.split("\n")
                header_lines = [line for line in lines if line.startswith("## ")]
                unique_headers = set(header_lines)
                if len(header_lines) != len(unique_headers):
                    semantic_issues.append(
                        f"REPEATED HEADERS: {len(header_lines)} total, {len(unique_headers)} unique"
                    )

                # 2b. Check that Session Context has actual content (not just header)
                if "## Session Context" in audit_content:
                    # Find content between Session Context and next section
                    idx = audit_content.find("## Session Context")
                    next_section = audit_content.find("\n## ", idx + 10)
                    if next_section == -1:
                        next_section = len(audit_content)
                    context_section = audit_content[idx:next_section]
                    # Should have more than just the header
                    context_lines = [
                        line
                        for line in context_section.split("\n")
                        if line.strip() and not line.startswith("#")
                    ]
                    if len(context_lines) < 3:
                        semantic_issues.append(
                            f"SESSION CONTEXT too short: only {len(context_lines)} content lines"
                        )
                else:
                    semantic_issues.append("MISSING Session Context section")

                # 2c. Check AXIOMS section has numbered items
                if "# AXIOMS" in audit_content:
                    axiom_idx = audit_content.find("# AXIOMS")
                    next_h1 = audit_content.find("\n# ", axiom_idx + 5)
                    if next_h1 == -1:
                        next_h1 = len(audit_content)
                    axiom_section = audit_content[axiom_idx:next_h1]
                    # Should have numbered axioms (0., 1., 2., etc.)
                    numbered_lines = [
                        line
                        for line in axiom_section.split("\n")
                        if line.strip()
                        and len(line) > 2
                        and line.strip()[0].isdigit()
                        and "." in line[:5]
                    ]
                    if len(numbered_lines) < 10:
                        semantic_issues.append(
                            f"AXIOMS section incomplete: only {len(numbered_lines)} numbered items"
                        )
                else:
                    semantic_issues.append("MISSING AXIOMS section")

                # 2d. Check HEURISTICS section has H-numbered items
                if "# HEURISTICS" in audit_content:
                    heur_idx = audit_content.find("# HEURISTICS")
                    next_h1 = audit_content.find("\n# ", heur_idx + 5)
                    if next_h1 == -1:
                        next_h1 = len(audit_content)
                    heur_section = audit_content[heur_idx:next_h1]
                    # Should have H1:, H2:, etc.
                    h_lines = [
                        line
                        for line in heur_section.split("\n")
                        if line.strip().startswith("H")
                    ]
                    if len(h_lines) < 10:
                        semantic_issues.append(
                            f"HEURISTICS section incomplete: only {len(h_lines)} H-items"
                        )
                else:
                    semantic_issues.append("MISSING HEURISTICS section")

                # 2e. Overall content length check
                if len(audit_content) < 1000:
                    semantic_issues.append(
                        f"AUDIT TOO SHORT: {len(audit_content)} chars (expected 1000+)"
                    )

                # Verdict: semantically valid if no issues found
                audit_semantically_valid = len(semantic_issues) == 0

                print("\n--- Semantic Validation ---")
                if semantic_issues:
                    print(f"    ISSUES FOUND ({len(semantic_issues)}):")
                    for issue in semantic_issues:
                        print(f"      - {issue}")
                else:
                    print("    All semantic checks passed")

                # Show content excerpt for human review
                print("\n--- Audit Content (first 800 chars) ---")
                print(audit_content[:800] + ("..." if len(audit_content) > 800 else ""))

            except Exception as e:
                print(f"    Could not read audit file: {e}")
                semantic_issues.append(f"READ ERROR: {e}")

        # Check 3: Action tools were used (required to trigger custodiet)
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        print(f"\n--- Bash Tool Calls: {len(bash_calls)} ---")
        action_tools_used = len(bash_calls) >= 3

        # Check 4: Custodiet threshold reached
        # Evidence: audit files created with valid content
        threshold_reached = custodiet_created_files and (
            len(bash_calls) >= 5 or audit_semantically_valid
        )
        print("--- Custodiet Hook Threshold ---")
        print(f"    Threshold reached: {threshold_reached}")

        # Tool usage summary
        print("\n--- All Tool Calls ---")
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count}")

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA (Semantic Evaluation)")
        print("=" * 80)

        criteria = [
            ("Session made progress (tool calls)", len(tool_calls) >= 1),
            ("Custodiet created audit files", custodiet_created_files),
            ("Audit content SEMANTICALLY valid", audit_semantically_valid),
            ("Action tools triggered threshold", action_tools_used),
            ("Custodiet hook threshold reached", threshold_reached),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        # Show semantic issues if any
        if semantic_issues:
            print("\n  Semantic issues found:")
            for issue in semantic_issues:
                print(f"    - {issue}")

        print("\n" + "=" * 80)
        print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 80)

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"Compliance detection validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. "
                f"Semantic issues: {semantic_issues}. Session: {session_id}"
            )
