"""An agent must never be able to invoke a skill that forks that same agent.

A skill carrying ``agent: X`` forks an X to run it. If X's own ``skills:`` list
names that skill, X can call it, forking another X, which can call it again.
Nothing bounds the recursion: one invocation becomes an unbounded subtree.

These checks read ``plugins/`` directly rather than ``dist/``, so they hold on a
source-only checkout and fail before a broken graph can be built or shipped.
"""

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLUGINS = PROJECT_ROOT / "plugins"


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, _, rest = text.partition("---\n")
    block, sep, _ = rest.partition("\n---")
    if not sep:
        return {}
    return yaml.safe_load(block) or {}


def skill_owners() -> dict[str, str]:
    """skill name -> the agent it forks, for every skill that declares one."""
    owners = {}
    for skill in sorted(PLUGINS.rglob("SKILL.md")):
        fm = frontmatter(skill)
        name = fm.get("name") or skill.parent.name
        agent = fm.get("agent")
        if agent:
            owners[name] = agent
    return owners


def agent_files() -> list[Path]:
    return sorted(PLUGINS.glob("*/agents/*.md"))


def test_agents_exist():
    assert agent_files(), "no agent definitions found under plugins/*/agents/"


@pytest.mark.parametrize("agent_path", agent_files(), ids=lambda p: p.stem)
def test_agent_does_not_list_a_skill_that_forks_it(agent_path: Path):
    fm = frontmatter(agent_path)
    name = fm.get("name") or agent_path.stem
    owners = skill_owners()

    cycles = [s for s in (fm.get("skills") or []) if owners.get(s) == name]
    assert not cycles, (
        f"{agent_path.relative_to(PROJECT_ROOT)}: agent '{name}' lists "
        f"{cycles}, and each of those skills declares 'agent: {name}'. "
        f"Calling one forks another {name}, which can call it again — "
        f"unbounded recursion. Remove it from the agent's 'skills:' list; "
        f"the skill body is already this agent's instruction when it runs."
    )


@pytest.mark.parametrize("agent_path", agent_files(), ids=lambda p: p.stem)
def test_agent_declares_a_bounded_subagent_set(agent_path: Path):
    """``subagents: ["*"]`` lets every level of a fan-out spawn every other."""
    fm = frontmatter(agent_path)
    name = fm.get("name") or agent_path.stem
    subagents = fm.get("subagents")

    assert subagents != ["*"], (
        f"{agent_path.relative_to(PROJECT_ROOT)}: agent '{name}' declares "
        f'subagents: ["*"]. Combined with any forking skill this permits '
        f"unbounded fan-out at every depth. Name the agents it may reach."
    )


def test_every_skill_agent_resolves_to_a_shipped_agent():
    """A skill that forks an agent no plugin ships cannot run."""
    shipped = {frontmatter(p).get("name") or p.stem for p in agent_files()}
    dangling = {skill: agent for skill, agent in skill_owners().items() if agent not in shipped}
    assert not dangling, (
        f"skills fork agents that no plugin ships: {dangling}. Shipped agents: {sorted(shipped)}"
    )
