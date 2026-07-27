"""Tests for the cope plugin (plugins/cope/).

cope's PreToolUse hook is advisory-only rule enforcement — nothing in-session
blocks on its verdict (specs/ARCHITECTURE.md, cope and Enforcement). These
tests exercise the real plugin source: rules.py's three-layer loading and
its graceful degradation, detectors.py's syntactic checks via handlers.py,
message loading, and the whole thing end to end through lib/hooks/dispatch.py
— simulating build stage 1's shared injection, where lib/hooks/*.py and
plugins/cope/hooks/*.py land in one directory.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_LIB_AXIOMS = _REPO_ROOT / "lib" / "axioms"
_COPE_HOOKS = _REPO_ROOT / "plugins" / "cope" / "hooks"

for _dir in (_LIB_HOOKS, _COPE_HOOKS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import detectors  # noqa: E402  (plugins/cope/hooks/detectors.py)
import handlers  # noqa: E402  (plugins/cope/hooks/handlers.py)
import rules  # noqa: E402  (plugins/cope/hooks/rules.py)
from context import HookContext  # noqa: E402
from result import warn  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_handlers_cache():
    """handlers.py caches the loaded rule set at module scope for the life
    of one hook process (see its docstring). In-process tests must reset
    that cache between cases or they'd see the previous test's rule set."""
    handlers._rules_cache = None
    yield
    handlers._rules_cache = None


def _ctx(
    hooks_dir: Path,
    *,
    tool: str = "",
    command: str = "",
    raw: dict | None = None,
    cwd: Path | None = None,
    client: str = "claude",
    event: str = "PreToolUse",
) -> HookContext:
    raw = dict(raw or {})
    raw.setdefault("tool_name", tool)
    if command:
        raw.setdefault("tool_input", {"command": command})
    if cwd is not None:
        raw.setdefault("cwd", str(cwd))
    return HookContext(
        client=client,
        event=event,
        tool=tool,
        command=command,
        session_id="test-session",
        raw=raw,
        hooks_dir=hooks_dir,
    )


# ---------------------------------------------------------------------------
# rules.py: three-layer loading + graceful degradation
# ---------------------------------------------------------------------------


@pytest.fixture()
def plugin_root(tmp_path):
    root = tmp_path / "plugin"
    (root / "axioms").mkdir(parents=True)
    (root / "axioms" / "bounded-execution.md").write_text(
        "---\ntrigger: always_on\ndescription: floor rule\n---\n\nFloor body.\n"
    )
    return root


def test_layer1_axioms_always_loads(plugin_root, tmp_path):
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert "bounded-execution" in loaded
    assert loaded["bounded-execution"].layer == 1


def test_layer2_and_layer3_absent_degrades_to_layer1_only(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    loaded = rules.load(plugin_root, tmp_path / "project")  # no .agents/rules dir at all
    assert set(loaded) == {"bounded-execution"}


def test_layer2_project_rules_add_new_slugs(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "costly-ops-approval.md").write_text(
        "---\ntrigger: always_on\ndescription: project rule\n---\n\nBody.\n"
    )
    loaded = rules.load(plugin_root, cwd)
    assert set(loaded) == {"bounded-execution", "costly-ops-approval"}
    assert loaded["costly-ops-approval"].layer == 2


def test_layer3_user_rules_require_aca_data_env(plugin_root, tmp_path, monkeypatch):
    aca_data = tmp_path / "pkb"
    (aca_data / ".agents" / "rules").mkdir(parents=True)
    (aca_data / ".agents" / "rules" / "data-boundaries.md").write_text(
        "---\ntrigger: always_on\ndescription: user rule\n---\n\nBody.\n"
    )
    monkeypatch.setenv("ACA_DATA", str(aca_data))
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert "data-boundaries" in loaded
    assert loaded["data-boundaries"].layer == 3


def test_missing_aca_data_env_is_not_an_error(plugin_root, tmp_path, monkeypatch):
    monkeypatch.delenv("ACA_DATA", raising=False)
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert loaded  # layer 1 still loaded — no exception


def test_layer_cannot_override_an_axiom(plugin_root, tmp_path, monkeypatch):
    """A project-local file reusing an axiom's filename cannot replace the
    axiom's entry — layer 1 always wins a slug collision, so a later layer
    can only add obligations, never weaken one."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "bounded-execution.md").write_text(
        "---\ntrigger: manual\ndescription: attempted override\n---\n\nWeaker body.\n"
    )
    loaded = rules.load(plugin_root, cwd)
    assert loaded["bounded-execution"].layer == 1
    assert loaded["bounded-execution"].description == "floor rule"


def test_layer1_skips_axiom_dir_files_that_are_not_always_on(plugin_root, tmp_path, monkeypatch):
    """The shipped axioms/ directory also carries index and companion docs
    (README.md, AXIOMS-REVIEW.md). They are reference material, not rules —
    the same line build/axioms.py draws — so they must never reach the agent
    as live rules."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    (plugin_root / "axioms" / "README.md").write_text(
        "---\ndescription: Index of the axioms.\n---\n\nNot a rule.\n"
    )
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert set(loaded) == {"bounded-execution"}


def test_layer1_loads_only_always_on_from_the_real_axioms_dir(tmp_path, monkeypatch):
    """Against the real lib/axioms/, not a synthetic one: every rule loaded at
    layer 1 declares trigger: always_on, and the index docs are absent."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    plugin_root = tmp_path / "plugin"
    shutil.copytree(_LIB_AXIOMS, plugin_root / "axioms")
    loaded = rules.load(plugin_root, tmp_path / "project")
    assert loaded
    assert all(rule.trigger == "always_on" for rule in loaded.values())
    assert "README" not in loaded
    assert "AXIOMS-REVIEW" not in loaded


def test_layer2_does_not_require_always_on_frontmatter(plugin_root, tmp_path, monkeypatch):
    """A project owns its .agents/rules/ directory; a rule written there
    without frontmatter is still a rule, and dropping it would be a silent
    weakening of the layer the project controls."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    cwd = tmp_path / "project"
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "house-style.md").write_text("Sentence case in headings.\n")
    loaded = rules.load(plugin_root, cwd)
    assert "house-style" in loaded
    assert loaded["house-style"].layer == 2


def test_unreadable_layer_directory_degrades_not_crashes(plugin_root, tmp_path):
    cwd = tmp_path / "project"
    (cwd / ".agents").mkdir(parents=True)
    (cwd / ".agents" / "rules").write_text("a file, not a directory")
    loaded = rules.load(plugin_root, cwd)  # must not raise
    assert set(loaded) == {"bounded-execution"}


# ---------------------------------------------------------------------------
# detectors.py + handlers.py: what actually fires, in-process
# ---------------------------------------------------------------------------


@pytest.fixture()
def hooks_dir_with_axioms(tmp_path):
    """A hooks_dir + sibling axioms/ dir carrying the real floor axioms for
    every detectable slug, plus the real message files — mirrors build
    stage 1's injection layout (axioms/ and hooks/ are plugin-root siblings).
    Also returns an empty, isolated project cwd so layer 2 never accidentally
    picks up this repo's own real .agents/rules/ during the test run."""
    plugin_root = tmp_path / "plugin"
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", hooks_dir / "messages")
    axioms_dir = plugin_root / "axioms"
    axioms_dir.mkdir()
    for slug in detectors.DETECTORS:
        src = _LIB_AXIOMS / f"{slug}.md"
        assert src.is_file(), f"expected real axiom file for {slug}"
        shutil.copy2(src, axioms_dir / src.name)
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    return hooks_dir, project_cwd


def test_evaluate_no_op_on_clean_command(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    ctx = _ctx(hooks_dir, tool="Bash", command="git status", cwd=cwd)
    assert handlers.evaluate(ctx) is None


def test_evaluate_flags_force_push(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    ctx = _ctx(hooks_dir, tool="Bash", command="git push --force origin main", cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "costly-ops-approval" in result.inject_text
    assert "--force" in result.inject_text


def test_evaluate_flags_no_verify(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    ctx = _ctx(hooks_dir, tool="Bash", command="git commit --no-verify -m x", cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "halt-on-failure" in result.inject_text


def test_evaluate_flags_tail_f(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    ctx = _ctx(hooks_dir, tool="Bash", command="tail -f /var/log/syslog", cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "bounded-execution" in result.inject_text


def test_evaluate_flags_env_file_read(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    raw = {"tool_name": "Read", "tool_input": {"file_path": "/home/nic/project/.env"}}
    ctx = _ctx(hooks_dir, tool="Read", raw=raw, cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "data-boundaries" in result.inject_text


def test_evaluate_flags_evidence_write(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    raw = {"tool_name": "Write", "tool_input": {"file_path": "tests/fixtures/golden/output.json"}}
    ctx = _ctx(hooks_dir, tool="Write", raw=raw, cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "evidence-immutable" in result.inject_text


def test_evaluate_flags_suppressed_mutating_output(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    ctx = _ctx(hooks_dir, tool="Bash", command="git push origin main > /dev/null 2>&1", cwd=cwd)
    result = handlers.evaluate(ctx)
    assert result is not None
    assert "full-observability" in result.inject_text


def test_evaluate_never_fires_for_slug_not_loaded(tmp_path):
    """A command that would otherwise match stays silent if that axiom
    isn't in the loaded rule set at all (no axiom file, no override)."""
    plugin_root = tmp_path / "plugin"
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", hooks_dir / "messages")
    (plugin_root / "axioms").mkdir()  # empty — nothing loaded
    project_cwd = tmp_path / "project"  # empty — no layer 2 either
    project_cwd.mkdir()
    ctx = _ctx(
        hooks_dir,
        tool="Bash",
        command="git push --force origin main",
        raw={"cwd": str(project_cwd)},
    )
    assert handlers.evaluate(ctx) is None


# ---------------------------------------------------------------------------
# inject_ruleset: the turn-level advisory, and the client scope that keeps it
# off Claude
# ---------------------------------------------------------------------------


def _prompt_ctx(hooks_dir: Path, cwd: Path, *, client: str) -> HookContext:
    return _ctx(
        hooks_dir,
        raw={"prompt": "what did we decide about the build?"},
        cwd=cwd,
        client=client,
        event="UserPromptSubmit",
    )


def test_inject_ruleset_is_declared_agy_only():
    """The scope is declared on the handler, not inferred from a hooks.json —
    dispatch.py reads this attribute, and so does test_shipped_hooks.py."""
    assert handlers.inject_ruleset.only_on_clients == frozenset({"agy"})


def test_inject_ruleset_names_every_live_rule(hooks_dir_with_axioms):
    hooks_dir, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks_dir, cwd, client="agy"))
    assert result is not None
    for slug in detectors.DETECTORS:
        assert f"**{slug}** (1)" in result.inject_text


def test_inject_ruleset_marks_the_layer_a_rule_came_from(hooks_dir_with_axioms, monkeypatch):
    """A project-local rule is the thing agy's own static rules/ directory
    cannot know about, so the layer marker is the load-bearing part."""
    monkeypatch.delenv("ACA_DATA", raising=False)
    hooks_dir, cwd = hooks_dir_with_axioms
    (cwd / ".agents" / "rules").mkdir(parents=True)
    (cwd / ".agents" / "rules" / "house-style.md").write_text(
        "---\ntrigger: always_on\ndescription: Sentence case in headings.\n---\n\nBody.\n"
    )
    result = handlers.inject_ruleset(_prompt_ctx(hooks_dir, cwd, client="agy"))
    assert result is not None
    assert "**house-style** (2) — Sentence case in headings." in result.inject_text


def test_inject_ruleset_is_one_line_per_rule_not_the_rule_bodies(hooks_dir_with_axioms):
    """Compressed, and cheap enough to pay every turn: the digest carries each
    rule's own one-line description, never the axiom body shipped alongside it."""
    hooks_dir, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks_dir, cwd, client="agy"))
    assert result is not None
    bullets = [ln for ln in result.inject_text.splitlines() if ln.startswith("- **")]
    assert len(bullets) == len(detectors.DETECTORS)
    axiom = (_LIB_AXIOMS / "halt-on-failure.md").read_text()
    body = axiom.split("\n---\n", 1)[1]
    body_line = next(
        ln for ln in body.splitlines() if len(ln.strip()) > 40 and not ln.startswith("#")
    )
    assert body_line not in result.inject_text


def test_inject_ruleset_silent_when_no_rules_load(tmp_path):
    plugin_root = tmp_path / "plugin"
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copytree(_COPE_HOOKS / "messages", hooks_dir / "messages")
    (plugin_root / "axioms").mkdir()  # empty — nothing loaded
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    assert handlers.inject_ruleset(_prompt_ctx(hooks_dir, project_cwd, client="agy")) is None


def test_ruleset_message_file_carries_the_placeholder_and_no_leftovers(hooks_dir_with_axioms):
    """The wording lives in messages/ruleset.md; the handler only fills in the
    generated roster. A renamed placeholder would silently ship un-substituted."""
    source = (_COPE_HOOKS / "messages" / "ruleset.md").read_text()
    assert "{rules}" in source
    hooks_dir, cwd = hooks_dir_with_axioms
    result = handlers.inject_ruleset(_prompt_ctx(hooks_dir, cwd, client="agy"))
    assert result is not None
    assert "{rules}" not in result.inject_text


# ---------------------------------------------------------------------------
# Result shape: cope is advisory-only, and cannot reach the blocking outcome
# ---------------------------------------------------------------------------
#
# The shared runtime does carry one blocking outcome — a refusal, reserved for
# structural impossibility and used by exactly one hook, aops's headless
# interactive-prompt check (lib/hooks/result.py). cope is not that hook and
# never will be: rule enforcement is advisory, permanently. So the guarantee is
# asserted about cope rather than about the type.


def test_warn_never_produces_a_refusal():
    result = warn("x")
    assert {f.name for f in dataclasses.fields(result)} == {
        "inject_text",
        "user_text",
        "is_refusal",
    }
    assert result.is_refusal is False


def test_cope_source_never_names_the_refusal_primitive():
    """cope may only ever call warn(). Checked at the source, so a future
    handler cannot acquire a blocking path without this failing — a payload
    that happens not to trigger one would not notice."""
    offenders = [
        path.name
        for path in sorted(_COPE_HOOKS.glob("*.py"))
        if "refuse" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_every_cope_handler_returns_an_advisory_or_nothing(hooks_dir_with_axioms):
    """Behavioural counterpart: run every registered cope handler on a payload
    each is known to fire on, and require a non-refusal result."""
    hooks_dir, cwd = hooks_dir_with_axioms
    fired = 0
    for event, hooks in handlers.HANDLERS.items():
        for handler in hooks:
            client = "agy" if getattr(handler, "only_on_clients", None) else "claude"
            ctx = _ctx(
                hooks_dir,
                tool="Bash",
                command="git commit --no-verify -m x",
                cwd=cwd,
                client=client,
                event=event,
            )
            result = handler(ctx)
            if result is None:
                continue
            assert result.is_refusal is False, f"{handler.__name__} refused on {event}"
            fired += 1
    assert fired > 0, "no cope handler produced a result; the assertion checked nothing"


# ---------------------------------------------------------------------------
# message loading
# ---------------------------------------------------------------------------


def test_every_detector_slug_has_a_message_file():
    messages_dir = _COPE_HOOKS / "messages"
    for slug in detectors.DETECTORS:
        path = messages_dir / f"{slug}.md"
        assert path.is_file(), f"missing message file for {slug}"
        assert path.read_text().strip()


# ---------------------------------------------------------------------------
# End to end through lib/hooks/dispatch.py, both angles: fires, and never blocks
# ---------------------------------------------------------------------------


@pytest.fixture()
def built_cope_plugin(tmp_path):
    """Assembles the plugin the way build stage 1 would: lib/hooks/*.py and
    plugins/cope/hooks/*.py copied into one hooks/ dir, plus a sibling
    axioms/ dir carrying lib/axioms/ verbatim — index docs included, because
    that is what ships, and a fixture that filtered them would hide whether
    the loader distinguishes a rule from a reference doc."""
    plugin_root = tmp_path / "plugin"
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True)
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    for py_file in _COPE_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    shutil.copytree(_COPE_HOOKS / "messages", hooks_dir / "messages")
    shutil.copytree(_LIB_AXIOMS, plugin_root / "axioms")
    return hooks_dir


def _run_dispatch(
    hooks_dir: Path, client: str, event: str, raw: dict, *, cwd: Path, env: dict | None = None
):
    return subprocess.run(
        [sys.executable, str(hooks_dir / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )


def test_dispatch_end_to_end_flags_force_push_advisory_only(built_cope_plugin, tmp_path):
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push --force origin main"},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd)
    assert result.returncode == 0
    out = json.loads(result.stdout)
    # advisory only: additionalContext, never a permission/blocking decision
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert "decision" not in out
    assert "costly-ops-approval" in out["hookSpecificOutput"]["additionalContext"]


def test_dispatch_end_to_end_clean_command_is_a_noop(built_cope_plugin, tmp_path):
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_dispatch_end_to_end_credential_path_read_is_flagged(built_cope_plugin, tmp_path):
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": str(project_cwd / ".env")},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd)
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "decision" not in out
    assert "data-boundaries" in out["hookSpecificOutput"]["additionalContext"]


def test_dispatch_end_to_end_missing_aca_data_degrades_gracefully(built_cope_plugin, tmp_path):
    """Layer 3 unset entirely (no $ACA_DATA in the environment at all) must
    not crash the hook or suppress a legitimate layer-1 advisory."""
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    env = dict(os.environ)
    env.pop("ACA_DATA", None)
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push --force origin main"},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd, env=env)
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "costly-ops-approval" in out["hookSpecificOutput"]["additionalContext"]


def _no_aca_data_env() -> dict:
    env = dict(os.environ)
    env.pop("ACA_DATA", None)  # keep layer 3 out of content assertions
    return env


def test_dispatch_agy_preinvocation_injects_the_live_ruleset(built_cope_plugin, tmp_path):
    """agy's only usable phase carries a prompt, not a tool call. cope fires
    there and states the rule set — the whole reason the hook is wired."""
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {"prompt": "ship the release", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "agy", "PreInvocation", raw, cwd=project_cwd, env=_no_aca_data_env()
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    out = json.loads(result.stdout)
    injected = out["injectSteps"][0]["ephemeralMessage"]
    assert "**halt-on-failure** (1)" in injected
    assert "**judgment-non-delegable** (1)" in injected
    # the axioms/ index docs ship alongside the rules and are not rules
    assert "**README**" not in injected
    assert "**AXIOMS-REVIEW**" not in injected


def test_dispatch_agy_preinvocation_is_advisory_only(built_cope_plugin, tmp_path):
    """agy's wire shape has one non-empty form — an ephemeral message. There is
    no decision, no permission field, nothing that could stop the turn."""
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {"prompt": "ship the release", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin, "agy", "PreInvocation", raw, cwd=project_cwd, env=_no_aca_data_env()
    )
    out = json.loads(result.stdout)
    assert set(out) == {"injectSteps"}
    assert set(out["injectSteps"][0]) == {"ephemeralMessage"}


def test_dispatch_claude_userpromptsubmit_stays_silent(built_cope_plugin, tmp_path):
    """Claude fires both UserPromptSubmit and PreToolUse, and cope covers it at
    PreToolUse; the pkb plugin owns Claude's UserPromptSubmit. Even reached
    directly, cope's turn-level advisory must produce nothing here."""
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {"hook_event_name": "UserPromptSubmit", "prompt": "hello", "cwd": str(project_cwd)}
    result = _run_dispatch(
        built_cope_plugin,
        "claude",
        "UserPromptSubmit",
        raw,
        cwd=project_cwd,
        env=_no_aca_data_env(),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert result.stdout.strip() == ""


def test_dispatch_agy_never_reaches_the_detectors(built_cope_plugin, tmp_path):
    """A tool payload delivered on agy's phase still yields the ruleset
    advisory, not a detector match — there is no PreToolUse on agy, so cope
    must not pretend it evaluated a tool call it never saw."""
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {
        "prompt": "commit it",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify -m x"},
        "cwd": str(project_cwd),
    }
    result = _run_dispatch(
        built_cope_plugin, "agy", "PreInvocation", raw, cwd=project_cwd, env=_no_aca_data_env()
    )
    injected = json.loads(result.stdout)["injectSteps"][0]["ephemeralMessage"]
    assert "Matched in this call" not in injected


def test_dispatch_falls_back_to_process_cwd_when_payload_omits_it(built_cope_plugin, tmp_path):
    project_cwd = tmp_path / "project"
    project_cwd.mkdir()
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push --force origin main"},
    }  # no "cwd" key in the payload
    result = _run_dispatch(built_cope_plugin, "claude", "PreToolUse", raw, cwd=project_cwd)
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "costly-ops-approval" in out["hookSpecificOutput"]["additionalContext"]
