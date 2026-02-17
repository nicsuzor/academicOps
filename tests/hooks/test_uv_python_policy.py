import sys
from pathlib import Path

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from lib.policy_enforcer import validate_uv_python_usage


def test_block_bare_python():
    args = {"command": "python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'python' command detected" in result["systemMessage"]


def test_block_bare_pip():
    args = {"command": "pip install requests"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'pip' command detected" in result["systemMessage"]


def test_block_bare_jupyter():
    args = {"command": "jupyter notebook"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'jupyter' command detected" in result["systemMessage"]


def test_allow_uv_run_python():
    args = {"command": "uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_python_version():
    args = {"command": "python --version"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_which_python():
    args = {"command": "which python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_chained_bare_python():
    args = {"command": "ls && python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_chained_uv_run_python():
    args = {"command": "ls && uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_bare_python_in_pipe():
    args = {"command": "cat script.py | python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_uv_run_python_in_pipe():
    args = {"command": "cat script.py | uv run python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_grep_python():
    """Commands where python is an argument should not be blocked."""
    args = {"command": "grep python myfile.txt"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_ls_python():
    """Commands where python appears as a filename should not be blocked."""
    args = {"command": "ls python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_python_in_compound_word():
    """Commands where 'python' appears inside another word should not be blocked."""
    args = {"command": "my_python_script arg1 arg2"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_bare_python3():
    args = {"command": "python3 script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False
    assert "Bare 'python3' command detected" in result["systemMessage"]


def test_allow_python3_version():
    args = {"command": "python3 --version"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_python_v_flag():
    """The -V flag should also be allowed as a version check."""
    args = {"command": "python -V"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_type_python():
    """type command should work similar to which."""
    args = {"command": "type python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_command_v_python():
    """command -v should work similar to which."""
    args = {"command": "command -v python"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_nested_pipes_bare_python():
    args = {"command": "echo 1 | cat | python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_nested_pipes_uv_run_python():
    args = {"command": "echo 1 | cat | uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_allow_echo_python_string():
    """Commands with 'python' in strings should not be blocked."""
    args = {"command": 'echo "run python"'}
    result = validate_uv_python_usage("Bash", args)
    assert result is None


def test_block_sudo_bare_python():
    """sudo python should be blocked (it's a pass-through prefix)."""
    args = {"command": "sudo python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is not None
    assert result["continue"] is False


def test_allow_sudo_uv_run_python():
    """sudo uv run python should be allowed."""
    args = {"command": "sudo uv run python script.py"}
    result = validate_uv_python_usage("Bash", args)
    assert result is None
