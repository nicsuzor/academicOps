import sys
import traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

TESTS_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(TESTS_DIR / "polecat"))

from cli import crew, run


def test_crew_interactive_pops_ci():
    """If crew with interactive shell, CI=true is popped from env."""

    with (
        patch("cli._build_docker_cmd") as mock_build_docker_cmd,
        patch("cli.PolecatManager") as MockManager,
        patch("cli._run_docker_container"),
        patch("cli._bootstrap_or_exit"),
        patch("cli._require_claude_oauth_or_exit"),
        patch("cli._get_sessions_base", return_value=Path("/tmp/sessions")),
        patch("cli._init_container_memory", return_value=(None, None)),
        patch("cli.sys.exit"),
    ):
        mock_manager = MockManager.return_value
        mock_manager.projects = {"aops": {"repo": "test"}}
        mock_manager.resolve_project_alias.return_value = "aops"
        mock_manager.home_dir = Path("/tmp/home")

        ctx = crew.make_context("crew", ["-i", "aops"])
        ctx.obj = {"home": Path("/tmp/home"), "verbose": False}

        try:
            crew.invoke(ctx)
        except Exception:
            traceback.print_exc()
            pass

        assert mock_build_docker_cmd.called
        env_arg = (
            mock_build_docker_cmd.call_args.kwargs.get("env")
            or mock_build_docker_cmd.call_args.args[2]
        )
        assert "CI" not in env_arg, "CI was not popped from env in interactive crew"
        assert "NONINTERACTIVE" not in env_arg, (
            "NONINTERACTIVE was not popped from env in interactive crew"
        )


def test_run_antigravity_interactive_pops_ci():
    """If run with --interactive and model=antigravity, CI=true is popped from env."""

    with (
        patch("cli._build_docker_cmd") as mock_build_docker_cmd,
        patch("cli.PolecatManager") as MockManager,
        patch("cli._replicate_gemini_auth", return_value=Path("/tmp/mock-gemini")),
        patch("cli._run_docker_container"),
        patch("cli._bootstrap_or_exit"),
        patch("cli._require_claude_oauth_or_exit"),
        patch("cli._require_pkb_url_or_exit"),
        patch("cli._get_sessions_base", return_value=Path("/tmp/sessions")),
        patch("cli._init_container_memory", return_value=(None, None)),
        patch("cli.sys.exit"),
    ):
        mock_manager = MockManager.return_value
        mock_manager.projects = {"aops": {"repo": "test"}}
        mock_manager.home_dir = Path("/tmp/home")

        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.project = "aops"
        mock_manager.get_task.return_value = mock_task
        mock_manager.resolve_project_alias.return_value = "aops"
        mock_manager.checkout_repo.return_value = (Path("/tmp/home"), "branch")

        ctx = run.make_context(
            "run", ["--model", "antigravity", "-i", "-t", "task-123", "-p", "aops"]
        )
        ctx.obj = {"home": Path("/tmp/home"), "verbose": False}

        try:
            run.invoke(ctx)
        except Exception:
            traceback.print_exc()
            pass

        assert mock_build_docker_cmd.called
        env_arg = (
            mock_build_docker_cmd.call_args.kwargs.get("env")
            or mock_build_docker_cmd.call_args.args[2]
        )
        assert "CI" not in env_arg, "CI was not popped from env in interactive run"
        assert "NONINTERACTIVE" not in env_arg, (
            "NONINTERACTIVE was not popped from env in interactive run"
        )
