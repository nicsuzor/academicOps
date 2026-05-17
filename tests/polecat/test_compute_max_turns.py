from polecat.cli import _DEFAULT_MAX_TURNS, _EFFORT_TO_MAX_TURNS, _compute_max_turns


class DummyTask:
    def __init__(self, effort=None):
        self.effort = effort


def test_compute_max_turns_precedence():
    """Test precedence: flag override > effort > global default."""
    # 1. Global default (no effort)
    task_no_effort = DummyTask()
    assert _compute_max_turns(task_no_effort) == str(_DEFAULT_MAX_TURNS)

    # 2. Effort fallback (unrecognised effort)
    task_bad_effort = DummyTask(effort="xl")
    assert _compute_max_turns(task_bad_effort) == str(_DEFAULT_MAX_TURNS)

    # 3. Effort mapping
    task_xs = DummyTask(effort="xs")
    assert _compute_max_turns(task_xs) == str(_EFFORT_TO_MAX_TURNS["xs"])

    task_s = DummyTask(effort="S")  # Case insensitive
    assert _compute_max_turns(task_s) == str(_EFFORT_TO_MAX_TURNS["s"])

    # 4. Flag override takes precedence over effort
    task_m = DummyTask(effort="m")
    assert _compute_max_turns(task_m, override=42) == "42"
    assert _compute_max_turns(task_m, override="42") == "42"

    # 5. Flag override takes precedence over default
    assert _compute_max_turns(task_no_effort, override=5) == "5"
