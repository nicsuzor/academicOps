#!/usr/bin/env python3
"""
Lint gates for aops-core plugin instruction files.
"""

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "aops-core"


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
