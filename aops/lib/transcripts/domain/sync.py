import os
import subprocess
from pathlib import Path


def git_sync(repo_path: Path) -> bool:
    """Run git add, commit, and push in the sessions repository.

    This ensures changes are pushed to Github (closes G12a, task-9c0710ae).
    """
    if not repo_path.exists():
        return False

    try:
        # Check if there are changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            return True

        # git add transcripts and summaries
        subprocess.run(["git", "add", "transcripts/", "summaries/"], cwd=str(repo_path), check=True)

        # Check again if anything is staged
        diff_cached = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(repo_path))
        if diff_cached.returncode == 0:
            return True

        # git commit
        env = os.environ.copy()
        env["GIT_COMMITTER_NAME"] = env.get("GIT_COMMITTER_NAME", "aops-bot")
        env["GIT_COMMITTER_EMAIL"] = env.get("GIT_COMMITTER_EMAIL", "bot@academicops.local")
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"]
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"]

        subprocess.run(
            ["git", "commit", "-m", "sync: update session transcripts and summaries"],
            cwd=str(repo_path),
            env=env,
            check=True,
        )

        # git push
        subprocess.run(["git", "push"], cwd=str(repo_path), check=True)
        return True
    except Exception as e:
        print(f"Warning: git_sync failed: {e}")
        return False
