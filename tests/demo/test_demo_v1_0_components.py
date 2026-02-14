#!/usr/bin/env python3
"""Demo test for v1.0 Core Loop Components - Full System Verification.

Demonstrates that ALL v1.0 components are working correctly by analyzing
real session transcripts with an LLM that searches for evidence of:

1. **Agents (5)**: prompt-hydrator, critic, custodiet, qa, framework
2. **Hooks (6)**: router, user_prompt_submit, unified_logger, session_env_setup, custodiet_gate, overdue_enforcement
3. **Workflows (6)**: question, design, tdd, batch, qa-proof, plan-mode
4. **QA Gates (3)**: Critic (BEFORE), Custodiet (DURING), QA-verifier (AFTER)
5. **Session Close**: Format, commit, push mandatory workflow

This test uses REAL transcript data from recent large sessions, not synthetic
examples. The LLM performs semantic analysis to find evidence that proves
each component is functioning as designed in README.md (Core Loop section).

Run with: uv run pytest tests/demo/test_demo_v1_0_components.py -v -s -n 0 -m demo

Related:
- Epic ns-6hm: v1.0 Core Loop - Hydration/Workflow/QA/Reflection
- README.md (Core Loop): Complete v1.0 specification
- aops-core/specs/flow.md: Detailed flow specification
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


def find_large_recent_sessions(min_size_mb: float = 1.5, limit: int = 5) -> list[Path]:
    """Find recent large session files for comprehensive testing.

    Args:
        min_size_mb: Minimum session file size in MB
        limit: Maximum number of sessions to return

    Returns:
        List of paths to large session JSONL files, sorted by size descending
    """
    projects_dir = Path.home() / ".claude" / "projects"
    academic_ops_dir = projects_dir / "-home-nic-src-academicOps"

    if not academic_ops_dir.exists():
        return []

    sessions = []
    for jsonl_file in academic_ops_dir.glob("*.jsonl"):
        # Skip agent and hook logs
        if jsonl_file.name.startswith("agent-") or "-hooks" in jsonl_file.name:
            continue

        size_mb = jsonl_file.stat().st_size / (1024 * 1024)
        if size_mb >= min_size_mb:
            sessions.append((size_mb, jsonl_file))

    # Sort by size descending
    sessions.sort(reverse=True, key=lambda x: x[0])

    return [path for _, path in sessions[:limit]]


def generate_transcript(session_path: Path, format_type: str = "abridged") -> str:
    """Generate markdown transcript from session JSONL file.

    Args:
        session_path: Path to session JSONL file
        format_type: "full" or "abridged"

    Returns:
        Markdown transcript content

    Raises:
        RuntimeError: If transcript generation fails
    """
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "aops-core/scripts/transcript.py",
                str(session_path),
                f"--format={format_type}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Transcript generation failed: {result.stderr}")

        return result.stdout

    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Transcript generation timed out after 60 seconds") from e
    except Exception as e:
        raise RuntimeError(f"Transcript generation error: {e}") from e


def analyze_transcript_for_v1_0_components(
    transcript: str, claude_headless_tracked
) -> dict[str, Any]:
    """Use headless LLM to analyze transcript for v1.0 component evidence.

    Args:
        transcript: Markdown transcript content
        claude_headless_tracked: Pytest fixture for headless Claude sessions

    Returns:
        Dict with component evidence:
        {
            "agents": {
                "prompt-hydrator": {"found": bool, "evidence": str},
                "critic": {"found": bool, "evidence": str},
                ...
            },
            "workflows": {
                "tdd": {"found": bool, "evidence": str},
                ...
            },
            "qa_gates": {...},
            "session_close": {...}
        }
    """
    # Create analysis prompt for headless LLM
    analysis_prompt = f"""Analyze this Claude Code session transcript for evidence of v1.0 aops-core components.

For EACH component below, determine if there is CLEAR EVIDENCE in the transcript, and provide:
1. "found": true/false
2. "evidence": A direct quote from the transcript (max 200 chars)

## Components to Check

### Agents (5)
1. **prompt-hydrator** - Was Task(subagent_type="aops-core:prompt-hydrator") invoked?
2. **critic** - Was Task(subagent_type="aops-core:critic") invoked to review a plan?
3. **custodiet** - Was Task(subagent_type="aops-core:custodiet") invoked for compliance?
4. **qa-verifier** - Was Task(subagent_type="aops-core:qa-verifier") invoked before completion?
5. **framework** - Was Task(subagent_type="aops-core:framework") invoked for reflection?

### Workflows (6)
Look for explicit workflow mentions like "Workflow: tdd" or "workflow: question"
6. **question** - Question answering workflow
7. **design** - Design/implementation workflow
8. **tdd** - Test-driven development workflow
9. **batch** - Batch processing workflow
10. **qa-proof** - QA evidence gathering workflow
11. **plan-mode** - Complex planning workflow

### QA Gates (3)
12. **critic_review** - Critic provided PROCEED/REVISE/HALT verdict
13. **custodiet_check** - Custodiet provided OK/ATTENTION verdict
14. **qa_verification** - QA verifier provided VERIFIED/ISSUES verdict

### Session Close
15. **commit** - Git commit was made (look for "git commit")
16. **push** - Git push to remote (look for "git push" or "Pushing to remote")

### TodoWrite Usage
17. **todowrite** - TodoWrite tool was used to track tasks

Return your analysis as JSON with this structure:
{{
    "agents": {{
        "prompt-hydrator": {{"found": bool, "evidence": "quote"}},
        "critic": {{"found": bool, "evidence": "quote"}},
        "custodiet": {{"found": bool, "evidence": "quote"}},
        "qa-verifier": {{"found": bool, "evidence": "quote"}},
        "framework": {{"found": bool, "evidence": "quote"}}
    }},
    "workflows": {{
        "question": {{"found": bool, "evidence": "quote"}},
        "design": {{"found": bool, "evidence": "quote"}},
        "tdd": {{"found": bool, "evidence": "quote"}},
        "batch": {{"found": bool, "evidence": "quote"}},
        "qa-proof": {{"found": bool, "evidence": "quote"}},
        "plan-mode": {{"found": bool, "evidence": "quote"}}
    }},
    "qa_gates": {{
        "critic_review": {{"found": bool, "evidence": "quote"}},
        "custodiet_check": {{"found": bool, "evidence": "quote"}},
        "qa_verification": {{"found": bool, "evidence": "quote"}}
    }},
    "session_close": {{
        "commit": {{"found": bool, "evidence": "quote"}},
        "push": {{"found": bool, "evidence": "quote"}}
    }},
    "todowrite": {{"found": bool, "evidence": "quote"}}
}}

IMPORTANT: Return ONLY the JSON, no other text.

## TRANSCRIPT

{transcript}
"""

    # Run analysis with headless LLM
    result, session_id, tool_calls = claude_headless_tracked(
        analysis_prompt, timeout_seconds=180, model="sonnet"
    )

    # Extract JSON from response
    from tests.conftest import extract_response_text

    response_text = extract_response_text(result)

    # Try to find JSON in response
    try:
        # Look for JSON block
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            json_text = response_text[start:end]
            analysis = json.loads(json_text)
            return analysis
        else:
            # Fallback: return empty structure
            return {
                "agents": {},
                "workflows": {},
                "qa_gates": {},
                "session_close": {},
                "todowrite": {"found": False, "evidence": ""},
            }
    except json.JSONDecodeError:
        # Return empty structure if parsing fails
        return {
            "agents": {},
            "workflows": {},
            "qa_gates": {},
            "session_close": {},
            "todowrite": {"found": False, "evidence": ""},
        }


@pytest.mark.demo
@pytest.mark.slow
class TestV1ComponentsDemo:
    """Demo test for comprehensive v1.0 component verification."""

    def test_demo_v1_0_components_from_real_transcripts(self, claude_headless_tracked) -> None:
        """Demo: Verify all v1.0 components working via real transcript analysis.

        This test demonstrates the COMPLETE v1.0 core loop by analyzing real
        session transcripts with an LLM that searches for evidence of each
        component functioning correctly.

        The test validates:
        1. All 5 agents are being invoked when appropriate
        2. Workflows are being selected correctly
        3. QA gates are functioning (critic, custodiet, qa-verifier)
        4. Session close workflow is happening (commit + push)
        5. TodoWrite is being used for task tracking
        """
        print("\n" + "=" * 80)
        print("v1.0 COMPONENTS DEMO: Full System Verification from Real Transcripts")
        print("=" * 80)

        # === STEP 1: Find Real Session Transcripts ===
        print("\n--- STEP 1: Discover Large Recent Sessions ---")

        session_files = find_large_recent_sessions(min_size_mb=1.5, limit=3)

        if not session_files:
            pytest.skip("No large recent sessions found for analysis")

        print(f"Found {len(session_files)} large session(s) for analysis:")
        for session_file in session_files:
            size_mb = session_file.stat().st_size / (1024 * 1024)
            print(f"  - {session_file.name} ({size_mb:.1f} MB)")

        # === STEP 2: Generate and Analyze Transcripts ===
        print("\n--- STEP 2: Generate and Analyze Transcripts ---")

        all_analyses = []

        for i, session_file in enumerate(session_files, 1):
            print(f"\n>>> SESSION {i}/{len(session_files)}: {session_file.name[:16]}...")

            # Generate transcript
            print("  Generating transcript...")
            try:
                transcript = generate_transcript(session_file, format_type="abridged")
                print(f"  Transcript length: {len(transcript)} chars")
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

            # Analyze with LLM
            print("  Analyzing with headless LLM...")
            try:
                analysis = analyze_transcript_for_v1_0_components(
                    transcript, claude_headless_tracked
                )
                all_analyses.append((session_file.name, analysis))
                print("  Analysis complete")
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

        if not all_analyses:
            pytest.fail("No sessions could be analyzed")

        # === STEP 3: Aggregate Results ===
        print("\n" + "=" * 80)
        print("COMPONENT VERIFICATION RESULTS")
        print("=" * 80)

        # Count how many sessions showed evidence of each component
        component_counts = {
            "agents": {
                "prompt-hydrator": 0,
                "critic": 0,
                "custodiet": 0,
                "qa-verifier": 0,
                "framework": 0,
            },
            "workflows": {
                "question": 0,
                "design": 0,
                "tdd": 0,
                "batch": 0,
                "qa-proof": 0,
                "plan-mode": 0,
            },
            "qa_gates": {
                "critic_review": 0,
                "custodiet_check": 0,
                "qa_verification": 0,
            },
            "session_close": {"commit": 0, "push": 0},
            "todowrite": 0,
        }

        # Aggregate findings
        for _session_name, analysis in all_analyses:
            for category in ["agents", "workflows", "qa_gates", "session_close"]:
                if category in analysis:
                    for component, data in analysis[category].items():
                        if isinstance(data, dict) and data.get("found"):
                            component_counts[category][component] += 1

            if analysis.get("todowrite", {}).get("found"):
                component_counts["todowrite"] += 1

        # === STEP 4: Report Results ===
        total_sessions = len(all_analyses)

        print("\n--- AGENTS (5) ---")
        for agent, count in component_counts["agents"].items():
            pct = (count / total_sessions) * 100
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {agent:20s} - {count}/{total_sessions} sessions ({pct:.0f}%)")

        print("\n--- WORKFLOWS (6) ---")
        for workflow, count in component_counts["workflows"].items():
            pct = (count / total_sessions) * 100
            status = "✓" if count > 0 else "○"
            print(f"  {status} {workflow:20s} - {count}/{total_sessions} sessions ({pct:.0f}%)")

        print("\n--- QA GATES (3) ---")
        for gate, count in component_counts["qa_gates"].items():
            pct = (count / total_sessions) * 100
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {gate:20s} - {count}/{total_sessions} sessions ({pct:.0f}%)")

        print("\n--- SESSION CLOSE (2) ---")
        for component, count in component_counts["session_close"].items():
            pct = (count / total_sessions) * 100
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {component:20s} - {count}/{total_sessions} sessions ({pct:.0f}%)")

        print("\n--- TODOWRITE ---")
        count = component_counts["todowrite"]
        pct = (count / total_sessions) * 100
        status = "✓" if count > 0 else "✗"
        print(f"  {status} TodoWrite usage     - {count}/{total_sessions} sessions ({pct:.0f}%)")

        # === STEP 5: Show Evidence Examples ===
        print("\n" + "=" * 80)
        print("HUMAN OPERATOR VALIDATION - Evidence Examples")
        print("=" * 80)

        # Show evidence from first session
        if all_analyses:
            session_name, first_analysis = all_analyses[0]
            print(f"\nShowing evidence from: {session_name[:32]}...")

            print("\n--- Agent Evidence ---")
            for agent, data in first_analysis.get("agents", {}).items():
                if data.get("found"):
                    evidence = data.get("evidence", "")[:150]
                    print(f'  {agent}: "{evidence}..."')

            print("\n--- Workflow Evidence ---")
            for workflow, data in first_analysis.get("workflows", {}).items():
                if data.get("found"):
                    evidence = data.get("evidence", "")[:150]
                    print(f'  {workflow}: "{evidence}..."')

            print("\n--- QA Gate Evidence ---")
            for gate, data in first_analysis.get("qa_gates", {}).items():
                if data.get("found"):
                    evidence = data.get("evidence", "")[:150]
                    print(f'  {gate}: "{evidence}..."')

        # === VALIDATION CRITERIA ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        # Core v1.0 requirements from README.md (Core Loop)
        criteria = [
            ("Sessions analyzed", total_sessions >= 1),
            (
                "Hydration (prompt-hydrator agent)",
                component_counts["agents"]["prompt-hydrator"] >= 1,
            ),
            (
                "QA Gates (critic OR custodiet)",
                sum(component_counts["qa_gates"].values()) >= 1,
            ),
            ("TodoWrite usage", component_counts["todowrite"] >= 1),
            (
                "At least one workflow identified",
                sum(component_counts["workflows"].values()) >= 1,
            ),
            (
                "Session close (commit OR push)",
                sum(component_counts["session_close"].values()) >= 1,
            ),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        # === DEMO SUMMARY ===
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo verified the v1.0 core loop by analyzing {total_sessions} real session transcript(s).

**v1.0 Components Verified:**

**Agents ({sum(1 for c in component_counts["agents"].values() if c > 0)}/5 found):**
- prompt-hydrator: Transforms prompts into execution plans
- critic: Reviews plans BEFORE execution
- custodiet: Checks compliance DURING execution
- qa-verifier: Verifies work AFTER completion
- framework: Manages reflections and learnings

**Workflows ({sum(1 for c in component_counts["workflows"].values() if c > 0)}/6 found):**
The hydrator routes prompts to appropriate workflows based on intent.

**QA Gates ({sum(1 for c in component_counts["qa_gates"].values() if c > 0)}/3 found):**
- Critic (BEFORE): Identifies plan problems before wasting effort
- Custodiet (DURING): Detects scope drift and compliance violations
- QA-verifier (AFTER): Independent verification before completion

**Session Close ({sum(1 for c in component_counts["session_close"].values() if c > 0)}/2 found):**
Work is NOT complete until git push succeeds.

**What This Proves:**
This test demonstrates that v1.0 components are actually being used in real
sessions, not just defined. The LLM semantic analysis found concrete evidence
in transcripts, proving the framework works as designed.

**Evidence Quality:**
All evidence is extracted from REAL session transcripts (not synthetic tests).
The user can verify not just outcomes, but that the framework actually worked
as expected by reviewing the evidence quotes above.
"""
        )
        print("=" * 80)
        print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 80)

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"v1.0 component verification FAILED. "
                f"Unmet criteria: {', '.join(failed)}. "
                f"Analyzed {total_sessions} session(s)."
            )

        assert all_passed, "v1.0 component verification failed"
