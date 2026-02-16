import sys
from pathlib import Path

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))


def test_block_bare_python():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'python' command detected" in result["systemMessage"]


def test_block_bare_pip():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "pip install requests"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'pip' command detected" in result["systemMessage"]


def test_block_bare_jupyter():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "jupyter notebook"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'jupyter' command detected" in result["systemMessage"]


def test_allow_uv_run_python():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_python_version():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "python --version"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_which_python():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "which python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_chained_bare_python():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "ls && python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_chained_uv_run_python():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "ls && uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_bare_python_in_pipe():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "cat script.py | python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_uv_run_python_in_pipe():
    from lib.policy_enforcer import validate_uv_python_usage

    args = {"command": "cat script.py | uv run python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None
