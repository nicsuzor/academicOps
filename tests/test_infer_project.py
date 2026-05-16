import importlib.util
import os
import sys
from pathlib import Path


def test_infer_project_no_truncation(tmp_path):
    """Test that _infer_project does not truncate hyphenated project names."""

    # Setup mock registry
    registry_yaml = """
projects:
  overwhelm-dashboard:
    repo: overwhelm-dashboard
  myproject:
    repo: myproject
"""
    sessions_repo = tmp_path / "sessions"
    sessions_repo.mkdir(exist_ok=True)
    registry_path = sessions_repo / "polecat.yaml"
    registry_path.write_text(registry_yaml)
    os.environ["AOPS_SESSIONS"] = str(sessions_repo)

    # Dynamically import scripts/transcript.py
    # because it is not a standard module in sys.path
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "aops-core" / "scripts" / "transcript.py"

    spec = importlib.util.spec_from_file_location("transcript_script", script_path)
    assert spec is not None and spec.loader is not None
    transcript_script = importlib.util.module_from_spec(spec)
    sys.modules["transcript_script"] = transcript_script
    spec.loader.exec_module(transcript_script)

    _infer_project = transcript_script._infer_project

    # 1. Test Claude project encoded path
    claude_path = Path(
        "/home/worker/.claude/projects/-home-nic-src-overwhelm-dashboard/session-id.jsonl"
    )
    result = _infer_project(claude_path)
    assert result == "overwhelm-dashboard", f"Expected 'overwhelm-dashboard', got '{result}'"

    # 2. Test bare directory name (e.g. from a manual parse or different format)
    bare_path = Path("/home/worker/projects/overwhelm-dashboard/session-id.jsonl")
    result = _infer_project(bare_path)
    assert result == "overwhelm-dashboard", f"Expected 'overwhelm-dashboard', got '{result}'"

    # 3. Test generic project without hyphens
    generic_path = Path("/home/worker/projects/myproject/session-id.jsonl")
    result = _infer_project(generic_path)
    assert result == "myproject", f"Expected 'myproject', got '{result}'"
