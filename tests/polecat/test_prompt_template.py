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
    task = {
        "parent": "parent-task-1",
        "priority": 1,
        "tags": ["tag1", "tag2"]
    }
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
        {"id": "dep2", "status": "done"} # missing title/body
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
        task_body="Fix the thing"
    )
    assert "- **ID**: task-123" in prompt
    assert "- **Title**: Test Task" in prompt
    assert "- **Type**: bug" in prompt
    assert "- **Project**: proj-1" in prompt
    assert "Fix the thing" in prompt
    assert FINISH_LOCAL_TASK.format(task_id="task-123") in prompt

def test_build_polecat_prompt_issue():
    prompt = build_polecat_prompt(
        task_id="issue-456",
        task_title="Issue Title",
        is_issue=True
    )
    assert FINISH_GITHUB_ISSUE in prompt
    assert 'complete_task(id="' not in prompt

def test_build_polecat_prompt_defaults():
    prompt = build_polecat_prompt(
        task_id="task-1",
        task_title="Title",
        task_type="",
        task_project="",
        task_body=""
    )
    assert "- **Type**: task" in prompt
    assert "- **Project**: (none)" in prompt
    assert "(no body)" in prompt

def test_build_polecat_prompt_with_extras_and_deps():
    task_meta = {"priority": 1}
    soft_deps = [{"id": "dep-1", "status": "done", "title": "Dep"}]
    prompt = build_polecat_prompt(
        task_id="task-1",
        task_title="Title",
        task_meta=task_meta,
        soft_deps=soft_deps
    )
    assert "- **Priority**: P1" in prompt
    assert "## Soft Dependency Context" in prompt
    assert "### [dep-1] Dep" in prompt
