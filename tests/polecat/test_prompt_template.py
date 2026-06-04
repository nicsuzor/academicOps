from polecat.prompt_template import (
    FINISH_GITHUB_ISSUE,
    FINISH_LOCAL_TASK,
    build_polecat_prompt,
    build_soft_dep_context,
    build_task_extras,
)


def test_build_task_extras_empty():
    assert build_task_extras({}) == ""


def test_build_task_extras_all_fields():
    task = {"parent": "parent-task-1", "priority": 1, "tags": ["tag1", "tag2"]}
    result = build_task_extras(task)
    assert "- **Parent**: parent-task-1" in result
    assert "- **Priority**: P1" in result
    assert "- **Tags**: tag1, tag2" in result
    assert result.endswith("\n")


def test_build_task_extras_partial_fields():
    task = {"priority": 0}
    result = build_task_extras(task)
    assert "- **Priority**: P0" in result
    assert "Parent" not in result
    assert "Tags" not in result


def test_build_soft_dep_context_none_or_empty():
    assert build_soft_dep_context(None) == ""
    assert build_soft_dep_context([]) == ""


def test_build_soft_dep_context_no_done():
    deps = [{"id": "dep1", "status": "todo"}]
    assert build_soft_dep_context(deps) == ""


def test_build_soft_dep_context_with_done():
    deps = [
        {"id": "dep1", "title": "Dep 1", "status": "done", "body": "Context body"},
        {"id": "dep2", "status": "done"},  # missing title/body
    ]
    result = build_soft_dep_context(deps)
    assert "## Soft Dependency Context (Advisory)" in result
    assert "### [dep1] Dep 1" in result
    assert "Context body" in result
    assert "### [dep2] (untitled)" in result


def test_build_soft_dep_context_truncation():
    long_body = "x" * 2500
    deps = [{"id": "dep1", "status": "done", "body": long_body}]
    result = build_soft_dep_context(deps)
    assert "[truncated]" in result
    # It should contain exactly 2000 chars of the body before [truncated]
    # The code is: body = body[:2000] + "\n\n[truncated]"
    assert "x" * 2000 in result
    assert "x" * 2001 not in result


def test_build_polecat_prompt_basic():
    prompt = build_polecat_prompt(
        task_id="task-123",
        task_title="Test Task",
        task_type="bug",
        task_project="proj-1",
        task_body="Fix the thing",
    )
    assert "- **ID**: task-123" in prompt
    assert "- **Title**: Test Task" in prompt
    assert "- **Type**: bug" in prompt
    assert "- **Project**: proj-1" in prompt
    assert "Fix the thing" in prompt
    assert FINISH_LOCAL_TASK.format(task_id="task-123") in prompt


def test_polecat_prompt_does_not_start_with_dot():
    """Polecat prompts must NOT start with '.' prefix.

    The '.' prefix was removed so polecats receive proper skill context
    (e.g., testing philosophy from python-dev skill for test-writing tasks).
    """
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    assert not prompt.startswith("."), "Polecat prompt must not start with '.' prefix"


def test_build_polecat_prompt_issue():
    prompt = build_polecat_prompt(task_id="issue-456", task_title="Issue Title", is_issue=True)
    assert FINISH_GITHUB_ISSUE in prompt
    assert 'complete_task(id="' not in prompt


def test_build_polecat_prompt_defaults():
    prompt = build_polecat_prompt(
        task_id="task-1", task_title="Title", task_type="", task_project="", task_body=""
    )
    assert "- **Type**: task" in prompt
    assert "- **Project**: (none)" in prompt
    assert "(no body)" in prompt


def test_build_polecat_prompt_with_extras_and_deps():
    task_meta = {"priority": 1}
    soft_deps = [{"id": "dep-1", "status": "done", "title": "Dep"}]
    prompt = build_polecat_prompt(
        task_id="task-1", task_title="Title", task_meta=task_meta, soft_deps=soft_deps
    )
    assert "- **Priority**: P1" in prompt
    assert "## Soft Dependency Context" in prompt
    assert "### [dep-1] Dep" in prompt


def test_build_task_extras_includes_status():
    task = {"status": "in_progress"}
    result = build_task_extras(task)
    assert "- **Status**: in_progress" in result


def test_build_task_extras_includes_pr_url():
    task = {"pr_url": "https://github.com/owner/repo/pull/42"}
    result = build_task_extras(task)
    assert "- **Existing PR**: https://github.com/owner/repo/pull/42" in result


def test_build_task_extras_includes_pr_number_when_no_url():
    task = {"pr": 99}
    result = build_task_extras(task)
    assert "- **Existing PR**: #99" in result


def test_build_task_extras_pr_url_takes_precedence_over_number():
    task = {"pr_url": "https://github.com/owner/repo/pull/7", "pr": 7}
    result = build_task_extras(task)
    assert "- **Existing PR**: https://github.com/owner/repo/pull/7" in result
    # Should not show #7 when pr_url is present
    assert "- **Existing PR**: #7" not in result


def test_prompt_contains_preflight_check():
    """Worker prompt must include Step 0 pre-flight check for prior work."""
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    assert "### Step 0: Pre-flight" in prompt
    assert "Prior Work" in prompt


def test_prompt_shows_pr_lock_warning_when_pr_url_set():
    """When task has a PR URL, the prompt metadata block must surface it."""
    task_meta = {"pr_url": "https://github.com/owner/repo/pull/825"}
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title", task_meta=task_meta)
    assert "**Existing PR**: https://github.com/owner/repo/pull/825" in prompt


def test_finish_section_reminds_re_reading_task_body_for_mandatory_gates():
    """Regression for #583: Step 0 of FINISH_LOCAL_TASK must be a labelled pre-push gate-recheck step.

    A polecat worker shipped a PR after satisfying gates 1+2 (plan review,
    TDD) but skipping the task body's gate 3 (James re-review on the
    implementation), because the generic "Finish" template structurally
    pulls toward push+PR once code is committed. The mitigation in the
    template is a labelled pre-push gate-recheck step that the worker
    cannot honestly skip without noticing.
    """
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    # The labelled pre-push step must exist.
    assert "Pre-push gate check" in prompt
    # It must explicitly tell the worker to re-read the task body.
    assert "re-read the task body" in prompt.lower()
    # It must reference task-specific / mandatory gates so the worker
    # parses for the right markers (MUST / mandatory / re-review etc.).
    assert "mandatory" in prompt.lower()
    # It must reference #583 so the rationale is auditable.
    assert "#583" in prompt


def test_preamble_leads_with_search_pkb_first_not_do_not_pull():
    """AC#4: the worker preamble must lead with 'search the PKB first', replacing
    the old 'Do not run /pull' stance.

    Partial-work doctrine (PKB: spec-partial-work, chunk 4): the worker is a
    PKB-first actor, not a context-blind executor. The old preamble's headline
    instruction was 'Do not run /pull'; the new headline is PKB-first.
    """
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    assert "Search the PKB first" in prompt
    # The PKB-first instruction must be the framing, not a buried aside: the
    # old hard 'Do not run `/pull`' headline must be gone.
    assert "Do not run `/pull`" not in prompt
    # It must name the PKB-as-system-of-record rationale, not just the slogan.
    assert "system of record" in prompt


def test_preamble_authorises_thin_brief_and_partial_stop():
    """AC#4: the preamble must frame the brief as thin (intent+AC) and authorise
    stopping `partial` when the chunk is too big for one focused session."""
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    assert "thin" in prompt.lower()
    # 'stop partial' must be presented as authorised + expected, not a failure.
    assert "stop partial" in prompt.lower()
    assert "Honest-partial beats false-whole" in prompt


def test_finish_contains_clause_2b_ac_self_certification():
    """AC#3: the finish flow must require every AC to resolve to one of
    tested | declared-deferred | illegal-gap — honesty-led, not a coverage gate.

    Partial-work doctrine clause 2b (PKB: spec-partial-work §3): a silently-absent
    AC is the dishonest stop. The discriminator is worker self-cert + a
    `## Deliberately deferred` PR section, explicitly NOT regex/keyword/coverage
    matching (No-Shitty-NLP P#49). Guard both halves: the three-way partition
    must be present, AND it must be framed as a judgment call, not a tool score.
    """
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    # The three-way partition by name.
    assert "tested" in prompt
    assert "declared-deferred" in prompt
    assert "illegal-gap" in prompt
    # The disclosure convention the partition relies on.
    assert "## Deliberately deferred" in prompt
    # It must NOT be reducible to mechanical matching — it encodes judgment.
    assert "keyword/coverage matching" in prompt
    # It must cite the axioms that forbid narrowing/relabelling an AC.
    assert "A6b" in prompt and "A8" in prompt


def test_finish_contains_partial_draft_pr_path():
    """AC#2: the finish flow must offer a `gh pr create --draft` partial path
    distinct from the ready path, releasing as `partial` not `merge_ready`."""
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    # A draft-PR partial path must exist alongside the ready path.
    assert "--draft" in prompt
    assert 'status="partial"' in prompt
    # It must explicitly forbid laundering a partial stop into merge_ready.
    assert "do **NOT** release" in prompt or "do NOT release `merge_ready`" in prompt
    # The four required gh flags must still be documented (regression guard:
    # omitting --head/--base hangs gh).
    for flag in ("--title", "--body", "--head", "--base"):
        assert flag in prompt


def test_prompt_contains_halt_on_unsatisfiable_checkpoint():
    """Worker prompt must instruct halt-as-blocked on an unsatisfiable AC.

    Regression for the worker-discipline gap behind #1392 / #1305 / #1286:
    when an AC cannot be satisfied as written (no runtime access, an
    out-of-scope config change, or a method the worker can't run), the worker
    must release `blocked` rather than substitute an easier adjacent action
    and self-justify under streetlight pressure. The mitigation is an explicit
    Step 2A checkpoint that grounds the rule in axioms A6b and A8 and names the
    three concrete failure tells.
    """
    prompt = build_polecat_prompt(task_id="task-1", task_title="Title")
    # It must ground the rule in the governing axioms rather than restate them.
    assert "A6b" in prompt
    assert "A8" in prompt
    # It must direct the worker to release as blocked, not proceed.
    assert 'status="blocked"' in prompt
    # The three source incidents must be auditable from the prompt.
    for issue in ("#1392", "#1305", "#1286"):
        assert issue in prompt
