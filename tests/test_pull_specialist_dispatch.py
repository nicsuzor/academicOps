"""Tests for /pull specialist-agent dispatch rule (issue #733).

Verifies that the /pull command file contains an explicit pre-EXECUTE
short-circuit that dispatches to a specialist sub-agent when the task's
assignee names one (aops-core:* or bare `polecat`).

Also verifies the corresponding heuristic exists in HEURISTICS.md.
"""

import re
import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.paths import get_commands_dir, get_heuristics_file  # noqa: E402

PULL_PATH = get_commands_dir() / "pull.md"
HEURISTICS_PATH = get_heuristics_file()  # type: ignore[misc]


class TestPullSpecialistDispatch:
    """Validate the specialist dispatch rule in /pull and HEURISTICS."""

    def test_pull_command_exists(self) -> None:
        assert PULL_PATH.exists(), f"/pull command file missing: {PULL_PATH}"

    def test_pull_has_specialist_dispatch_section(self) -> None:
        """/pull SKILL must contain a pre-EXECUTE specialist dispatch step."""
        content = PULL_PATH.read_text(encoding="utf-8")
        # Heading must exist and explicitly call out specialist dispatch
        assert re.search(
            r"^###\s+Step\s+1\.7.*Specialist", content, flags=re.MULTILINE | re.IGNORECASE
        ), "Step 1.7 (Specialist Agent Dispatch) heading missing from /pull"

    def test_pull_lists_namespace_prefixes(self) -> None:
        """The dispatch rule must list aops-core: and polecat."""
        content = PULL_PATH.read_text(encoding="utf-8")
        for needle in ("aops-core:", "polecat"):
            assert needle in content, f"specialist namespace {needle!r} missing from /pull"

    def test_pull_dispatches_via_agent_tool(self) -> None:
        """The rule must instruct dispatch via the Agent tool with subagent_type."""
        content = PULL_PATH.read_text(encoding="utf-8")
        assert "Agent(" in content, "Agent tool dispatch example missing from /pull"
        assert "subagent_type" in content, "subagent_type parameter missing from /pull"

    def test_pull_short_circuits_inline_execute(self) -> None:
        """The rule must HALT / not fall through to inline EXECUTE."""
        content = PULL_PATH.read_text(encoding="utf-8")
        # Look in the specialist section specifically
        match = re.search(
            r"###\s+Step\s+1\.7.*?(?=^###\s)",
            content,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        assert match, "Step 1.7 section not isolatable for short-circuit assertion"
        section = match.group(0)
        assert re.search(
            r"\bHALT\b|do NOT (?:continue|fall through|execute)",
            section,
            flags=re.IGNORECASE,
        ), "Step 1.7 does not explicitly HALT / forbid inline execution"

    def test_heuristics_has_specialist_dispatch_rule(self) -> None:
        """HEURISTICS.md must include a corresponding rule for the supervisor."""
        content = HEURISTICS_PATH.read_text(encoding="utf-8")
        # Heuristic must mention specialist dispatch and Agent tool
        assert re.search(r"specialist", content, flags=re.IGNORECASE), (
            "no specialist-dispatch heuristic found in HEURISTICS.md"
        )
        assert "Agent tool" in content or "subagent_type" in content, (
            "specialist heuristic does not reference Agent tool / subagent_type"
        )


class TestPullScenarioMarsha:
    """Scenario fixture: assignee=aops-core:marsha must NOT trigger inline EXECUTE."""

    def test_marsha_assignee_routes_to_dispatch(self) -> None:
        """A task assigned to aops-core:marsha is matched by the namespace rule."""
        content = PULL_PATH.read_text(encoding="utf-8")
        assignee = "aops-core:marsha"
        # The bare name extraction logic must be documented (strip prefix → marsha)
        # We assert the rule pattern itself exists; the bare name is derived at runtime.
        assert "aops-core:" in content, "aops-core: namespace handling missing"
        # And the prefix-strip behaviour must be specified
        assert re.search(
            r"strip\s+the\s+`?aops-core:`?\s+prefix",
            content,
            flags=re.IGNORECASE,
        ), "aops-core: prefix stripping not documented in /pull"
        # Sanity: assignee value structure matches what the rule keys on
        assert assignee.startswith("aops-core:")
        assert assignee.split(":", 1)[1] == "marsha"
