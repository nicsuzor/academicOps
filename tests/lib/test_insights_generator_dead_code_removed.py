"""Lock-in tests confirming dead prompt-loader functions are removed.

The functions `load_prompt_template`, `substitute_prompt_variables`, and
`extract_project_name` were removed from `aops-core/lib/insights_generator.py`
in task-83932f98. They had zero production callers and resolved a path
(`specs/session-insights-prompt.md`) that was moved to the brain PKB.

These tests guard against accidental reintroduction of the dead code.
"""

import lib.insights_generator as insights_generator


def test_load_prompt_template_removed():
    """`load_prompt_template` must not exist on the module."""
    assert not hasattr(insights_generator, "load_prompt_template")


def test_substitute_prompt_variables_removed():
    """`substitute_prompt_variables` must not exist on the module."""
    assert not hasattr(insights_generator, "substitute_prompt_variables")


def test_extract_project_name_removed():
    """`extract_project_name` must not exist on the module.

    The live equivalent is `infer_project_from_working_dir` in
    `lib.transcript_parser`.
    """
    assert not hasattr(insights_generator, "extract_project_name")
