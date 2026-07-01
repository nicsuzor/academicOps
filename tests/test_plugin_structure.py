#!/usr/bin/env python3
"""
Lint gates for aops-core plugin instruction files.
"""

import re
from pathlib import Path

import pytest

from polecat.prompt_template import PKB_HALT_SENTINEL

REPO_ROOT = Path(__file__).parent.parent
PLUGIN_ROOT = REPO_ROOT / "aops-core"


class TestNoProjectInferenceByPrefix:
    """Skill bodies must not instruct agents to infer project membership from
    task ID prefixes or by walking parent chains. Use ``list_tasks(project=...)``
    or ``frontmatter.project`` instead. See task-3dfb97b5 / nicsuzor/academicOps#579.
    """

    # Affirmative imperatives only — negative guidance ("do not infer ... from ID prefix")
    # is allowed and required.
    PROHIBITED_PATTERNS = [
        r"\binfer\s+(?:the\s+)?project\s+from\s+(?:the\s+)?(?:task\s+)?(?:ID|id)\s+prefix",
        r"\buse\s+(?:the\s+)?(?:task\s+)?(?:ID|id)\s+prefix\s+to\s+(?:scope|determine|identify|infer)",
        r"\bwalk\s+(?:up\s+)?the\s+parent\s+chain\s+to\s+scope\s+to\s+(?:a\s+)?project",
    ]

    def test_skill_bodies_do_not_instruct_prefix_inference(self) -> None:
        skills_dir = PLUGIN_ROOT / "skills"
        commands_dir = PLUGIN_ROOT / "commands"
        agents_dir = PLUGIN_ROOT / "agents"

        violations: list[str] = []
        for root in (skills_dir, commands_dir, agents_dir):
            if not root.is_dir():
                continue
            for md in root.rglob("*.md"):
                text = md.read_text()
                for pat in self.PROHIBITED_PATTERNS:
                    for m in re.finditer(pat, text, re.IGNORECASE):
                        violations.append(f"{md}:{m.start()}: matched /{pat}/")
        assert not violations, "Prohibited project-inference instructions:\n" + "\n".join(
            violations
        )


class TestCoreMdPkbHalt:
    """.agents/CORE.md must contain the PKB-HALT sentinel so it binds for every
    interactive/in-repo agent surface (load-bearing constraint from aops-0203b9cb).

    Supersedes the retired ``TestJuniorMdPkbHalt`` (2026-07-01): that test
    asserted the sentinel on `aops-core/agents/junior.md`, which was retired
    from this plugin during the 2026-07 simplification pass (Junior moved into
    userspace, out of the redistributable package — see
    specs/agents/interactive-coworking.md's revision note). Per the settled
    doctrine in that same file, PKB-HALT is meant to live as ONE injected copy
    in the session-start SSoT (`.agents/CORE.md`), not duplicated per-agent —
    so the replacement assertion targets CORE.md directly rather than the
    plugin's remaining head agent (`aops-core/agents/ida.md`), which correctly
    carries no per-agent copy.

    Asserts inclusion of PKB_HALT_SENTINEL (from polecat.prompt_template), not
    hardcoded prose tokens — the sentinel is the protocol-specified transcript
    marker that enables post-hoc audit. Whether the surrounding wording does
    its job is owned by review and the runtime verification task aops-f00c699f,
    not by a string-match here (AXIOMS#judgment-non-delegable).

    This test is designed to FAIL if the PKB-HALT instruction is removed or
    silently dropped from CORE.md — that is the property a load-bearing test
    must have. Routing around the PKB MCP is a security incident
    (aops-18572bc0 §5); removing this instruction is a security regression,
    not a refactor.
    """

    def test_core_md_pkb_halt_sentinel_is_load_bearing(self) -> None:
        core_md = REPO_ROOT / ".agents" / "CORE.md"
        assert core_md.exists(), f"CORE.md not found at {core_md}"
        text = core_md.read_text()
        assert PKB_HALT_SENTINEL in text, (
            f"CORE.md must contain the PKB-HALT sentinel ({PKB_HALT_SENTINEL!r}). "
            "Removing this instruction is a security regression — "
            "routing around the PKB MCP is a security incident (aops-18572bc0 §5)."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
