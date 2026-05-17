from polecat.cli import _emit_budget_hit_diagnostic


def test_emit_budget_hit_diagnostic_returns_true_on_max_turns(capsys):
    """Test that _emit_budget_hit_diagnostic detects 'Reached max turns' and emits the structured RESUME_HINT to stderr."""
    stdout = "Some output\n"
    stderr = "Reached max turns\n"

    result = _emit_budget_hit_diagnostic(stdout, stderr, "40", "task-123")

    assert result is True

    captured = capsys.readouterr()
    assert "RESUME_HINT task_id=task-123 command=polecat resume task-123" in captured.err
    assert "⛔ Turn budget exhausted (--max-turns 40)." in captured.err


def test_emit_budget_hit_diagnostic_returns_false_otherwise(capsys):
    """Test that _emit_budget_hit_diagnostic returns False when 'Reached max turns' is not present."""
    stdout = "Just some output\n"
    stderr = ""

    result = _emit_budget_hit_diagnostic(stdout, stderr, "40", "task-123")

    assert result is False
    captured = capsys.readouterr()
    assert captured.err == ""
