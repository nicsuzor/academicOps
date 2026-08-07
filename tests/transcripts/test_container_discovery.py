"""A supervisor inside a container must be able to see what its workers did.

`$AOPS_SESSIONS` is a host value polecat does not forward
(`lib/polecat/env_contract.py`: it is in neither `FORWARDED_ENV` nor
`CONTAINER_SET_ENV`), so every host-side session-store path is unreachable from
inside a single-repository container. What the container does have is the
clients' own state roots, live under its own `$HOME`:

    $CLAUDE_CONFIG_DIR or ~/.claude
        projects/<slugified-cwd>/<session-uuid>.jsonl              — supervisor
        projects/<slugified-cwd>/<uuid>/subagents/agent-*.jsonl    — its workers
    ~/.gemini/antigravity-cli/brain
        <conversation-id>/.system_generated/logs/transcript*.jsonl — agy workers

The batch pipeline's `find_session_files` cannot answer this question: it drops
`subagents/` on purpose, and those sidechains are exactly the worker record a
supervisor is judging claims against.
"""

import json
from pathlib import Path

from transcripts.discovery import (
    AGY_TRANSCRIPT_GLOB,
    agy_brain_roots,
    claude_projects_root,
    find_container_transcripts,
)
from transcripts.runner import find_session_files

_TRUNK = "4bebd5ff-9386-439f-9e54-c711c86d0cb5"


def _claude_container_state(home: Path, project: str = "-workspace") -> dict[str, Path]:
    """The layout a claude polecat container holds after spawning one subagent."""
    project_dir = home / ".claude" / "projects" / project
    subagents = project_dir / _TRUNK / "subagents"
    subagents.mkdir(parents=True)

    trunk = project_dir / f"{_TRUNK}.jsonl"
    trunk.write_text(json.dumps({"type": "user", "cwd": "/workspace"}) + "\n", encoding="utf-8")

    worker = subagents / "agent-aw1-transcripts-ecf65e9acf99994c.jsonl"
    worker.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")
    (subagents / "agent-aw1-transcripts-ecf65e9acf99994c.meta.json").write_text(
        json.dumps({"agentType": "w1-transcripts", "name": "w1-transcripts"}), encoding="utf-8"
    )

    # Polecat's own hook log shares the directory and the suffix.
    (project_dir / "polecat-session-hooks.jsonl").write_text('{"hook":"Stop"}\n', encoding="utf-8")
    return {"trunk": trunk, "worker": worker, "project_dir": project_dir}


def _agy_container_state(home: Path, conversation: str = "0e15fe21-cd9e-4043-80d1-a87e9115834b"):
    logs = (
        home / ".gemini" / "antigravity-cli" / "brain" / conversation / ".system_generated" / "logs"
    )
    logs.mkdir(parents=True)
    transcript = logs / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "USER_INPUT", "content": "hi"}) + "\n", "utf-8")
    full = logs / "transcript_full.jsonl"
    full.write_text(json.dumps({"type": "USER_INPUT", "content": "hi"}) + "\n", "utf-8")
    return {"transcript": transcript, "full": full}


def test_the_container_view_needs_no_host_session_store(tmp_path, monkeypatch):
    """The whole point: with `$AOPS_SESSIONS` absent, as it is in every polecat
    container, the worker transcripts are still resolved."""
    home = tmp_path / "home"
    state = _claude_container_state(home)
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)

    refs = find_container_transcripts({}, home=home)

    assert state["worker"] in [ref.path for ref in refs]


def test_a_supervisor_sees_the_workers_it_spawned(tmp_path):
    """The sidechain the batch pipeline drops is the one a supervisor needs, and
    it arrives named by the agent that ran it and by the session it belongs to."""
    home = tmp_path / "home"
    state = _claude_container_state(home)

    workers = [ref for ref in find_container_transcripts({}, home=home) if ref.kind == "subagent"]

    assert [ref.path for ref in workers] == [state["worker"]]
    assert workers[0].client == "claude"
    assert workers[0].parent_id == _TRUNK
    assert workers[0].agent == "w1-transcripts"


def test_the_batch_pipeline_alone_cannot_answer_this(tmp_path, monkeypatch):
    """Guards the reason this module exists rather than reusing
    `find_session_files`: that function drops `subagents/` by design, so a
    supervisor calling it gets its own transcript and none of its workers'."""
    home = tmp_path / "home"
    state = _claude_container_state(home)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)

    assert state["worker"] not in find_session_files()
    assert state["trunk"] in find_session_files()


def test_the_supervisors_own_session_is_distinguished_from_a_worker(tmp_path):
    home = tmp_path / "home"
    state = _claude_container_state(home)

    by_path = {ref.path: ref for ref in find_container_transcripts({}, home=home)}

    assert by_path[state["trunk"]].kind == "session"
    assert by_path[state["trunk"]].parent_id is None
    assert by_path[state["worker"]].kind == "subagent"


def test_the_hook_log_is_never_mistaken_for_a_conversation(tmp_path):
    home = tmp_path / "home"
    _claude_container_state(home)

    names = [ref.path.name for ref in find_container_transcripts({}, home=home)]

    assert "polecat-session-hooks.jsonl" not in names


def test_agy_workers_are_found_under_the_brain_root(tmp_path):
    """An agy run launched from inside the container writes a conversation
    directory under the brain, both the pruned and the full transcript."""
    home = tmp_path / "home"
    state = _agy_container_state(home)

    refs = [ref for ref in find_container_transcripts({}, home=home) if ref.client == "agy"]

    assert sorted(ref.path for ref in refs) == sorted([state["full"], state["transcript"]])
    assert {ref.session_id for ref in refs} == {"0e15fe21-cd9e-4043-80d1-a87e9115834b"}
    assert all(ref.kind == "session" for ref in refs)


def test_both_clients_come_back_from_one_call(tmp_path):
    home = tmp_path / "home"
    _claude_container_state(home)
    _agy_container_state(home)

    refs = find_container_transcripts({}, home=home)

    assert {ref.client for ref in refs} == {"claude", "agy"}


def test_a_relocated_claude_state_dir_is_honoured(tmp_path):
    """`$CLAUDE_CONFIG_DIR` moves Claude Code's whole state directory; discovery
    follows it rather than assuming a path under home."""
    home = tmp_path / "home"
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "projects").mkdir(parents=True)
    (elsewhere / "projects" / "-workspace").mkdir()
    trunk = elsewhere / "projects" / "-workspace" / f"{_TRUNK}.jsonl"
    trunk.write_text("{}\n", encoding="utf-8")

    assert claude_projects_root({"CLAUDE_CONFIG_DIR": str(elsewhere)}, home=home) == (
        elsewhere / "projects"
    )
    refs = find_container_transcripts({"CLAUDE_CONFIG_DIR": str(elsewhere)}, home=home)
    assert [ref.path for ref in refs] == [trunk]


def test_no_root_is_a_hardcoded_host_path(tmp_path):
    """Every root is composed from the environment, so nothing resolves outside
    the home the caller is actually running under."""
    home = tmp_path / "home"

    roots = [claude_projects_root({}, home=home), *agy_brain_roots({}, home=home)]

    assert all(home in root.parents for root in roots)


def test_the_agy_glob_matches_the_runtime_layout():
    """The path the runtime writes, asserted against the shape polecat mounts:
    `<brain>/<conversation-id>/.system_generated/logs/transcript*.jsonl`."""
    assert AGY_TRANSCRIPT_GLOB == "*/.system_generated/logs/transcript*.jsonl"


def test_missing_roots_are_not_an_error(tmp_path):
    assert find_container_transcripts({}, home=tmp_path / "nothing-here") == []
